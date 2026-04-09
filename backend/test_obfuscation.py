#!/usr/bin/env python3
"""Quick test of obfuscation handling in nlp_filter."""

from nlp_filter import analyze_message

test_cases = [
    "sh1t",          # Should detect: 1 -> i
    "fvck",          # Should detect: v -> u
    "sh1t you",      # Combined
    "fvck th1s",     # Combined
    "fuck",          # Normal (baseline)
    "shit",          # Normal (baseline)
    "hello world",   # Clean (baseline)
]

print("=" * 60)
print("OBFUSCATION FILTER TEST")
print("=" * 60)

for msg in test_cases:
    result = analyze_message(msg)
    print(f"\nMessage: '{msg}'")
    print(f"  Action: {result.action.upper()}")
    print(f"  Toxicity Score: {result.toxicity_score}")
    print(f"  Toxic Words Found: {result.toxic_words}")
    print(f"  Severity: {result.severity}")
    print(f"  Suggestion: {result.suggestion if result.suggestion else '(none)'}")

print("\n" + "=" * 60)
