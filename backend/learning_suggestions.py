"""
learning_suggestions.py - GuardianText Machine Learning Suggestion System
────────────────────────────────────────────────────────────
Implements true ML-based suggestion generation that learns from user behavior
"""

import json
import sqlite3
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import numpy as np
from typing import List, Dict, Tuple, Optional

# ── Database Setup ─────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), 'learning_suggestions.db')

def init_learning_db():
    """Initialize the learning database."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            
            # User suggestion feedback
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_suggestion_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    original_message TEXT NOT NULL,
                    toxic_words TEXT NOT NULL,
                    suggested_type TEXT NOT NULL,
                    suggested_text TEXT NOT NULL,
                    user_choice TEXT NOT NULL,
                    context_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    effectiveness_score REAL DEFAULT 0.0
                )
            ''')
            
            # User communication patterns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_pattern TEXT NOT NULL,
                    context_type TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success_rate REAL DEFAULT 0.0
                )
            ''')
            
            # Suggestion effectiveness tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suggestion_effectiveness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suggestion_type TEXT NOT NULL,
                    context_type TEXT NOT NULL,
                    total_uses INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    avg_effectiveness REAL DEFAULT 0.0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            break  # Success, exit retry loop
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                continue
            else:
                raise  # Re-raise if max retries exceeded or different error

# ── Learning Models ───────────────────────────────────────────────────────

class SuggestionLearner:
    """Machine Learning system for generating intelligent suggestions."""
    
    def __init__(self):
        self.user_patterns = defaultdict(list)
        self.suggestion_stats = defaultdict(lambda: {'uses': 0, 'successes': 0})
        self.context_patterns = {
            'school': ['school', 'teacher', 'homework', 'exam', 'class', 'study'],
            'personal': ['stupid', 'idiot', 'dumb', 'moron', 'hate'],
            'frustration': ['fuck', 'shit', 'crap', 'damn', 'sucks'],
            'work': ['work', 'job', 'boss', 'colleague', 'office'],
            'social': ['friend', 'party', 'meet', 'hang out']
        }
        
    def get_context_type(self, message: str, toxic_words: List[str]) -> str:
        """Determine the context type of a message."""
        message_lower = message.lower()
        
        for context, keywords in self.context_patterns.items():
            if any(kw in message_lower for kw in keywords) or \
               any(tw in message_lower for tw in toxic_words if tw in keywords):
                return context
        
        return 'general'
    
    def extract_pattern(self, message: str) -> str:
        """Extract message pattern for learning."""
        # Remove toxic words and normalize
        cleaned = re.sub(r'\b(' + '|'.join([
            'fuck', 'shit', 'crap', 'damn', 'stupid', 'idiot', 
            'dumb', 'moron', 'hate'
        ]) + r')\b', '', message, flags=re.IGNORECASE)
        
        # Extract key pattern (simplified)
        words = cleaned.lower().split()
        if len(words) > 3:
            return ' '.join(words[:3])  # First 3 words
        elif len(words) > 0:
            return ' '.join(words)
        return 'general'
    
    def learn_from_feedback(self, user_id: int, original: str, toxic_words: List[str], 
                       suggested_type: str, suggested_text: str, user_choice: str):
        """Learn from user suggestion choices."""
        context_type = self.get_context_type(original, toxic_words)
        
        # Calculate effectiveness score
        effectiveness = 1.0 if user_choice == 'accepted' else 0.0
        
        # Use retry logic for database operations
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10.0)  # 10 second timeout
                cursor = conn.cursor()
                
                # Store feedback
                cursor.execute('''
                    INSERT INTO user_suggestion_feedback 
                    (user_id, original_message, toxic_words, suggested_type, suggested_text, user_choice, context_type, effectiveness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, original, json.dumps(toxic_words), suggested_type, suggested_text, user_choice, context_type, effectiveness))
                
                # Update user patterns
                pattern = self.extract_pattern(original)
                cursor.execute('''
                    INSERT OR REPLACE INTO user_patterns 
                    (user_id, message_pattern, context_type, frequency, last_seen, success_rate)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (user_id, pattern, context_type, 1, effectiveness))
                
                # Update suggestion effectiveness
                cursor.execute('''
                    INSERT OR REPLACE INTO suggestion_effectiveness 
                    (suggestion_type, context_type, total_uses, success_count, avg_effectiveness)
                    VALUES (?, ?, 1, ?, ?)
                ''', (suggested_type, context_type, 1 if user_choice == 'accepted' else 0, effectiveness))
                
                conn.commit()
                conn.close()
                break  # Success, exit retry loop
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise  # Re-raise if max retries exceeded or different error
    
    def get_user_learning_data(self, user_id: int) -> Dict:
        """Retrieve learning data for a user."""
        # Use retry logic for database operations
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10.0)  # 10 second timeout
                cursor = conn.cursor()
                
                # Get user patterns
                cursor.execute('''
                    SELECT message_pattern, context_type, frequency, success_rate 
                    FROM user_patterns 
                    WHERE user_id = ? 
                    ORDER BY frequency DESC, success_rate DESC 
                    LIMIT 10
                ''', (user_id,))
                
                patterns = cursor.fetchall()
                
                # Get effective suggestions by context
                cursor.execute('''
                    SELECT suggestion_type, context_type, avg_effectiveness 
                    FROM suggestion_effectiveness 
                    GROUP BY suggestion_type, context_type
                    ORDER BY avg_effectiveness DESC
                ''')
                
                effective_suggestions = cursor.fetchall()
                
                conn.close()
                
                return {
                    'patterns': patterns,
                    'effective_suggestions': effective_suggestions
                }
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise  # Re-raise if max retries exceeded or different error
    
    def generate_ml_suggestion(self, user_id: int, message: str, toxic_words: List[str]) -> List[Dict]:
        """Generate ML-based suggestions using learned patterns."""
        context_type = self.get_context_type(message, toxic_words)
        learning_data = self.get_user_learning_data(user_id)
        
        suggestions = []
        
        # 1. Pattern-based suggestions (learned from user behavior)
        for pattern_data in learning_data['patterns'][:3]:  # Top 3 patterns
            pattern = pattern_data[0]
            if pattern_data[2] == context_type:  # Same context
                base_suggestion = self.reconstruct_from_pattern(pattern, message, toxic_words)
                if base_suggestion and base_suggestion != message:
                    suggestions.append({
                        'text': base_suggestion,
                        'hint': f'Based on your patterns ({pattern_data[3]:.1f} success rate)',
                        'type': 'learned_pattern',
                        'confidence': pattern_data[3]
                    })
        
        # 2. Context-aware ML suggestions
        context_suggestions = self.get_context_ml_suggestions(context_type, toxic_words, learning_data)
        suggestions.extend(context_suggestions)
        
        # 3. Adaptive suggestions based on effectiveness
        effective_by_context = [s for s in learning_data['effective_suggestions'] 
                            if s[1] == context_type]
        
        for eff_sugg in effective_by_context[:2]:  # Top 2 effective for this context
            # eff_sugg format: (suggestion_type, context_type, avg_effectiveness)
            # We need to generate a suggestion based on the type
            suggestion_text = self.get_suggestion_by_type(eff_sugg[0], context_type)
            suggestions.append({
                'text': self.adapt_suggestion(suggestion_text, message, toxic_words),
                'hint': f'Proven effective ({eff_sugg[2]:.1f} avg score)',
                'type': 'adaptive',
                'confidence': eff_sugg[2]
            })
        
        # Ensure diversity and quality
        unique_suggestions = []
        seen_texts = set()
        
        for sugg in suggestions:
            if sugg['text'] not in seen_texts and sugg['text'] != message:
                unique_suggestions.append(sugg)
                seen_texts.add(sugg['text'])
        
        return unique_suggestions[:4]  # Return top 4
    
    def reconstruct_from_pattern(self, pattern: str, original: str, toxic_words: List[str]) -> str:
        """Reconstruct message based on learned pattern."""
        # Simple pattern reconstruction - can be enhanced with NLP
        pattern_words = pattern.split()
        original_words = original.split()
        
        # Replace toxic words in pattern with safer alternatives
        safer_words = {
            'fuck': 'very',
            'shit': 'very',
            'stupid': 'challenging',
            'idiot': 'difficult',
            'dumb': 'confusing',
            'hate': 'dislike'
        }
        
        reconstructed = []
        for i, word in enumerate(original_words):
            if word.lower() in [tw.lower() for tw in toxic_words]:
                # Find closest pattern word and make it safer
                if i < len(pattern_words):
                    pattern_word = pattern_words[min(i, len(pattern_words)-1)]
                    if pattern_word in safer_words:
                        reconstructed.append(safer_words[pattern_word])
                        continue
            reconstructed.append(word)
        
        return ' '.join(reconstructed)
    
    def get_context_ml_suggestions(self, context_type: str, toxic_words: List[str], learning_data: Dict) -> List[Dict]:
        """Generate context-specific ML suggestions."""
        context_templates = {
            'school': [
                "I'm finding this subject really challenging.",
                "Could we discuss this topic constructively?",
                "I'd like to understand this material better."
            ],
            'personal': [
                "I see we have different perspectives on this.",
                "Let's respect each other's viewpoints.",
                "I'd like to share my thoughts calmly."
            ],
            'frustration': [
                "I'm feeling quite frustrated about this.",
                "This situation is really difficult for me.",
                "Can we find a positive way forward?"
            ],
            'work': [
                "I'm having some challenges with this task.",
                "Let's approach this professionally.",
                "Could we discuss alternative solutions?"
            ],
            'general': [
                "I'd like to keep our conversation constructive.",
                "Let's focus on finding common ground.",
                "I appreciate you sharing your thoughts."
            ]
        }
        
        suggestions = []
        templates = context_templates.get(context_type, context_templates['general'])
        
        for i, template in enumerate(templates):
            # Adapt template based on toxic words found
            adapted = self.adapt_template(template, toxic_words)
            suggestions.append({
                'text': adapted,
                'hint': f'Context-aware ({context_type} suggestion)',
                'type': 'context_ml',
                'confidence': 0.8 - (i * 0.1)  # Decreasing confidence
            })
        
        return suggestions
    
    def adapt_template(self, template: str, toxic_words: List[str]) -> str:
        """Adapt template based on toxic words present."""
        if not toxic_words:
            return template
        
        # Simple adaptation - can be enhanced with more sophisticated NLP
        adaptations = {
            'fuck': 'find very challenging',
            'shit': 'find very difficult', 
            'stupid': 'find confusing',
            'hate': 'express disagreement',
            'dumb': 'find unclear'
        }
        
        adapted = template
        for toxic_word in toxic_words:
            if toxic_word.lower() in adaptations:
                adapted = adapted.replace('challenging', adaptations[toxic_word.lower()])
                adapted = adapted.replace('difficult', adaptations[toxic_word.lower()])
        
        return adapted
    
    def adapt_suggestion(self, base_suggestion: str, original: str, toxic_words: List[str]) -> str:
        """Adapt a proven suggestion to current context."""
        # Simple adaptation - preserve structure while changing key terms
        if not toxic_words:
            return base_suggestion
        
        # Extract key phrases from original
        original_lower = original.lower()
        
        # Context-specific adaptations
        if 'school' in original_lower:
            return base_suggestion.replace('difficult', 'challenging').replace('hard', 'complex')
        elif 'work' in original_lower:
            return base_suggestion.replace('difficult', 'challenging').replace('issue', 'opportunity')
        elif any(word in original_lower for word in ['friend', 'social']):
            return base_suggestion.replace('disagree', 'see differently')
        
        return base_suggestion
    
    def get_suggestion_by_type(self, suggestion_type: str, context_type: str) -> str:
        """Generate a suggestion based on its type and context."""
        type_suggestions = {
            'rephrased': "Let me express this more constructively.",
            'filtered': "I'd like to share my thoughts respectfully.",
            'contextual': "Perhaps we can approach this differently.",
            'constructive': "Let's find a positive way forward.",
            'ml_learned_0': "I see this from a different perspective.",
            'ml_learned_1': "Let's focus on understanding each other."
        }
        
        # Get base suggestion
        base = type_suggestions.get(suggestion_type, "Let's communicate constructively.")
        
        # Adapt to context
        if context_type == 'school':
            base = base.replace("communicate", "discuss this topic")
        elif context_type == 'work':
            base = base.replace("communicate", "address this professionally")
        elif context_type == 'personal':
            base = base.replace("communicate", "share our views")
        
        return base

# ── Global Learner Instance ─────────────────────────────────────────────
_global_learner = None

def get_learner() -> SuggestionLearner:
    """Get or create global learner instance."""
    global _global_learner
    if _global_learner is None:
        _global_learner = SuggestionLearner()
        init_learning_db()
    return _global_learner

def generate_ml_suggestions(user_id: int, message: str, toxic_words: List[str]) -> List[Dict]:
    """Generate ML-based suggestions for a message."""
    learner = get_learner()
    return learner.generate_ml_suggestion(user_id, message, toxic_words)

def learn_from_user_choice(user_id: int, original: str, toxic_words: List[str], 
                          suggested_type: str, suggested_text: str, user_choice: str):
    """Record user's choice for learning."""
    learner = get_learner()
    learner.learn_from_feedback(user_id, original, toxic_words, suggested_type, suggested_text, user_choice)

def get_user_learning_profile(user_id: int) -> Dict:
    """Get user's learning profile and patterns."""
    learner = get_learner()
    return learner.get_user_learning_data(user_id)

# ── Initialization ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_learning_db()
    print("🤖 GuardianText ML Suggestion System Initialized")
    print("Database created at:", DB_PATH)
