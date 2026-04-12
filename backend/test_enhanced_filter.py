#!/usr/bin/env python3
"""
Test script to verify enhanced word filtering for vulgar and racist terms.
"""

from nlp_filter import analyze_message

# Test cases for vulgar words
vulgar_tests = [
    ("This is penis", "Vulgar sexual term"),
    ("You are such a pussy", "Vulgar sexual term"),
    ("Stop being such a cock", "Male sexual term"),
    ("That's bullshit", "Moderate vulgar"),
    ("Go fuck yourself", "Severe vulgar"),
]

# Test cases for racist/offensive terms
racist_tests = [
    ("I don't like those people", "Potential racial bias"),
    ("This group of people is inferior", "Racist statement"),
    ("certain ethnic groups cause problems", "Ethnic stereotype"),
]

# Test cases that should pass
clean_tests = [
    ("I disagree with your approach", "Respectful disagreement"),
    ("Can we discuss this calmly", "Clean message"),
    ("Thank you for your help", "Positive message"),
]

print("=" * 60)
print("ENHANCED WORD FILTER TEST RESULTS")
print("=" * 60)

# Test vulgar words
print("\n[VULGAR WORDS TEST]")
print("-" * 60)
for message, description in vulgar_tests:
    result = analyze_message(message)
    print(f"\nMessage: '{message}'")
    print(f"Description: {description}")
    print(f"Toxic: {result.is_toxic}")
    print(f"Score: {result.toxicity_score:.2f}")
    print(f"Severity: {result.severity}")
    print(f"Toxic Words Found: {result.toxic_words}")
    print(f"Action: {result.action}")
    if result.suggestion:
        print(f"Suggestion: {result.suggestion}")

# Test racist/offensive content
print("\n" + "=" * 60)
print("[RACIST/OFFENSIVE CONTENT TEST]")
print("-" * 60)
for message, description in racist_tests:
    result = analyze_message(message)
    print(f"\nMessage: '{message}'")
    print(f"Description: {description}")
    print(f"Toxic: {result.is_toxic}")
    print(f"Score: {result.toxicity_score:.2f}")
    print(f"Severity: {result.severity}")
    print(f"Toxic Words Found: {result.toxic_words}")
    print(f"Action: {result.action}")
    if result.suggestion:
        print(f"Suggestion: {result.suggestion}")

# Test clean messages
print("\n" + "=" * 60)
print("[CLEAN MESSAGES TEST]")
print("-" * 60)
for message, description in clean_tests:
    result = analyze_message(message)
    print(f"\nMessage: '{message}'")
    print(f"Description: {description}")
    print(f"Toxic: {result.is_toxic}")
    print(f"Score: {result.toxicity_score:.2f}")
    print(f"Action: {result.action}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
