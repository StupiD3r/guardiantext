#!/usr/bin/env python3
"""Test ML fix directly."""

from true_ml_toxicity import analyze_with_true_ml

test_cases = [
    ("hello world", False),  # Should be clean
    ("hi there", False),      # Should be clean
    ("fuck you", True),       # Should be toxic
    ("thanks", False),        # Should be clean
    ("you're amazing", False), # Should be clean
]

print("=" * 60)
print("ML FALSE POSITIVE FIX TEST")
print("=" * 60)

for msg, should_be_toxic in test_cases:
    result = analyze_with_true_ml(msg)
    status = "✅" if result.is_toxic == should_be_toxic else "❌"
    print(f"\n{status} Message: '{msg}' (Expected: {'TOXIC' if should_be_toxic else 'CLEAN'})")
    print(f"  Is Toxic: {result.is_toxic} (Score: {result.toxicity_score:.3f})")
    print(f"  Toxic Words: {[tw.word for tw in result.toxic_words]}")

print("\n" + "=" * 60)
