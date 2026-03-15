#!/usr/bin/env python3
"""
test_dataset_phrases.py - Test with exact phrases from the datasets
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from nlp_filter import analyze_message
from enhanced_ml_retrieval import enhanced_generate_ml_suggestions

def test_exact_dataset_phrases():
    """Test with exact phrases that were in the training datasets."""
    
    print("Testing Exact Dataset Phrases")
    print("=" * 50)
    
    # Exact phrases from the datasets
    dataset_phrases = [
        "shut the fuck up",
        "this system is stupid", 
        "stop being dumb",
        "this game is fucking trash",
        "go fuck yourself",
        "you're a dumbass",
        "this code is shit",
        "this project is bullshit"
    ]
    
    for phrase in dataset_phrases:
        print(f"\nPhrase: {phrase}")
        print("-" * 40)
        
        # Analyze the phrase
        result = analyze_message(phrase)
        print(f"Toxic Words: {result.toxic_words}")
        print(f"Action: {result.action}")
        
        # Get enhanced ML suggestions
        ml_suggestions = enhanced_generate_ml_suggestions(0, phrase, result.toxic_words)
        
        print(f"\nEnhanced ML Suggestions ({len(ml_suggestions)}):")
        for i, sugg in enumerate(ml_suggestions, 1):
            text = sugg.get('text', 'N/A')
            confidence = sugg.get('confidence', 0)
            sugg_type = sugg.get('type', 'unknown')
            hint = sugg.get('hint', 'No hint')
            
            print(f"  {i}. {text}")
            print(f"     Type: {sugg_type}")
            print(f"     Confidence: {confidence:.2f}")
            print(f"     Hint: {hint}")
        
        print()

if __name__ == "__main__":
    test_exact_dataset_phrases()
