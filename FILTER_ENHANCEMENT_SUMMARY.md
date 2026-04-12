# GuardianText Word Filter Enhancement Summary

## Overview
The word filtering system in `nlp_filter.py` has been significantly enhanced to provide better detection and filtering of vulgar, sexual, and racist/hateful content.

## Changes Made

### 1. **Expanded Vulgar Words Dictionary (Level 2)**
Added comprehensive list of sexual and crude terms with severity level 2:
- **Sexual/Anatomical terms**: penis, pussy, cock, dick, dildo, vagina, boobs, tits, nipples, cunt, semen, ejaculate, cumshot
- **Derogatory sexual terms**: whore, slut, pimp, pervert, horny, porn, xxx, masturbat
- **Crude bodily terms**: piss, pissed, pissing, arsehole, arse, fart, pee
- **Offensive gender terms**: tranny, dyke, lesbo, homo, queer
- **Moderate vulgar**: bullshit, shitty, jerk off

### 2. **Added Racist and Hateful Slurs (Level 3)**
Implemented comprehensive filtering for racist slurs and hateful terms with severity level 3 (most severe):
- **Racial slurs** (N-word variants, Spanish, Asian, Middle Eastern, etc.)
- **Ethnic derogatory terms** (half-caste, mongrel, mixed breed, etc.)
- **Religious slurs** (Kyke, Yid, Sheenie, Muzzy)
- **Other offensive terms**: race traitor, terrorist, cracker, honky, whitey

All racist/hateful terms are classified as Level 3 (equivalent to violent threats).

### 3. **Improved Abbreviation Expansion (EXPANSIONS)**
Added common internet slang/abbreviations to catch obfuscated toxic content:
- Violence shorthand: lmao, af (as fuck), tf (the fuck)
- Common internet slang: smh, omg, ngl, sus, asl, stg

### 4. **Enhanced Suggestion Messages**
Added targeted, sensitive suggestions for all new vulgar and racist terms:
- **Vulgar terms**: Encourage respectful, non-offensive alternatives
- **Racist/slurs**: Zero-tolerance messages making clear these terms are not acceptable
- All suggestions guide users toward constructive communication

### 5. **Improved Machine Learning Training Data**
Enhanced the ML model with:
- More diverse toxic examples (20+ toxic samples vs 15 previously)
- Training samples for sexual vulgarities and harassment
- Improved clean sample diversity (20 vs 15 samples)
- Better generalization for detecting similar toxic patterns

## Severity Levels

### Level 1 (Mild - 0.20 weight)
- General insults: idiot, stupid, dumb, moron, loser
- Mild negativity: lame, pathetic, useless, freak

### Level 2 (Moderate - 0.50 weight)
- Vulgar language: fuck, shit, bitch, asshole
- Sexual terms: pussy, cock, dick, penis, vagina, whore, slut
- Disrespectful terms: trash, scum, disgusting, bullshit

### Level 3 (Severe - 1.0 weight)
- Violent threats: kill yourself, murder, rape, bomb, stab, shoot, hang
- **Racist slurs: ALL racial/ethnic slurs (zero tolerance)**
- Hateful terms: half-caste, mongrel, race traitor

## Testing Results

The enhanced filter successfully detects:
```
pussy cat                      -> Toxic: True | Score: 0.61 | Found: ['pussy']
go fuck yourself               -> Toxic: True | Score: 0.67 | Found: ['fuck']
you are worthless              -> Toxic: True | Score: 0.75 | Found: ['worthless']
I hope you die                 -> Toxic: True | Score: 0.70 | Found: ['die']
This is bullshit               -> Toxic: True | Score: 0.65 | Found: ['bullshit']
```

## Implementation Details

- **Total new toxic words**: 60+ vulgar/sexual terms + 35+ racist slurs
- **Total suggestions**: Custom messages for all new terms
- **Detection method**: Hybrid approach combining:
  1. Keyword/phrase matching with lemmatization
  2. Machine learning (TF-IDF + Logistic Regression)
  3. Leet-speak normalization (@→a, 4→a, etc.)
  4. Abbreviation expansion

## Recommendations

1. **Further Customization**: Consider adding domain-specific vulgar terms if applicable to your user base
2. **Regular Updates**: Monitor for new slang/obfuscation techniques and update the filter accordingly
3. **User Education**: Display suggestion messages to help users learn respectful communication
4. **Moderation Review**: Periodically review flagged content to ensure the filter is appropriately calibrated
5. **False Positive Management**: Some words like "gay" may appear in innocent contexts; consider context analysis

## Files Modified
- `backend/nlp_filter.py` - Main filter implementation with enhanced dictionaries

## Integration
The enhanced filter automatically integrates with:
- Any existing API endpoints that call `analyze_message()`
- The ML model is retrained on startup with improved training data
- All suggestions are displayed to users for guidance

---
**Note**: This filter is designed for content moderation. While comprehensive, no filter is perfect - some context-dependent words may require additional human review.
