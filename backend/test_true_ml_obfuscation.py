#!/usr/bin/env python3
"""Test True ML obfuscation detection."""

from true_ml_toxicity import analyze_with_true_ml

test_messages = [
    "well fvck",
    "well fuck",
    "sh1t",
    "shit",
    "fvck th1s",
    "hello world",
]

print("=" * 60)
print("TRUE ML OBFUSCATION TEST")
print("=" * 60)

for msg in test_messages:
    result = analyze_with_true_ml(msg)
    print(f"\nMessage: '{msg}'")
    print(f"  Is Toxic: {result.is_toxic}")
    print(f"  Score: {result.toxicity_score:.3f}")
    print(f"  Severity: {result.severity}")
    print(f"  Toxic Words: {[tw.word for tw in result.toxic_words]}")
    print(f"  Suggestion: {result.clean_suggestion}")

print("\n" + "=" * 60)
