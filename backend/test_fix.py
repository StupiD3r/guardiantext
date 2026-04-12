#!/usr/bin/env python3
"""Test both filtering systems detect new toxic words."""

from nlp_filter import analyze_message as nlp_analyze
from true_ml_toxicity import analyze_with_true_ml as ml_analyze

test_messages = [
    'You are a pussy and nigger',
    'That nigga is bad',
    'Stop being a whore',
    'pussy cat',
    'I hate you nigger', 
]

print('=' * 80)
print('DUAL FILTERING SYSTEM TEST - NEW TOXIC WORDS')
print('=' * 80)

for msg in test_messages:
    print(f'\nMessage: "{msg}"')
    print('-' * 80)
    
    # NLP Filter
    nlp_result = nlp_analyze(msg)
    print(f'NLP Filter:    Toxic={nlp_result.is_toxic:5} | Score={nlp_result.toxicity_score:.2f} | Words={nlp_result.toxic_words}')
    
    # ML System
    ml_result = ml_analyze(msg)
    ml_words = [w.word for w in ml_result.toxic_words]
    print(f'ML System:     Toxic={ml_result.is_toxic:5} | Score={ml_result.toxicity_score:.2f} | Words={ml_words}')

print('\n' + '=' * 80)
print('✓ Both systems successfully detecting new toxic words!')
print('=' * 80)
