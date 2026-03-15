#!/usr/bin/env python3
"""
train_datasets.py - Train GuardianText ML system with the available datasets
"""

import csv
import os
import sys
from typing import List, Dict

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from learning_suggestions import init_learning_db, learn_from_user_choice

def detect_context(toxic_sentence: str, clean_sentence: str) -> str:
    """Detect the context type based on message content."""
    
    toxic_lower = toxic_sentence.lower()
    clean_lower = clean_sentence.lower()
    
    # School/education context
    if any(word in toxic_lower for word in ['school', 'homework', 'exam', 'class', 'teacher', 'assignment', 'project']):
        return 'education'
    
    # Work/professional context
    if any(word in toxic_lower for word in ['work', 'job', 'boss', 'deadline', 'project', 'task', 'meeting', 'system']):
        return 'work'
    
    # Personal conflict
    if any(word in toxic_lower for word in ['you', 'your', 'personally', 'feel', 'think']):
        return 'personal'
    
    # General frustration
    if any(word in toxic_lower for word in ['this', 'that', 'game', 'code', 'feature', 'idea', 'explanation']):
        return 'general'
    
    return 'general'

def generate_multiple_responses(toxic_sentence: str, clean_sentence: str, context: str) -> List[str]:
    """Generate multiple alternative responses based on the clean sentence."""
    
    responses = [clean_sentence]  # Primary response from dataset
    
    # Generate alternatives based on context
    if context == 'education':
        alternatives = [
            "I'm finding this challenging to understand.",
            "Could you explain this differently?",
            "I need help with this material.",
            "Let's work through this together."
        ]
    elif context == 'work':
        alternatives = [
            "I have concerns about this approach.",
            "Let's discuss this professionally.",
            "I'd like to suggest an alternative.",
            "This may need further review."
        ]
    elif context == 'personal':
        alternatives = [
            "I see things differently.",
            "Let's respect each other's views.",
            "I'd like to communicate constructively.",
            "We may need to find common ground."
        ]
    else:  # general
        alternatives = [
            "This could be improved.",
            "I have some feedback on this.",
            "Let's approach this differently.",
            "This needs some adjustment."
        ]
    
    # Add 2-3 alternatives (avoiding duplicates)
    for alt in alternatives:
        if alt not in responses and len(responses) < 4:
            responses.append(alt)
    
    return responses[:4]  # Ensure max 4 responses

def extract_toxic_words(toxic_sentence: str) -> List[str]:
    """Extract toxic words from the sentence using the known toxic words list."""
    
    # Import from backend
    try:
        from nlp_filter import _find_toxics, _normalize, _expand
        
        # Use the same detection as the main system
        norm = _normalize(toxic_sentence)
        expanded = _expand(norm)
        found = _find_toxics(expanded)
        toxic_words = [w for w, _ in found]
        return toxic_words
    except:
        # Fallback: simple keyword detection
        known_toxic = ['fuck', 'shit', 'damn', 'hell', 'bitch', 'ass', 'crap', 'stupid', 'dumb', 'idiot', 'moron', 'jerk', 'loser', 'bullshit', 'bullshit', 'bullshit']
        toxic_lower = toxic_sentence.lower()
        return [word for word in known_toxic if word in toxic_lower]

def train_from_simple_csv(csv_file_path: str):
    """Train ML system from simple toxic/clean CSV format."""
    
    print(f"Training from: {csv_file_path}")
    print("-" * 50)
    
    if not os.path.exists(csv_file_path):
        print(f"Error: File {csv_file_path} not found!")
        return
    
    # Initialize ML database
    print("Initializing ML database...")
    init_learning_db()
    
    examples_processed = 0
    interactions_created = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    toxic_sentence = row.get('toxic_sentence', '') or row.get('idiot', '')  # Handle different column names
                    clean_sentence = row.get('clean_sentence', '')
                    
                    if not toxic_sentence or not clean_sentence:
                        continue
                    
                    # Extract toxic words
                    toxic_words = extract_toxic_words(toxic_sentence)
                    
                    if not toxic_words:
                        # If no toxic words detected, skip or add common ones
                        toxic_words = ['general_toxicity']
                    
                    # Detect context
                    context = detect_context(toxic_sentence, clean_sentence)
                    
                    # Generate multiple responses
                    responses = generate_multiple_responses(toxic_sentence, clean_sentence, context)
                    
                    # Generate effectiveness scores (primary response gets highest score)
                    effectiveness_scores = [0.9, 0.7, 0.6, 0.5][:len(responses)]
                    
                    examples_processed += 1
                    
                    # Train the ML system with each response
                    for i, (response, effectiveness) in enumerate(zip(responses, effectiveness_scores)):
                        # Simulate user choice based on effectiveness
                        user_choice = 'accepted' if effectiveness >= 0.7 else 'rejected'
                        
                        learn_from_user_choice(
                            user_id=0,  # Training user ID
                            original=toxic_sentence,
                            toxic_words=toxic_words,
                            suggested_type=f"dataset_training_{i}",
                            suggested_text=response,
                            user_choice=user_choice
                        )
                        
                        interactions_created += 1
                    
                    # Progress indicator
                    if row_num % 50 == 0:
                        print(f"Processed {row_num} examples...")
                
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    continue
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    print(f"\nTraining completed!")
    print(f"Examples processed: {examples_processed}")
    print(f"ML interactions created: {interactions_created}")
    print(f"Average responses per example: {interactions_created / examples_processed if examples_processed > 0 else 0:.1f}")

def main():
    """Train with all available datasets."""
    
    print("GuardianText ML Dataset Training")
    print("=" * 50)
    
    # Dataset files
    datasets = [
        "datasets/toxic_clean_dataset_1000.csv",
        "datasets/toxic_swear_sexual_dataset.csv"
    ]
    
    total_examples = 0
    total_interactions = 0
    
    for dataset_file in datasets:
        if os.path.exists(dataset_file):
            print(f"\nProcessing {dataset_file}...")
            train_from_simple_csv(dataset_file)
            total_examples += 1000  # Approximate
            total_interactions += 4000  # Approximate (4 responses per example)
        else:
            print(f"Dataset not found: {dataset_file}")
    
    print(f"\n" + "=" * 50)
    print(f"Total Training Summary:")
    print(f"Total datasets processed: {len([d for d in datasets if os.path.exists(d)])}")
    print(f"Total examples trained: ~{total_examples}")
    print(f"Total ML interactions: ~{total_interactions}")
    print(f"\n*** GuardianText ML system is now trained with real data! ***")
    print(f"The suggestion system should now provide much better responses!")

if __name__ == "__main__":
    main()
