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
}

TOXIC_WORDS = {
    'idiot':1,'stupid':1,'dumb':1,'moron':1,'loser':1,'jerk':1,'lame':1,
    'ugly':1,'pathetic':1,'worthless':1,'useless':1,'freak':1,'weirdo':1,
    'creep':1,'liar':1,'coward':1,'dummy':1,'shut up':1,'crap':1,
    'damn':1,'dork':1,'prick':1,'twit':1,'nitwit':1,
    'hate':2,'disgusting':2,'trash':2,'scum':2,'garbage':2,'filth':2,
    'pig':2,'degenerate':2,'ass':2,'bastard':2,'bitch':2,'damn you':2,
    'stfu':2,'go to hell':2,'piece of garbage':2,'piece of trash':2,
    'fck':2,'fck you':2,'gtfo':2,'fuck':2,'fuck you':2,'shit':2,'asshole':2,
    'fucking':2,'fucking shit':2,
    'kill yourself':3,'kys':3,'kill you':3,'murder':3,'gonna kill':3,
    'beat you':3,'hurt you':3,'rape':3,'destroy you':3,'bomb':3,
    'die':3,'drop dead':3,
}

SUGGESTIONS = {
    'idiot':"Try 'I disagree with that' instead.",
    'stupid':"Consider saying 'I see it differently'.",
    'dumb':"Express your frustration more constructively.",
    'moron':"Try 'I think there is a misunderstanding here'.",
    'loser':"Everyone has strengths - try a more respectful tone.",
    'ugly':"Focus on actions rather than appearances.",
    'worthless':"Every person has value - try a constructive approach.",
    'useless':"Perhaps 'That is not very helpful' expresses your point respectfully.",
    'hate':"Consider 'I strongly disagree with' instead of 'hate'.",
    'trash':"Express your opinion without derogatory comparisons.",
    'scum':"Please use respectful language to express frustration.",
    'bastard':"Please choose a more respectful word.",
    'bitch':"Please choose a more respectful term.",
    'ass':"Please use more respectful language.",
    'asshole':"Please use more respectful language.",
    'crap':"Consider saying 'This is not good' instead.",
    'damn':"Consider softening your language.",
    'shut up':"Try 'Please let me finish' instead.",
    'kill yourself':"Please rephrase. If someone is struggling, encourage them to seek support.",
    'kys':"Please rephrase. If someone is struggling, encourage them to seek support.",
    'die':"Please express disagreement without wishing harm.",
    'kill you':"Please rephrase this without violent language.",
    'rape':"This term is deeply harmful. Please rephrase entirely.",
    'fuck':"Please use less offensive language.",
    'fuck you':"Consider expressing frustration more calmly.",
    'fck':"Please use less offensive language.",
    'fck you':"Consider expressing frustration more calmly.",
    'stfu':"Try 'Please stop' or 'I prefer quiet right now'.",
    'shit':"Consider using less offensive words.",
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
        "you are an idiot",
        "you are so stupid",
        "you dumb loser",
        "you are such a moron",
        "kill yourself now",
        "kys loser",
        "i hate you so much",
        "you are worthless garbage",
        "shut up you freak",
        "go to hell",
        "fuck you",
        "you are a bitch",
        "you piece of shit",
        "this is crap trash",
        "drop dead",
        "i will kill you",
        "i am gonna kill you",
        "i will beat you up",
        "i hope you die",
        "what a disgusting pig",
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
