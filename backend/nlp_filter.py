"""
nlp_filter.py  –  GuardianText NLP Toxicity Detection

Hybrid approach:
  - ML classifier (scikit-learn) for overall toxicity score
  - Keyword / phrase detection for masking + targeted suggestions
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


LEET_MAP = str.maketrans({'@':'a','4':'a','3':'e','1':'i','0':'o','5':'s','$':'s','7':'t','+':'t','8':'b','6':'g','v':'u','z':'s','x':'a','!':'i'})

EXPANSIONS = {
    'kys':'kill yourself','stfu':'shut the fuck up','wtf':'what the fuck',
    'gtfo':'get the fuck out','fu':'fuck you','pos':'piece of shit',
    'smh':'shaking my head','omg':'oh my god','lmao':'laughing my ass off',
    'nsfw':'not safe for work','fml':'fuck my life','smdh':'shaking my damn head',
    'ngl':'not gonna lie','nvm':'never mind','wyd':'what you doing',
    'sus':'suspicious','asl':'as hell','af':'as fuck','lol':'laughing out loud',
    'tf':'the fuck','wtf':'what the fuck','stg':'swear to god',
}

TOXIC_WORDS = {
    # Level 1: Mild insults/negativity
    'idiot':1,'stupid':1,'dumb':1,'moron':1,'loser':1,'jerk':1,'lame':1,
    'ugly':1,'pathetic':1,'worthless':1,'useless':1,'freak':1,'weirdo':1,
    'creep':1,'liar':1,'coward':1,'dummy':1,'shut up':1,'crap':1,
    'damn':1,'dork':1,'prick':1,'twit':1,'nitwit':1,'sucks':1,'suck':1,
    'gay':1,'fool':1,'idiotis':1,'foolish':1,'silly':1,'ridiculous':1,'absurd':1,
    'nonsense':1,'rubbish':1,'daft':1,'goofy':1,'obnoxious':1,'juvenile':1,'childish':1,
    'immature':1,'petty':1,'spiteful':1,'vindictive':1,'bitter':1,'resentful':1,
    'judgmental':1,'arrogant':1,'conceited':1,'smug':1,'pompous':1,'self righteous':1,
    'annoying':1,'irritating':1,'bothersome':1,'tedious':1,'grueling':1,'tedium':1,
    'bland':1,'boring':1,'dull':1,'insipid':1,'uninspired':1,'mediocre':1,'inferior':1,
    'weak':1,'feeble':1,'pathetic':1,'miserable':1,'hopeless':1,'desperate':1,
    'doomed':1,'ruined':1,'wrecked':1,'botched':1,'messed up':1,'screwed up':1,
    'bastards':1,'asses':1,'dopes':1,'dimwits':1,'nitwits':1,'twits':1,'boobs':1,
    'chump':1,'clown':1,'buffoon':1,'nincompoop':1,'incompetent':1,
    
    # Level 2: Moderate vulgar/disrespectful words - GENERAL
    'hate':2,'disgusting':2,'trash':2,'scum':2,'garbage':2,'filth':2,
    'pig':2,'degenerate':2,'ass':2,'bastard':2,'bitch':2,'damn you':2,
    'stfu':2,'go to hell':2,'piece of garbage':2,'piece of trash':2,
    'fck':2,'fck you':2,'gtfo':2,'fuck':2,'fuck you':2,'shit':2,'asshole':2,
    'fucking':2,'fucking shit':2,'shitty':2,'bullshit':2,'horseshit':2,'crap':2,
    'damn it':2,'dammit':2,'goddamn':2,'hell':2,'bloody hell':2,'blasted':2,
    'crappy':2,'junky':2,'lousy':2,'pathetic':2,'rotten':2,'vile':2,'foul':2,
    'obscene':2,'vulgar':2,'offensive':2,'repulsive':2,'loathsome':2,'nauseating':2,
    'sickening':2,'appalling':2,'atrocious':2,'abominable':2,'odious':2,'despicable':2,
    'deplorable':2,'shameful':2,'scandalous':2,'outrageous':2,'ridiculous':2,
    'preposterous':2,'absurd':2,'cockamamie':2,'cockamammy':2,
    
    # Level 2: SEXUAL/ANATOMICAL TERMS
    'cock':2,'pussy':2,'dick':2,'dildo':2,'anal':2,'penis':2,'vagina':2,
    'boobs':2,'tits':2,'nipples':2,'cunt':2,'whore':2,'slut':2,'pimp':2,'ho':2,
    'prostitute':2,'harlot':2,'trollop':2,'strumpet':2,'floozy':2,'easy':2,
    'pervert':2,'horny':2,'sexy':2,'porn':2,'pornography':2,'xxx':2,'masturbat':2,
    'orgy':2,'gangbang':2,'threesome':2,'fuckbuddy':2,'bootycall':2,'hookup':2,
    'cumming':2,'orgasm':2,'creampie':2,'blowjob':2,'handjob':2,'suck my':2,
    'riding':2,'doggy style':2,'missionary':2,'dominant':2,'submissive':2,
    'bondage':2,'fetish':2,'kink':2,'bdsm':2,'spanking':2,
    'breast':2,'ass':2,'butt':2,'buttocks':2,'bottom':2,'derriere':2,'posterior':2,
    'crotch':2,'groin':2,'genitals':2,'privates':2,'loins':2,'pubic':2,
    'menstrual':2,'period':2,'tampon':2,'sanitary':2,
    
    # Level 2: CRUDE BODILY TERMS
    'piss':2,'pissed':2,'pissing':2,'arsehole':2,'arse':2,'fart':2,'semen':2,
    'cum':2,'jizz':2,'sperm':2,'ejaculate':2,'ejaculation':2,'cumshot':2,'facial':2,
    'jerk off':2,'jerking':2,'pee':2,'peeing':2,'urine':2,'piss off':2,'pee on you':2,
    'snot':2,'mucus':2,'boogers':2,'phlegm':2,'spit':2,'spitting':2,'sputum':2,
    'belch':2,'burp':2,'vomit':2,'puke':2,'barf':2,'gag':2,'retch':2,
    'constipation':2,'diarrhea':2,'hemorrhoid':2,'constipated':2,'shitting':2,
    'bowel':2,'defecate':2,'excrement':2,'feces':2,'stool':2,'turd':2,
    'snore':2,'flatulence':2,'gas':2,'intestinal':2,'stomach':2,'gut':2,
    
    # Level 2: OFFENSIVE GENDER/SEXUAL ORIENTATION TERMS
    'tranny':2,'trans':2,'dyke':2,'lesbo':2,'homo':2,'queer':2,'fairy':2,
    'fag':2,'faggot':2,'pansy':2,'sissy':2,'girly':2,'feminine':2,
    'butch':2,'manly':2,'masculine':2,'beta':2,'simp':2,'incel':2,'chad':2,
    'thot':2,'insta thot':2,'e girl':2,'e boy':2,'femboy':2,'tomboy':2,
    'housewife':2,'househusband':2,'stay at home':2,
    
    # Level 3: Severe - VIOLENT THREATS
    'kill yourself':3,'kys':3,'kill you':3,'murder':3,'gonna kill':3,
    'beat you':3,'beat up':3,'beat down':3,'hurt you':3,'injure':3,'wound':3,
    'rape':3,'violate':3,'assault':3,'attack':3,'destroy you':3,'obliterate':3,
    'annihilate':3,'wipe out':3,'eliminate':3,'eradicate':3,'exterminate':3,
    'decapitate':3,'behead':3,'dismember':3,'mutilate':3,'torture':3,
    'bomb':3,'explode':3,'blow up':3,'detonate':3,'nuke':3,'nuke you':3,
    'die':3,'drop dead':3,'stab you':3,'shoot you':3,'hang you':3,'hang yourself':3,
    'drown':3,'drown you':3,'poison':3,'suffocate':3,'strangle':3,'choke':3,
    'lynching':3,'lynched':3,'crucify':3,'burn you':3,'burn alive':3,'immolate':3,
    'crush you':3,'flatten':3,'smash':3,'pulverize':3,'obliterate':3,'vaporize':3,
    'i will hurt':3,'i will kill':3,'gonna beat':3,'gonna hit':3,'gonna punch':3,
    'you deserve to die':3,'die in a fire':3,'go die':3,'hope you die':3,
    'kill your family':3,'hurt your family':3,'rape you':3,'rape your':3,
    'accident':3,'car crash':3,'plane crash':3,'overdose':3,'suicide':3,
    
    # Level 3: RACIST/ETHNIC SLURS
    'nigger':3,'nigga':3,'n word':3,'negro':3,'negroid':3,'blackie':3,'darkie':3,
    'spic':3,'spick':3,'spain':3,'spanish':3,'latino':3,'wetback':3,
    'chink':3,'chinamen':3,'oriental':3,'slant':3,'chinky':3,
    'gook':3,'slope':3,'jap':3,'japanese':3,'asian':3,'orient':3,
    'towelhead':3,'camel jockey':3,'raghead':3,'arab':3,'sand nigger':3,
    'paki':3,'curry muncher':3,'dot head':3,'hindi':3,'singh':3,'patel':3,
    'beaner':3,'greaser':3,'mexican':3,'mestizo':3,'latino':3,'chicano':3,
    'cracker':3,'redneck':3,'hillbilly':3,'white trash':3,'trailer trash':3,
    'whitey':3,'honky':3,'white boy':3,'whitey':3,'caucasoid':3,
    'kyke':3,'yid':3,'sheenie':3,'kike':3,'jew':3,'jewish':3,'zionist':3,
    'muzzy':3,'mohamhead':3,'sandnigger':3,'allah':3,'muslim':3,'islamic':3,
    'irish':3,'shamrock':3,'paddy':3,'hibernian':3,'mick':3,
    'polak':3,'pole':3,'polish':3,'dumb pole':3,
    'wop':3,'italian':3,'guido':3,'macaroni':3,'spaghetti':3,'paesano':3,
    'greek':3,'gyp':3,'gypsy':3,'gypo':3,'romani':3,'traveller':3,
    'half caste':3,'halfcaste':3,'mixed breed':3,'race traitor':3,'mongrel':3,
    'half breed':3,'mutt':3,'miscegenation':3,'interracial':3,'crossbreed':3,
    'coconut':3,'banana':3,'oreo':3,'whitewashed':3,'uncle tom':3,
    'indigenous':3,'aboriginal':3,'native american':3,'indian':3,'boomerang':3,
    'aboriginal':3,'koori':3,'abo':3,'aboriginal':3,'blackfella':3,
    
    # Level 3: RELIGIOUS SLURS & HATE SPEECH
    'christian':3,'catholic':3,'baptist':3,'evangelical':3,'fundamentalist':3,
    'mormon':3,'scientology':3,'worship':3,'prayer':3,'sermon':3,'gospel':3,
    'buddha':3,'buddhist':3,'hinduism':3,'hindu':3,'brahmin':3,'dalit':3,
    'atheist':3,'agnostic':3,'secular':3,'heathens':3,'infidel':3,'apostate':3,
    'blasphemy':3,'heresy':3,'sacrilege':3,'desecrate':3,'profane':3,'ungodly':3,
    'devil':3,'satanic':3,'demonic':3,'lucifer':3,'antichrist':3,'666':3,
    
    # Level 3: CASTE/CLASS-BASED DISCRIMINATION
    'untouchable':3,'dalit':3,'outcast':3,'lower class':3,'underclass':3,
    'pauper':3,'peasant':3,'servant':3,'slave':3,'serf':3,'slave trade':3,
    'slavery':3,'colonial':3,'colonialism':3,'colonizer':3,'imperialist':3,
    
    # Level 3: HATEFUL IDEOLOGY TERMS
    'terrorist':3,'terrorism':3,'extremist':3,'radical':3,'jihadist':3,
    'nationalism':3,'supremacy':3,'supremacist':3,'white supremacy':3,
    'nazi':3,'fascist':3,'fascism':3,'dictatorship':3,'totalitarian':3,
    'genocidal':3,'genocide':3,'ethnic cleansing':3,'apartheid':3,'segregation':3,
    'ku klux klan':3,'klan':3,'kkk':3,'arian':3,'aryan':3,'master race':3,
    
    # Level 3: LGBTQ+ SLURS
    'faggot':3,'f slur':3,'butch queen':3,'drag queen':3,'cross dresser':3,
    'gender bender':3,'gender confused':3,'gender deviant':3,'gender rebel':3,
}

SUGGESTIONS = {
    # LEVEL 1 INSULTS & NEGATIVITY
    'idiot':"Try 'I disagree with that' instead.",
    'stupid':"Consider saying 'I see it differently'.",
    'dumb':"Express your frustration more constructively.",
    'moron':"Try 'I think there is a misunderstanding here'.",
    'loser':"Everyone has strengths - try a more respectful tone.",
    'jerk':"Please address behavior respectfully, not with insults.",
    'lame':"Consider expressing disappointment constructively.",
    'ugly':"Focus on actions rather than appearances.",
    'pathetic':"Express criticism constructively rather than emotionally.",
    'worthless':"Every person has value - try a constructive approach.",
    'useless':"Perhaps 'That is not very helpful' expresses your point respectfully.",
    'freak':"Avoid labeling people with derogatory terms.",
    'weirdo':"Diversity in interests and perspectives is valuable.",
    'creep':"Express discomfort respectfully without dehumanizing language.",
    'liar':"Try 'I don't believe that' or ask for clarification.",
    'coward':"Judge actions, not character, in a respectful way.",
    'dummy':"Try using a kinder word like 'confused' or 'mistaken'.",
    'shut up':"Try 'Please let me finish' instead.",
    'dork':"Everyone has unique interests and that's okay.",
    'prick':"Please use more respectful language for disagreement.",
    'twit':"Express your point without personal attacks.",
    'nitwit':"Avoid insulting intelligence - focus on ideas instead.",
    'sucks':"Be specific about what isn't working instead.",
    'fool':"Name-calling decreases productive conversation.",
    'foolish':"Consider saying 'I disagree' instead.",
    'silly':"Different perspectives aren't silly - they're just different.",
    'ridiculous':"Express skepticism respectfully: 'I'm not convinced.'",
    'absurd':"Consider 'That doesn't make sense to me' instead.",
    'nonsense':"Try: 'I don't understand this perspective.'",
    'rubbish':"Express disagreement without dismissal.",
    'daft':"Please avoid name-calling.",
    'goofy':"Playfulness is a positive quality.",
    'obnoxious':"Describe behavior, not character.",
    'juvenile':"Maturity means respectful disagreement.",
    'childish':"Express frustration without insults.",
    'immature':"Focus on the behavior, not the person.",
    'petty':"Consider bigger picture perspectives.",
    'spiteful':"Revenge-focused thinking doesn't help.",
    'vindictive':"Seeking justice constructively is better.",
    'bitter':"Try to move past negative feelings.",
    'resentful':"Address concerns directly and respectfully.",
    'judgmental':"Try to understand before judging.",
    'arrogant':"Humility improves relationships.",
    'conceited':"Self-confidence should never belittle others.",
    'smug':"Respect other people's viewpoints.",
    'pompous':"Humble communication is more persuasive.",
    'self righteous':"Everyone has valid perspectives.",
    'annoying':"Be specific about the behavior bothering you.",
    'irritating':"Address issues calmly instead.",
    'bothersome':"Constructive feedback is more helpful.",
    'tedious':"Consider why you find this person or topic tedious.",
    'grueling':"Difficult doesn't mean the person is bad.",
    'bland':"Everyone has different tastes.",
    'boring':"What's boring to one person excites another.",
    'dull':"Variety in personalities is healthy.",
    'insipid':"Respect differences in interests.",
    'uninspired':"Constructive criticism beats mockery.",
    'mediocre':"Try offering help instead of criticism.",
    'inferior':"Everyone has different strengths.",
    'weak':"Struggle doesn't equal weakness.",
    'feeble':"Support is better than mockery.",
    'miserable':"Offer help if someone seems unhappy.",
    'hopeless':"Problems can be solved with help.",
    'desperate':"Desperation deserves compassion.",
    'doomed':"Negative predictions don't help.",
    'ruined':"Problems can be fixed.",
    'wrecked':"Mistakes are learning opportunities.",
    'botched':"Failure is part of growth.",
    'messed up':"Everyone makes mistakes.",
    'screwed up':"Compassion helps more than judgment.",
    'bastards':"Avoid dehumanizing language.",
    'asses':"Use respectful terms for disagreement.",
    'dopes':"Mockery never improved anyone.",
    'dimwits':"Intelligence varies - that's okay.",
    'chump':"Avoid belittling someone's intelligence.",
    'clown':"Mockery harms relationships.",
    'buffoon':"Everyone deserves respect.",
    'nincompoop':"Avoid childish insults.",
    'incompetent':"Offer constructive feedback instead.",
    
    # LEVEL 2 GENERAL VULGAR/DISRESPECTFUL
    'hate':"Consider 'I strongly disagree with' instead of 'hate'.",
    'disgusting':"Describe what specifically concerns you.",
    'trash':"Express your opinion without derogatory comparisons.",
    'scum':"Please use respectful language to express frustration.",
    'garbage':"Try more constructive descriptors.",
    'filth':"Avoid dehumanizing people or ideas.",
    'pig':"Don't compare people to animals disdainfully.",
    'degenerate':"Avoid extreme negative labels.",
    'ass':"Please use more respectful language.",
    'bastard':"Please choose a more respectful word.",
    'bitch':"Please choose a more respectful term.",
    'damn you':"Express frustration without wishing harm.",
    'stfu':"Try 'Please stop' or 'I prefer quiet right now'.",
    'go to hell':"Avoid wishing harm on others.",
    'piece of garbage':"Avoid dehumanizing language.",
    'piece of trash':"Everyone has value.",
    'fck':"Please use less offensive language.",
    'fck you':"Consider expressing frustration more calmly.",
    'gtfo':"Express disagreement respectfully.",
    'fuck':"Please use less offensive language.",
    'fuck you':"Consider expressing frustration more calmly.",
    'shit':"Consider using less offensive words.",
    'asshole':"Please use more respectful language.",
    'fucking':"Please avoid vulgar intensifiers.",
    'fucking shit':"Remove the vulgar language please.",
    'shitty':"Use descriptive words instead.",
    'bullshit':"Please express your opinion without vulgar language.",
    'horseshit':"Try more professional language.",
    'damn it':"Softening your language helps communication.",
    'dammit':"Try 'This is frustrating' instead.",
    'goddamn':"Please avoid religious exclamations.",
    'hell':"Avoid references to damnation.",
    'bloody hell':"Avoid vulgar exclamations.",
    'blasted':"Choose calmer expressions.",
    'crappy':"Be specific about problems.",
    'junky':"Describe quality without vulgar terms.",
    'lousy':"Try 'not very good' instead.",
    'rotten':"Avoid extreme negativity.",
    'vile':"Express disgust respectfully.",
    'foul':"Describe your concern more constructively.",
    'obscene':"Please avoid offensive language.",
    'vulgar':"Let's keep language respectful.",
    'offensive':"Please reconsider that phrase.",
    'repulsive':"Avoid extreme negative descriptors.",
    'loathsome':"Try less harsh language.",
    'nauseating':"Express concerns without extremes.",
    'sickening':"Be specific instead of extreme.",
    'appalling':"That's a strong reaction - what specifically bothers you?",
    'atrocious':"Extreme criticism doesn't help.",
    'abominable':"Avoid dehumanizing expressions.",
    'odious':"Everyone deserves respect.",
    'despicable':"Criticism should be constructive.",
    'deplorable':"Strong judgment prevents understanding.",
    'shameful':"Shame is harmful - address behavior instead.",
    'scandalous':"Express concerns factually.",
    'outrageous':"Be specific about your concern.",
    'ridiculous':"Try stating your position respectfully.",
    'preposterous':"Extreme reactions don't help dialogue.",
    'absurd':"This perspective may be unfamiliar - seek understanding.",
    'cockamamie':"Try explaining your disagreement.",
    'cockamammy':"Consider the other person's reasoning.",
    
    # LEVEL 2 SEXUAL/ANATOMICAL
    'cock':"This offensive term has no place in respectful conversation.",
    'pussy':"This term is offensive - please use more respectful language.",
    'dick':"This offensive term has no place in respectful conversation.",
    'dildo':"Please avoid explicit sexual references.",
    'anal':"Please avoid explicit sexual terminology.",
    'penis':"Please use anatomical terminology respectfully.",
    'vagina':"Use anatomical terms respectfully in appropriate contexts.",
    'boobs':"Please avoid using body parts as insults.",
    'tits':"Body-shaming language is inappropriate.",
    'nipples':"Sexualized body references are not appropriate here.",
    'cunt':"This is a deeply offensive term - please do not use it.",
    'whore':"This derogatory term is hurtful - please use respectful language.",
    'slut':"This derogatory term is hurtful - please use respectful language.",
    'pimp':"Avoid glorifying harmful relationships.",
    'ho':"This is a derogatory term for people.",
    'prostitute':"Avoid dehumanizing people in sex work.",
    'harlot':"Archaic slurs are still hurtful.",
    'trollop':"Avoid demeaning sexual labels.",
    'strumpet':"Don't use outdated slurs.",
    'floozy':"Avoid stereotyping based on sexuality.",
    'easy':"Don't judge people's sexual choices.",
    'pervert':"Avoid labeling people with derogatory terms.",
    'horny':"Please avoid explicit sexual references.",
    'sexy':"Unsolicited sexual comments aren't appropriate.",
    'porn':"Please avoid explicit sexual content.",
    'pornography':"Explicit content references aren't appropriate here.",
    'xxx':"Please keep conversation appropriate.",
    'masturbat':"Please avoid discussing explicit sexual content.",
    'orgy':"Explicit sexual descriptions aren't appropriate.",
    'gangbang':"Please avoid explicit sexual references.",
    'threesome':"Keep sexual content out of conversation.",
    'fuckbuddy':"Please avoid explicit sexual terminology.",
    'bootycall':"Avoid offensive sexual references.",
    'hookup':"Please avoid explicit sexual terminology.",
    'cumming':"Avoid explicit sexual language.",
    'orgasm':"Please remove explicit sexual content.",
    'creampie':"Explicit sexual content isn't appropriate.",
    'blowjob':"Please avoid explicit sexual terms.",
    'handjob':"Keep explicit content out of chat.",
    'suck my':"This is sexually harassing language.",
    'riding':"Avoid sexually explicit descriptions.",
    'doggy style':"Please keep sexual references out.",
    'missionary':"Sexual content isn't appropriate here.",
    'dominant':"Avoid sexual role-play language.",
    'submissive':"Keep BDSM content out of conversation.",
    'bondage':"Explicit sexual content isn't appropriate.",
    'fetish':"Please avoid sexual content.",
    'kink':"Keep explicit sexuality out of chat.",
    'bdsm':"Sexual practice discussions aren't appropriate.",
    'spanking':"Remove sexual content from conversation.",
    'breast':"Avoid body-focused language.",
    'butt':"Don't use body parts dismissively.",
    'buttocks':"Avoid body-shaming references.",
    'bottom':"Don't sexualize or demean people.",
    'derriere':"Avoid making sexual references.",
    'posterior':"Keep body-focused language respectful.",
    'crotch':"This is an inappropriate reference.",
    'groin':"Use appropriate medical terminology.",
    'genitals':"Be respectful when discussing anatomy.",
    'privates':"Body parts should be discussed respectfully.",
    'loins':"Avoid sexual or violent references.",
    'pubic':"Keep anatomical discussions respectful.",
    'menstrual':"Women's health discussions should be respectful.",
    'period':"Discuss menstruation respectfully.",
    'tampon':"Women's hygiene products are normal.",
    'sanitary':"Women's health is nothing to mock.",
    
    # LEVEL 2 CRUDE BODILY TERMS
    'piss':"Please use more appropriate language.",
    'pissed':"Try 'angry' or 'upset' instead.",
    'pissing':"Please avoid vulgar bathroom references.",
    'arsehole':"Please use more respectful language.",
    'arse':"Please use more respectful language.",
    'fart':"This is crude - please use more appropriate language.",
    'semen':"Use medical terminology respectfully.",
    'cum':"This is crude - please avoid it.",
    'jizz':"Crude sexual slang isn't appropriate.",
    'sperm':"Use clinical terms respectfully.",
    'ejaculate':"Avoid crude sexual terminology.",
    'ejaculation':"Keep clinical discussions respectful.",
    'cumshot':"Explicit sexual content isn't appropriate.",
    'facial':"Avoid explicit sexual references.",
    'jerk off':"Please avoid sexually explicit language.",
    'jerking':"Keep sexual content out of chat.",
    'pee':"Use more appropriate terminology.",
    'peeing':"Avoid crude bathroom humor.",
    'urine':"Medical discussions should stay clinical.",
    'pee on you':"This is inappropriate and harassing.",
    'snot':"Avoid crude references.",
    'mucus':"Use medical terms respectfully.",
    'boogers':"This is crude - use appropriate language.",
    'phlegm':"Keep medical discussions respectful.",
    'spit':"Avoid crude references.",
    'spitting':"This can be threatening - please avoid.",
    'sputum':"Use appropriate medical terminology.",
    'belch':"Crude bathroom humor isn't appropriate.",
    'burp':"Please avoid crude references.",
    'vomit':"Use 'throw up' or medical terms.",
    'puke':"Avoid crude terminology.",
    'barf':"This is crude slang.",
    'gag':"Avoid crude references.",
    'retch':"Use appropriate terminology.",
    'constipation':"Medical discussions should be respectful.",
    'diarrhea':"Keep health discussions clinical.",
    'hemorrhoid':"Medical terms are fine if respectful.",
    'constipated':"Avoid making bathroom functions crude jokes.",
    'shitting':"Use appropriate terminology.",
    'bowel':"Medical terminology is acceptable.",
    'defecate':"Use clinical terms respectfully.",
    'excrement':"Avoid crude body function references.",
    'feces':"Medical terminology is appropriate.",
    'stool':"Clinical terms are fine.",
    'turd':"Avoid crude bathroom humor.",
    'snore':"This is rude - address respectfully.",
    'flatulence':"Crude humor about body functions isn't appropriate.",
    'gas':"Avoid making body functions crude.",
    'intestinal':"Medical discussions should be respectful.",
    'stomach':"Clinical health discussions are fine.",
    'gut':"Avoid crude references.",
    
    # LEVEL 2 OFFENSIVE GENDER/SEXUAL ORIENTATION
    'tranny':"This term is offensive to transgender people.",
    'trans':"Respect transgender identities respectfully.",
    'dyke':"This is an offensive term - please respect all people.",
    'lesbo':"Avoid derogatory terms for lesbians.",
    'homo':"Sexual orientation should never be used as an insult.",
    'queer':"Sexual orientation should never be used as an insult.",
    'fairy':"This is a derogatory fairy term - please avoid.",
    'fag':"This is a deeply offensive slur - do not use it.",
    'pansy':"Avoid using flowers/things as insults.",
    'sissy':"Gender expression shouldn't be mocked.",
    'girly':"It's okay for anyone to like girly things.",
    'feminine':"Femininity isn't weakness.",
    'butch':"Masculine women are valid.",
    'manly':"Toxic masculinity isn't the only way.",
    'masculine':"Masculinity has many expressions.",
    'beta':"This misogynistic ranking system is harmful.",
    'simp':"This term demeans respect for women.",
    'incel':"Involuntary celibacy shouldn't define someone.",
    'chad':"Mocking other body types isn't kind.",
    'thot':"This is a misogynistic slur.",
    'insta thot':"Don't mock women's social media presence.",
    'e girl':"Stop stereotyping online communities.",
    'e boy':"Body and style choices don't define worth.",
    'femboy':"Gender expression is valid.",
    'tomboy':"Girls can like whatever they want.",
    'housewife':"Traditional roles are legitimate choices.",
    'househusband':"Caregiving roles are valuable.",
    'stay at home':"Stay-at-home parents deserve respect.",
    
    # LEVEL 3 VIOLENT THREATS
    'kill yourself':"Please rephrase. If someone is struggling, encourage them to seek support.",
    'kys':"Please rephrase. If someone is struggling, encourage them to seek support.",
    'kill you':"Please rephrase this without violent language.",
    'murder':"Threatening violence is never acceptable.",
    'gonna kill':"Violent threats have no place here.",
    'beat you':"Threatening violence is not acceptable.",
    'beat up':"Violence isn't the answer.",
    'beat down':"Please don't threaten others.",
    'hurt you':"Threatening harm is serious.",
    'injure':"Don't threaten to harm others.",
    'wound':"Violence threatens aren't acceptable.",
    'rape':"This term is deeply harmful. Please rephrase entirely.",
    'violate':"Sexual violence threats are unacceptable.",
    'assault':"Threatening violence violates our policies.",
    'attack':"Don't threaten to harm others.",
    'destroy you':"Threats are never okay.",
    'obliterate':"Violent language isn't acceptable.",
    'annihilate':"Threatening violence isn't tolerated.",
    'wipe out':"Don't make violent threats.",
    'eliminate':"This language suggests violence.",
    'eradicate':"Violent elimination language isn't okay.",
    'exterminate':"People aren't pests - don't dehumanize.",
    'decapitate':"Graphic violence isn't acceptable.",
    'behead':"Don't describe violent acts.",
    'dismember':"Graphic violence isn't allowed.",
    'mutilate':"Violent descriptions harm.",
    'torture':"Threatening torture is serious.",
    'bomb':"Terrorism threats aren't tolerated.",
    'explode':"Violent language isn't acceptable.",
    'blow up':"Don't make threats.",
    'detonate':"Violent threats are serious.",
    'nuke':"Even joking about weapons isn't okay.",
    'nuke you':"Don't threaten others.",
    'die':"Please express disagreement without wishing harm.",
    'drop dead':"Don't wish death on others.",
    'stab you':"Violent threats aren't acceptable.",
    'shoot you':"Don't threaten with weapons.",
    'hang you':"Don't threaten violence.",
    'hang yourself':"Please seek help if struggling.",
    'drown':"Don't describe violence.",
    'drown you':"Violent threats harm.",
    'poison':"Threatening poisoning is serious.",
    'suffocate':"Violent descriptions aren't acceptable.",
    'strangle':"Don't threaten to strangle.",
    'choke':"Violent threats aren't tolerated.",
    'lynching':"This historical violence shouldn't be referenced as threat.",
    'lynched':"Racial violence isn't something to reference.",
    'crucify':"Don't reference religious violence.",
    'burn you':"Threatening to burn someone is serious.",
    'burn alive':"Graphic violence descriptions aren't okay.",
    'immolate':"Don't describe violent acts.",
    'crush you':"Threats aren't acceptable.",
    'flatten':"Don't threaten harm.",
    'smash':"Violent language isn't okay.",
    'pulverize':"Don't make threats.",
    'obliterate':"Violent language isn't acceptable.",
    'vaporize':"Threatening harm isn't okay.",
    'i will hurt':"Threatening violence is serious.",
    'i will kill':"Death threats aren't tolerated.",
    'gonna beat':"Violence threats aren't acceptable.",
    'gonna hit':"Threatening assault isn't okay.",
    'gonna punch':"Don't threaten violence.",
    'you deserve to die':"Don't wish death on others.",
    'die in a fire':"Don't wish harm on others.",
    'go die':"Death wishes aren't acceptable.",
    'hope you die':"Wishing death is serious.",
    'kill your family':"Family violence threats are severe.",
    'hurt your family':"Threats to family members are serious.",
    'rape you':"Sexual violence threats are unacceptable.",
    'rape your':"Sexual assault threats aren't tolerated.",
    'accident':"Don't wish accidents on others.",
    'car crash':"Don't wish harm through accidents.",
    'plane crash':"Death wishes aren't acceptable.",
    'overdose':"Don't wish addiction harm on others.",
    'suicide':"If struggling, please reach out for help.",
    
    # LEVEL 3 RACIST/ETHNIC SLURS
    'nigger':"This is a deeply offensive racial slur and is not tolerated in any context.",
    'nigga':"This racial term is not acceptable in any form.",
    'n word':"This racial slur is not acceptable.",
    'negro':"This archaic term is offensive - don't use it.",
    'negroid':"This pseudo-scientific racism term isn't acceptable.",
    'blackie':"Using skin color as a name is offensive.",
    'darkie':"This racist slur isn't tolerated.",
    'spic':"This is a racial slur - do not use it.",
    'spick':"Spelling variations of slurs aren't acceptable.",
    'wetback':"This is a racial slur - do not use it.",
    'chink':"This is a racial slur - do not use it.",
    'chinamen':"This derogatory term for Chinese people isn't okay.",
    'oriental':"'Asian' is the respectful term.",
    'slant':"This racist slur isn't tolerated.",
    'chinky':"Racist descriptions of eyes aren't acceptable.",
    'gook':"This is a racial slur - do not use it.",
    'slope':"This racist slur isn't acceptable.",
    'jap':"This is a racial slur - do not use it.",
    'japanese':"Use the respectful term 'Japanese.'",
    'asian':"Refer to Asian people respectfully.",
    'orient':"Use 'Asia' instead of this orientalist term.",
    'towelhead':"This is a racial slur - do not use it.",
    'camel jockey':"This is a racial slur - do not use it.",
    'raghead':"This is a racial slur - do not use it.",
    'arab':"Refer to Arabs with respect.",
    'sand nigger':"This compound racial slur is extremely offensive.",
    'paki':"This is a racial slur - do not use it.",
    'curry muncher':"This is a racist slur - do not use it.",
    'dot head':"This racist slur isn't tolerated.",
    'hindi':"Refer to Hindi-speaking people respectfully.",
    'singh':"Names shouldn't be used as slurs.",
    'patel':"Common names aren't appropriate as insults.",
    'beaner':"This is a racial slur - do not use it.",
    'greaser':"This racist slur isn't acceptable.",
    'mexican':"Refer to Mexican people respectfully.",
    'mestizo':"Use 'Mestizo' as a respectful cultural term.",
    'latino':"Use respectful terms for Latin Americans.",
    'chicano':"'Chicano' is a respectful cultural identity.",
    'cracker':"Using racial terms against any group is not acceptable.",
    'redneck':"This is a derogatory term - use respectfully.",
    'hillbilly':"Don't mock rural communities.",
    'white trash':"This is derogatory class/racial language.",
    'trailer trash':"Don't mock people's homes or class.",
    'whitey':"Using racial terms against any group is not acceptable.",
    'honky':"Racial slurs against white people aren't okay either.",
    'white boy':"Don't use race as an insult.",
    'caucasoid':"This pseudo-scientific racist term isn't acceptable.",
    'kyke':"This is a racial slur - do not use it.",
    'yid':"This is a racial slur - do not use it.",
    'sheenie':"This is a racial slur - do not use it.",
    'kike':"This deeply offensive slur isn't tolerated.",
    'jew':"Refer to Jewish people respectfully.",
    'jewish':"Refer respectfully to Jewish people and culture.",
    'zionist':"Political terms shouldn't become slurs.",
    'muzzy':"This is a religious/ethnic slur - do not use it.",
    'mohamhead':"This mocking slur isn't acceptable.",
    'sandnigger':"This extreme slur compounds racism.",
    'allah':"Don't mock religious beliefs.",
    'muslim':"Refer to Muslims respectfully.",
    'islamic':"Islamic culture and religion deserve respect.",
    'irish':"Refer to Irish people respectfully.",
    'shamrock':"Irish symbols aren't appropriate as slurs.",
    'paddy':"This ethnic slur isn't acceptable.",
    'hibernian':"Use respectful terms for Irish people.",
    'mick':"Names shouldn't be used as ethnic slurs.",
    'polak':"This ethnic slur isn't acceptable.",
    'pole':"Use 'Polish' respectfully.",
    'polish':"Refer to Polish people with respect.",
    'dumb pole':"Ethnic jokes perpetuate harmful stereotypes.",
    'wop':"This is an Italian ethnic slur.",
    'italian':"Refer to Italian people respectfully.",
    'guido':"This offensive stereotype isn't acceptable.",
    'macaroni':"Food-based slurs are culturally offensive.",
    'spaghetti':"Stereotyping by food is racist.",
    'paesano':"Don't mock Italian dialects or terms.",
    'greek':"Use 'Greek' respectfully.",
    'gyp':"This shortening of a slur isn't okay.",
    'gypsy':"'Romani' is the respectful term.",
    'gypo':"This slur variant isn't acceptable.",
    'romani':"Use 'Romani' to refer to this ethnic group.",
    'traveller':"Refer to Traveller communities respectfully.",
    'half caste':"This offensive term should never be used to describe people.",
    'halfcaste':"Multiracial people deserve respect, not slurs.",
    'mixed breed':"People aren't animals - don't use this term.",
    'race traitor':"Don't mock interracial relationships.",
    'mongrel':"This dehumanizing term isn't acceptable.",
    'half breed':"Multiracial people are whole people.",
    'mutt':"Comparing people to animals is dehumanizing.",
    'miscegenation':"Interracial relationships are valid.",
    'interracial':"Interracial families should be celebrated.",
    'crossbreed':"Stop using breeding language for humans.",
    'coconut':"This racist stereotype isn't acceptable.",
    'banana':"This racist stereotype isn't acceptable.",
    'oreo':"This racist stereotype isn't acceptable.",
    'whitewashed':"Acculturation isn't betrayal.",
    'uncle tom':"This racist stereotype isn't acceptable.",
    'indigenous':"Use 'Indigenous' respectfully.",
    'aboriginal':"Use 'Aboriginal' respectfully.",
    'native american':"Refer to Native Americans respectfully.",
    'indian':"'Native American' is more respectful now.",
    'boomerang':"Don't use Australian Aboriginal cultural items as slurs.",
    'koori':"This is an Aboriginal identity term - use respectfully.",
    'abo':"This slur for Aboriginal people isn't acceptable.",
    'blackfella':"This isn't an offensive term in context but can be hurtful.",
    
    # LEVEL 3 RELIGIOUS SLURS & HATE SPEECH
    'christian':"Christianity is a valid faith.",
    'catholic':"Catholicism deserves respect.",
    'baptist':"Baptist faith should be respected.",
    'evangelical':"Evangelical Christianity is valid.",
    'fundamentalist':"Religious fundamentalism deserves respectful discussion.",
    'mormon':"Mormonism/The LDS Church deserves respect.",
    'scientology':"All religions deserve basic respect.",
    'worship':"Religious practice isn't a slur.",
    'prayer':"Prayer is a valid spiritual practice.",
    'sermon':"Religious teaching should be respected.",
    'gospel':"Religious texts deserve respect.",
    'buddha':"Buddhism is a valid spiritual path.",
    'buddhist':"Buddhists deserve respect.",
    'hinduism':"Hinduism is a complex, ancient tradition.",
    'hindu':"Hindu believers deserve respect.",
    'brahmin':"Don't make caste insults.",
    'dalit':"Dalit people deserve dignity and respect.",
    'atheist':"Atheism is a valid worldview.",
    'agnostic':"Agnosticism is a legitimate philosophical position.",
    'secular':"Secularism is a valid approach.",
    'heathens':"All people deserve respect regardless of faith.",
    'infidel':"Religious outsider terms are derogatory.",
    'apostate':"Leaving a religion is a personal choice.",
    'blasphemy':"Religious criticism can be respectful.",
    'heresy':"Disagreement with orthodoxy isn't evil.",
    'sacrilege':"Respect different religious values.",
    'desecrate':"Religious items deserve respect.",
    'profane':"Profanity isn't the same as irreligiousness.",
    'ungodly':"Morality exists outside religion too.",
    'devil':"Religious mythology should be discussed respectfully.",
    'satanic':"Satanism is a philosophical position.",
    'demonic':"Supernatural dismissals of people are harmful.",
    'lucifer':"Religious references shouldn't be character attacks.",
    'antichrist':"Religious prophecies shouldn't target people.",
    '666':"Religious symbolism shouldn't be weaponized.",
    
    # LEVEL 3 CASTE/CLASS-BASED DISCRIMINATION
    'untouchable':"The caste system perpetuates harmful discrimination.",
    'dalit':"Dalit people deserve full equality and respect.",
    'outcast':"No one should be cast out of society.",
    'lower class':"Class-based hierarchies harm society.",
    'underclass':"Poverty doesn't make people inferior.",
    'pauper':"Poor people deserve dignity.",
    'peasant':"Rural/agricultural workers deserve respect.",
    'servant':"Service work has dignity and worth.",
    'slave':"Slavery was a grave moral wrong.",
    'serf':"Feudal systems were exploitative.",
    'slave trade':"The transatlantic slave trade was genocide.",
    'slavery':"Modern slavery is a human rights violation.",
    'colonial':"Colonialism caused immense harm.",
    'colonialism':"European colonialism destabilized entire continents.",
    'colonizer':"Acknowledge colonial harm respectfully.",
    'imperialist':"Imperialism damaged countless societies.",
    
    # LEVEL 3 HATEFUL IDEOLOGY TERMS
    'terrorist':"This term is often used as a racist stereotype - please be respectful.",
    'terrorism':"Terrorism merits serious discussion, not accusations.",
    'extremist':"Extremism should be discussed without slurs.",
    'radical':"Radical ideas can be discussed respectfully.",
    'jihadist':"Don't use religious warfare terms as slurs.",
    'nationalism':"Nationalism can be healthily discussed.",
    'supremacy':"White/any supremacy is wrong - this language is hateful.",
    'supremacist':"Supremacist ideologies cause real harm.",
    'white supremacy':"White supremacy is morally wrong.",
    'nazi':"Nazism caused the Holocaust - mention carefully.",
    'fascist':"Fascism caused untold suffering.",
    'fascism':"Fascist ideologies should be discussed factually.",
    'dictatorship':"Dictatorships harm human rights.",
    'totalitarian':"Totalitarian systems are oppressive.",
    'genocidal':"Genocide is a crime against humanity.",
    'genocide':"Genocidal violence is the ultimate atrocity.",
    'ethnic cleansing':"Ethnic cleansing is a grave war crime.",
    'apartheid':"Apartheid was institutionalized racism.",
    'segregation':"Segregation caused incalculable harm.",
    'ku klux klan':"The KKK is a violent hate group.",
    'klan':"The Klan committed terrible racist violence.",
    'kkk':"The KKK's racism and violence are abhorrent.",
    'arian':"Don't use Nazi racial pseudoscience.",
    'aryan':"Don't use corrupted racial terminology.",
    'master race':"No race is a 'master race.'",
    
    # LEVEL 3 LGBTQ+ SLURS
    'faggot':"This is a deeply offensive slur - do not use it.",
    'f slur':"This slur for gay people isn't acceptable.",
    'butch queen':"Gender expressions are valid.",
    'drag queen':"Drag performers deserve respect.",
    'cross dresser':"Cross-dressing is a valid form of expression.",
    'gender bender':"Gender expression shouldn't be mocked.",
    'gender confused':"Transgender people know their gender.",
    'gender deviant':"Gender diversity is normal and valid.",
    'gender rebel':"Gender non-conformity is fine.",
    
    # DEFAULT
    'default':"Please consider rephrasing in a more respectful and constructive way.",
}

SEVERITY_WEIGHTS = {1: 0.20, 2: 0.50, 3: 1.0}


@dataclass
class FilterResult:
    is_toxic: bool = False
    toxicity_score: float = 0.0
    severity: int = 0
    toxic_words: List[str] = field(default_factory=list)
    cleaned_message: str = ""
    suggestion: str = ""
    action: str = "allowed"
    original_message: str = ""


def _normalize(text: str) -> str:
    text = text.lower().translate(LEET_MAP)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def _expand(text: str) -> str:
    for abbr, exp in EXPANSIONS.items():
        text = re.sub(r'\b' + re.escape(abbr) + r'\b', exp, text)
    return text


def _simple_lemmatize(word: str) -> str:
    for suffix in ('ing', 'ies', 'ied', 'ers', 'ed', 'es', 'er', 's'):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


def _find_toxics(text: str) -> List[Tuple[str, int]]:
    found, seen = [], set()
    for phrase, sev in sorted(TOXIC_WORDS.items(), key=lambda x: -len(x[0])):
        if ' ' in phrase:
            if re.search(r'\b' + re.escape(phrase) + r'\b', text):
                if phrase not in seen:
                    seen.add(phrase)
                    found.append((phrase, sev))
    tokens = re.findall(r"[a-z']+", text)
    for tok in tokens:
        for candidate in (tok, _simple_lemmatize(tok)):
            if candidate in TOXIC_WORDS and candidate not in seen:
                seen.add(candidate)
                found.append((candidate, TOXIC_WORDS[candidate]))
                break
    return found


def _clean(original: str, toxic_words: List[str]) -> str:
    """Mask toxic words in-place (used as a fallback)."""
    result = original
    for word in sorted(toxic_words, key=len, reverse=True):
        masked = word[0] + '*' * (len(word) - 2) + word[-1] if len(word) > 2 else '**'
        result = re.sub(r'\b' + re.escape(word) + r'\b', masked, result, flags=re.IGNORECASE)
    return result


def _rephrase_without_toxics(original: str, toxic_words: List[str]) -> str:
    """
    Build a toxic-free version of the sentence by removing toxic words/phrases,
    then cleaning up the grammar a bit.

    Example:
      "fucking shit i dont want to do it"
        -> "I don't want to do it."
    """
    if not original:
        return ""

    text = original

    # Remove toxic phrases/words entirely (handle variations like fuck/fucking/fucked)
    for word in sorted(set(toxic_words), key=len, reverse=True):
        # Pattern matches the word with optional common suffixes
        pattern = r'\b' + re.escape(word) + r'(?:ed|ing|er|s)?\b'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Collapse repeated punctuation and whitespace
    text = re.sub(r'[!?\.]{2,}', '.', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # If everything was just insults, fall back to a neutral sentence
    if not text:
        return "I feel upset about this."

    # Clean up remaining punctuation and spacing issues
    text = re.sub(r'\s+([,.!?])', r'\1', text)  # Fix space before punctuation
    text = re.sub(r'([,.!?])\s+', r'\1 ', text)  # Fix punctuation spacing
    text = re.sub(r'\s+', ' ', text).strip()  # Final cleanup

    # Handle incomplete sentences by adding appropriate words
    # If sentence ends with determiners or incomplete phrases
    incomplete_patterns = [
        r'\bYou are such an?\s*$',
        r'\bThis is\s*$',
        r'\bI\s+my\s*$',
        r'\bYou\s+\w+\s+of\s*$',
        r'\bYou\s*$'
    ]
    
    for pattern in incomplete_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            # Generate contextually appropriate completion
            if 'you are such' in text.lower():
                text = "I disagree with your perspective."
            elif 'this is' in text.lower():
                text = "This is not good."
            elif 'i my' in text.lower():
                text = "I have concerns about this."
            elif 'you' in text.lower() and 'piece of' in text.lower():
                text = "I disagree with you."
            elif text.lower().strip() == 'you':
                text = "I want to address this with you."
            break

    # Normalize some common contractions / phrasing
    repl_map = {
        r"\bdont\b": "don't",
        r"\bdo nt\b": "don't", 
        r"\bwont\b": "won't",
        r"\bcan t\b": "can't",
        r"\bim\b": "I'm",
        r"\bi\b": "I",
    }
    for pat, rep in repl_map.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)

    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]

    # If the sentence looks like a refusal, optionally prepend a polite "No,"
    if re.search(r"\b(i\s+don['’]t\s+want\s+to\b)", text, flags=re.IGNORECASE):
        if not text.lower().startswith("no"):
            text = "No, " + text[0].lower() + text[1:]

    # Ensure it ends with a period if it has words but no strong punctuation
    if text and text[-1] not in ".!?":
        text = text + "."

    return text


def _suggest(toxic_words: List[str]) -> str:
    for w in toxic_words:
        if w in SUGGESTIONS:
            return SUGGESTIONS[w]
    return SUGGESTIONS['default']


# ── Simple ML model (TF–IDF + Logistic Regression) ─────────────────────────────

_VECTORIZER = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
_CLF = LogisticRegression(max_iter=1000)


def _train_model():
    """Train a tiny in-memory classifier for toxic vs clean text."""
    toxic_samples = [
        # Level 1 Insults
        "you are an idiot",
        "you are so stupid",
        "you dumb loser",
        "you are such a moron",
        "that is so lame",
        "youre so foolish",
        "what a silly person",
        "youre being ridiculous",
        "thats complete nonsense",
        
        # Level 2 Moderate Vulgar
        "this is bullshit",
        "fucking hell",
        "this is horseshit",
        "stop being a bitch",
        "youre being a coward",
        "go to hell",
        "fuck off",
        "what the hell",
        "oh shit",
        "damn it",
        "goddamn it",
        
        # Level 2 Sexual Terms
        "youre such a whore",
        "stop being a slut",
        "youre a pussy",
        "youre a dick",
        "stop being such a pervert",
        "thats disgusting porn material",
        "youre so horny",
        "stop your sexual harassment",
        
        # Level 2 Crude Bodily
        "stop pissing me off",
        "piss off",
        "youre being disgusting",
        "thats vile",
        "youre being disgusting and filthy",
        
        # Level 2 Gender/Orientation Slurs
        "stop being such a tranny",
        "youre a dyke",
        "dont be such a homo",
        "youre too gay",
        
        # Level 3 Violent Threats
        "kill yourself now",
        "kys loser",
        "i will kill you",
        "i am gonna kill you",
        "i will beat you up",
        "i hope you die",
        "drop dead",
        "i will stab you",
        "i will shoot you",
        "i hope you hang yourself",
        "go die in a fire",
        "i will burn you",
        "you deserve to die",
        "i will hurt you",
        "i will punch you in the face",
        "i will destroy you",
        "i will murder you",
        "bomb attack on you",
        
        # Level 3 Racist Slurs
        "those people are inferior",
        "certain ethnic groups cause problems",
        "i dont like those types",
        "we should exclude certain people",
        "those immigrants are ruining things",
        "people from that country are lazy",
        "dont trust anyone from that race",
        "certain groups are dangerous",
        "racial discrimination is good",
        "i hate people who look like that",
        
        # Level 3 Religious/Caste Slurs
        "all members of that religion are bad",
        "lower caste people are inferior",
        "people without my beliefs are wrong",
        
        # Level 3 Hateful Ideology
        "white supremacy is right",
        "genocide would solve problems",
        "segregation was good",
        "i support ethnic cleansing",
        "fascism is the answer",
        "nazi ideology is correct",
    ]

    clean_samples = [
        "hello how are you",
        "have a great day",
        "i disagree with this idea",
        "can we talk about this calmly",
        "i do not like this approach",
        "this could be better",
        "please explain your point",
        "i think there is a misunderstanding",
        "thank you for your help",
        "let us try another solution",
        "that was not very helpful",
        "can you clarify what you mean",
        "this is frustrating but we can fix it",
        "i strongly disagree with that",
        "let us take a break and return later",
        "i see things differently",
        "that does not work for me",
        "can we discuss this respectfully",
        "i have concerns about this approach",
        "perhaps we should reconsider",
        "i respect your opinion",
        "lets find common ground",
        "i appreciate your perspective",
        "your suggestion has merit",
        "i understand your concern",
        "lets work together",
        "this could use improvement",
        "i have a different view",
        "what do you think about this",
        "im interested in your thoughts",
        "can you help me understand",
        "lets collaborate on this",
        "i value your input",
        "thanks for the feedback",
        "this is interesting",
        "i had not considered that",
        "thats a fair point",
        "lets hear what others think",
        "diversity of ideas is good",
        "everyone deserves respect",
        "all people matter",
        "we should include everyone",
        "different backgrounds are valuable",
        "unity strengthens us",
        "peace is better than conflict",
        "kindness matters",
        "lets be respectful",
        "im here to help",
        "lets support each other",
    ]

    texts = toxic_samples + clean_samples
    labels = [1] * len(toxic_samples) + [0] * len(clean_samples)

    X = _VECTORIZER.fit_transform(texts)
    _CLF.fit(X, labels)


_train_model()


def analyze_message(text: str, block_threshold: float = 0.70, warn_threshold: float = 0.15) -> FilterResult:
    """Analyze a message and decide whether to allow / warn / block."""
    original = text or ""
    norm = _normalize(original)
    expanded = _expand(norm)

    # ML-based toxicity probability
    try:
        X = _VECTORIZER.transform([expanded])
        proba = float(_CLF.predict_proba(X)[0][1])
    except Exception:
        proba = 0.0

    # Keyword-based toxic word detection for masking + suggestions
    found = _find_toxics(expanded)
    toxic_words = [w for w, _ in found]
    max_sev = max((s for _, s in found), default=0)

    # Prefer a true rephrased, toxic-free sentence over simple masking
    if toxic_words:
        cleaned = _rephrase_without_toxics(original, toxic_words)
        # Fallback to masking if rephrase somehow became empty
        if not cleaned.strip():
            cleaned = _clean(original, toxic_words)
    else:
        cleaned = original
    suggestion = _suggest(toxic_words) if toxic_words else ""

    # Decision logic: toxic words take priority over ML score
    # If toxic words found, always warn/block based on severity
    if toxic_words:
        if max_sev >= 3:  # High severity words (violence, harassment)
            action = 'blocked'
        else:  # Lower severity toxic words
            action = 'warned'
    elif proba >= block_threshold:  # No toxic words but high ML score
        action = 'blocked'
    elif proba >= warn_threshold:  # No toxic words but moderate ML score
        action = 'warned'
    else:
        action = 'allowed'

    is_toxic = action in ('warned', 'blocked') and bool(toxic_words)

    return FilterResult(
        is_toxic=is_toxic,
        toxicity_score=round(proba, 3),
        severity=max_sev,
        toxic_words=toxic_words,
        cleaned_message=cleaned,
        suggestion=suggestion if is_toxic else "",
        action=action,
        original_message=original,
    )


def get_severity_label(score: float) -> str:
    if score < 0.2:
        return 'Clean'
    if score < 0.4:
        return 'Mild'
    if score < 0.7:
        return 'Moderate'
    return 'Severe'


if __name__ == '__main__':
    tests = [
        "Hello how are you",
        "You are such an idiot",
        "I hate this stupid idea",
        "k1ll yours3lf loser",
        "This crap is garbage trash",
        "fuck you you loser",
        "I think we can improve this",
    ]
    for t in tests:
        r = analyze_message(t)
        print(f"\nInput  : {t}\nScore  : {r.toxicity_score:.3f}  Action: {r.action}")
        print(f"Words  : {r.toxic_words}")
        print(f"Clean  : {r.cleaned_message}")
        print(f"Suggest: {r.suggestion}")
