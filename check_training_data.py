#!/usr/bin/env python3
"""
check_training_data.py - Check what training data was stored
"""

import sys
import os
import sqlite3

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from learning_suggestions import init_learning_db, get_learner

def check_training_database():
    """Check what's actually stored in the training database."""
    
    print("Checking Training Database Contents")
    print("=" * 40)
    
    init_learning_db()
    
    # Connect to database
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'learning_suggestions.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check total records
    cursor.execute('SELECT COUNT(*) FROM user_suggestion_feedback')
    count = cursor.fetchone()[0]
    print(f"Total training records: {count}")
    
    # Show sample records
    cursor.execute('''
        SELECT original_message, suggested_text, user_choice, effectiveness_score, suggested_type 
        FROM user_suggestion_feedback 
        ORDER BY effectiveness_score DESC 
        LIMIT 15
    ''')
    records = cursor.fetchall()
    
    print("\nTop training records by effectiveness:")
    for i, (orig, sugg, choice, score, sugg_type) in enumerate(records, 1):
        print(f"{i}. \"{orig}\"")
        print(f"   -> \"{sugg}\" ({choice}, score: {score:.2f}, type: {sugg_type})")
        print()
    
    # Check unique original messages
    cursor.execute('SELECT COUNT(DISTINCT original_message) FROM user_suggestion_feedback')
    unique_messages = cursor.fetchone()[0]
    print(f"Unique original messages: {unique_messages}")
    
    # Check some specific examples from datasets
    dataset_examples = [
        "shut the fuck up",
        "this system is stupid",
        "this game is fucking trash"
    ]
    
    print("\nChecking specific dataset examples:")
    for example in dataset_examples:
        cursor.execute('''
            SELECT suggested_text, effectiveness_score, user_choice 
            FROM user_suggestion_feedback 
            WHERE original_message = ?
        ''', (example,))
        matches = cursor.fetchall()
        
        print(f"\nExample: \"{example}\"")
        if matches:
            for sugg, score, choice in matches:
                print(f"  -> \"{sugg}\" (score: {score:.2f}, choice: {choice})")
        else:
            print("  No exact matches found")
    
    conn.close()

if __name__ == "__main__":
    check_training_database()
