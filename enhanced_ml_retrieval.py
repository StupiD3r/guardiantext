#!/usr/bin/env python3
"""
enhanced_ml_retrieval.py - Enhanced ML retrieval that prioritizes exact training matches
"""

import sys
import os
import sqlite3
from typing import List, Dict

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def get_exact_training_matches(original_message: str, toxic_words: List[str]) -> List[Dict]:
    """Get exact matches from training data for the original message."""
    
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'learning_suggestions.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Look for exact matches or very similar messages
        cursor.execute('''
            SELECT suggested_text, effectiveness_score, suggested_type, user_choice
            FROM user_suggestion_feedback 
            WHERE original_message = ? OR (
                LENGTH(original_message) - LENGTH(REPLACE(LOWER(original_message), ?, '')) > 0
                AND ABS(LENGTH(original_message) - LENGTH(?)) <= 5
            )
            ORDER BY effectiveness_score DESC, user_choice = 'accepted' DESC
            LIMIT 4
        ''', (original_message, original_message.lower(), original_message))
        
        matches = cursor.fetchall()
        
        suggestions = []
        for sugg_text, score, sugg_type, choice in matches:
            if sugg_text and sugg_text.strip():
                suggestions.append({
                    'text': sugg_text,
                    'confidence': score,
                    'type': 'exact_training_match',
                    'hint': f'From training data (score: {score:.2f})'
                })
        
        conn.close()
        return suggestions
        
    except Exception as e:
        print(f"Error getting exact matches: {e}")
        return []

def get_similar_training_matches(original_message: str, toxic_words: List[str]) -> List[Dict]:
    """Get similar matches from training data based on toxic words and patterns."""
    
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'learning_suggestions.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Look for messages with similar toxic words
        toxic_word_conditions = []
        params = []
        
        for word in toxic_words[:3]:  # Limit to first 3 toxic words
            toxic_word_conditions.append("original_message LIKE ?")
            params.append(f"%{word}%")
        
        if toxic_word_conditions:
            sql = f'''
                SELECT suggested_text, effectiveness_score, suggested_type, user_choice, original_message
                FROM user_suggestion_feedback 
                WHERE {' OR '.join(toxic_word_conditions)}
                AND original_message != ?
                ORDER BY effectiveness_score DESC, user_choice = 'accepted' DESC
                LIMIT 6
            '''
            params.append(original_message)
            
            cursor.execute(sql, params)
            matches = cursor.fetchall()
            
            suggestions = []
            seen_texts = set()
            
            for sugg_text, score, sugg_type, choice, orig_msg in matches:
                if sugg_text and sugg_text.strip() and sugg_text not in seen_texts:
                    suggestions.append({
                        'text': sugg_text,
                        'confidence': score * 0.9,  # Slightly lower confidence for similar matches
                        'type': 'similar_training_match',
                        'hint': f'Similar to: "{orig_msg[:50]}..." (score: {score:.2f})'
                    })
                    seen_texts.add(sugg_text)
            
            conn.close()
            return suggestions[:4]  # Return top 4
        
        conn.close()
        return []
        
    except Exception as e:
        print(f"Error getting similar matches: {e}")
        return []

def enhanced_generate_ml_suggestions(user_id: int, message: str, toxic_words: List[str]) -> List[Dict]:
    """Enhanced ML generation that prioritizes training data matches."""
    
    # Try exact matches first
    exact_matches = get_exact_training_matches(message, toxic_words)
    
    # If we have exact matches, use them
    if exact_matches:
        print(f"Found {len(exact_matches)} exact training matches")
        return exact_matches
    
    # Try similar matches
    similar_matches = get_similar_training_matches(message, toxic_words)
    
    if similar_matches:
        print(f"Found {len(similar_matches)} similar training matches")
        return similar_matches
    
    # Fallback to original ML system
    try:
        from learning_suggestions import generate_ml_suggestions
        original_suggestions = generate_ml_suggestions(user_id, message, toxic_words)
        print(f"Fallback to original ML: {len(original_suggestions)} suggestions")
        return original_suggestions
    except Exception as e:
        print(f"Error with fallback ML: {e}")
        return []

def test_enhanced_retrieval():
    """Test the enhanced retrieval system."""
    
    print("Testing Enhanced ML Retrieval")
    print("=" * 40)
    
    test_cases = [
        "shut the fuck up",
        "this system is stupid",
        "this game is fucking trash",
        "go fuck yourself",
        "stop being dumb"
    ]
    
    for test_message in test_cases:
        print(f"\nTesting: {test_message}")
        print("-" * 30)
        
        # Get toxic words
        try:
            from nlp_filter import _find_toxics, _normalize, _expand
            norm = _normalize(test_message)
            expanded = _expand(norm)
            found = _find_toxics(expanded)
            toxic_words = [w for w, _ in found]
        except:
            toxic_words = ['unknown']
        
        # Get enhanced suggestions
        suggestions = enhanced_generate_ml_suggestions(0, test_message, toxic_words)
        
        print(f"Found {len(suggestions)} suggestions:")
        for i, sugg in enumerate(suggestions, 1):
            print(f"  {i}. {sugg.get('text', 'N/A')}")
            print(f"     Type: {sugg.get('type', 'unknown')}, Confidence: {sugg.get('confidence', 0):.2f}")
            print(f"     Hint: {sugg.get('hint', 'No hint')}")
        
        print()

if __name__ == "__main__":
    test_enhanced_retrieval()
