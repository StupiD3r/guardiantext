#!/usr/bin/env python3
"""
test_trained_ml.py - Test the trained ML system with examples from datasets
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from learning_suggestions import generate_ml_suggestions, get_user_learning_profile
from nlp_filter import analyze_message

def test_dataset_examples():
    """Test ML system with examples that were in the training datasets."""
    
    print("Testing Trained ML System with Dataset Examples")
    print("=" * 60)
    
    # Examples from the datasets
    test_cases = [
        {
            "original": "shut the fuck up",
            "expected_clean": "please be quiet",
            "context": "personal"
        },
        {
            "original": "this system is stupid", 
            "expected_clean": "this system has design issues",
            "context": "work"
        },
        {
            "original": "stop being dumb",
            "expected_clean": "please think more carefully", 
            "context": "general"
        },
        {
            "original": "this game is fucking trash",
            "expected_clean": "this game is not good",
            "context": "general"
        },
        {
            "original": "go fuck yourself",
            "expected_clean": "please leave me alone",
            "context": "personal"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['original']}")
        print(f"Expected from dataset: {test_case['expected_clean']}")
        print("-" * 50)
        
        # Analyze the message
        result = analyze_message(test_case['original'])
        print(f"Toxic Words: {result.toxic_words}")
        print(f"Action: {result.action}")
        
        # Get ML suggestions
        try:
            ml_suggestions = generate_ml_suggestions(0, test_case['original'], result.toxic_words)
            print(f"\nML Suggestions ({len(ml_suggestions)} found):")
            
            for j, sugg in enumerate(ml_suggestions):
                confidence = sugg.get('confidence', 0)
                text = sugg.get('text', 'N/A')
                print(f"  {j+1}. {text} (confidence: {confidence:.2f})")
                
                # Check if it matches the expected clean version
                if test_case['expected_clean'].lower() in text.lower() or text.lower() in test_case['expected_clean'].lower():
                    print(f"     *** MATCHES DATASET EXPECTATION! ***")
            
        except Exception as e:
            print(f"Error getting ML suggestions: {e}")
        
        print()

def check_learning_profile():
    """Check what the ML system has learned."""
    
    print("Checking ML Learning Profile")
    print("=" * 40)
    
    try:
        profile = get_user_learning_profile(0)
        
        print(f"Total suggestions learned: {len(profile.get('effective_suggestions', []))}")
        print(f"Total patterns learned: {len(profile.get('communication_patterns', []))}")
        
        print("\nTop learned suggestions:")
        effective_suggestions = profile.get('effective_suggestions', [])
        for i, sugg in enumerate(effective_suggestions[:10]):
            if isinstance(sugg, (list, tuple)) and len(sugg) >= 3:
                sugg_type, context, effectiveness = sugg[:3]
                print(f"  {i+1}. Type: {sugg_type}, Context: {context}, Effectiveness: {effectiveness:.2f}")
        
        print("\nCommunication patterns:")
        patterns = profile.get('communication_patterns', [])
        for i, pattern in enumerate(patterns[:5]):
            print(f"  {i+1}. {pattern}")
            
    except Exception as e:
        print(f"Error checking learning profile: {e}")

if __name__ == "__main__":
    check_learning_profile()
    test_dataset_examples()
