# GuardianText Enhanced ML System
# ==============================

print("GuardianText Enhanced ML System")
print("=" * 50)

from learning_suggestions import generate_ml_suggestions, init_learning_db
import sqlite3

# 1. Enhanced context detection for complex phrases
def detect_enhanced_context(message: str, toxic_words: list) -> str:
    """Enhanced context detection for specific scenarios."""
    message_lower = message.lower()
    
    # Work contexts (exact match to trained data)
    if any(word in message_lower for word in ['work', 'job', 'boss', 'colleague', 'project', 'task', 'system', 'design']):
        return 'work'
    
    # Academic contexts  
    if any(word in message_lower for word in ['school', 'homework', 'class', 'teacher', 'student', 'study', 'exam']):
        return 'academic'
    
    # Frustration contexts (exact match to trained data)
    if any(word in message_lower for word in ['stupid', 'dumb', 'annoying', 'frustrating', 'shut the fuck up']):
        return 'frustration'
    
    # Personal contexts (exact match to trained data)
    if any(word in message_lower for word in ['family', 'friend', 'personal', 'home', 'mom', 'dad', 'you are']):
        return 'personal'
    
    # Default to general (exact match to trained data)
    return 'general'

# 2. Enhanced suggestion templates using trained ML data
def get_enhanced_context_suggestions(context_type: str, original_message: str) -> list:
    """Get context-specific enhanced suggestions from trained ML data."""
    
    try:
        # Import here to avoid circular imports
        from learning_suggestions import get_user_learning_profile
        import random
        
        # Get trained learning data
        learning_data = get_user_learning_profile(0)  # Use training user ID
        
        # Collect all matching suggestions for this context
        matching_suggestions = []
        
        # Look for suggestions that match the context
        for suggestion in learning_data['effective_suggestions']:
            sug_type, sug_context, avg_effectiveness = suggestion  # Correct tuple unpacking
            
            # Direct context match
            if sug_context == context_type:
                # Get unique suggestion texts for this type
                suggestion_texts = get_all_suggestions_by_type(sug_type, original_message)
                for text in suggestion_texts:
                    if text and text not in [s['text'] for s in matching_suggestions]:
                        matching_suggestions.append({
                            'text': text,
                            'effectiveness': avg_effectiveness,
                            'type': sug_type
                        })
        
        # If we have trained suggestions, select 2 varied ones
        if matching_suggestions:
            # Shuffle to get variety
            random.shuffle(matching_suggestions)
            
            # Sort by effectiveness within the shuffled list to get good but varied options
            matching_suggestions.sort(key=lambda x: x['effectiveness'], reverse=True)
            
            # Return top 2 varied suggestions
            selected = matching_suggestions[:2]
            return [s['text'] for s in selected]
        
        # Fallback to context-specific templates if no trained data found
        return get_fallback_suggestions(context_type)
        
    except Exception as e:
        # If anything goes wrong, use fallback templates
        return get_fallback_suggestions(context_type)

def get_all_suggestions_by_type(suggestion_type: str, original_message: str) -> list:
    """Get all unique suggestion texts for a specific type."""
    
    import sqlite3
    import os
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'learning_suggestions.db')
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Get all unique suggestions for this type
        cursor.execute('''
            SELECT DISTINCT suggested_text FROM user_suggestion_feedback 
            WHERE suggested_type = ? AND user_choice = 'accepted'
            ORDER BY effectiveness_score DESC 
            LIMIT 5
        ''', (suggestion_type,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [r[0] for r in results if r[0]]
        
    except:
        # Return fallback suggestions
        return [
            generate_suggestion_by_type(suggestion_type, original_message),
            generate_suggestion_by_type('dataset_training_1', original_message)
        ]

def get_trained_suggestion_text(suggestion_type: str, original_message: str, used_suggestions: list = None) -> str:
    """Get actual trained suggestion text from the database."""
    
    import sqlite3
    import os
    
    if used_suggestions is None:
        used_suggestions = []
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'learning_suggestions.db')
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Look for the suggestion in user_suggestion_feedback, excluding already used ones
        if used_suggestions:
            placeholders = ','.join('?' * len(used_suggestions))
            cursor.execute(f'''
                SELECT suggested_text FROM user_suggestion_feedback 
                WHERE suggested_type = ? AND user_choice = 'accepted'
                AND suggested_text NOT IN ({placeholders})
                ORDER BY effectiveness_score DESC 
                LIMIT 1
            ''', (suggestion_type,) + tuple(used_suggestions))
        else:
            cursor.execute('''
                SELECT suggested_text FROM user_suggestion_feedback 
                WHERE suggested_type = ? AND user_choice = 'accepted'
                ORDER BY effectiveness_score DESC 
                LIMIT 1
            ''', (suggestion_type,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # If not found, try to get any suggestion for this context
        return get_any_trained_suggestion(original_message, used_suggestions)
        
    except:
        return get_any_trained_suggestion(original_message, used_suggestions)

def get_any_trained_suggestion(original_message: str, used_suggestions: list = None) -> str:
    """Get any trained suggestion as fallback."""
    
    import sqlite3
    import os
    
    if used_suggestions is None:
        used_suggestions = []
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'learning_suggestions.db')
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Get accepted suggestions not already used
        if used_suggestions:
            placeholders = ','.join('?' * len(used_suggestions))
            cursor.execute(f'''
                SELECT suggested_text FROM user_suggestion_feedback 
                WHERE user_choice = 'accepted' AND suggested_type LIKE 'dataset_training%'
                AND suggested_text NOT IN ({placeholders})
                ORDER BY RANDOM() 
                LIMIT 1
            ''', tuple(used_suggestions))
        else:
            cursor.execute('''
                SELECT suggested_text FROM user_suggestion_feedback 
                WHERE user_choice = 'accepted' AND suggested_type LIKE 'dataset_training%'
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # Final fallback to type-based generation
        return generate_suggestion_by_type('dataset_training_0', original_message)
        
    except:
        return generate_suggestion_by_type('dataset_training_0', original_message)

def generate_suggestion_by_type(suggestion_type: str, original_message: str) -> str:
    """Generate suggestion based on type when database lookup fails."""
    
    type_mappings = {
        'dataset_training_0': "Let's communicate constructively.",
        'dataset_training_1': "I'd like to express this differently.",
        'dataset_training_2': "Let's find a positive way forward.",
        'dataset_training_3': "Let's focus on finding common ground.",
        'ml_learned_0': "I see this from a different perspective.",
        'ml_learned_1': "Let's focus on understanding each other.",
        'csv_training_0': "Let's approach this more thoughtfully.",
        'csv_training_1': "I want to express myself better.",
        'csv_training_2': "This situation is challenging for me.",
        'csv_training_3': "Let's discuss this respectfully."
    }
    
    return type_mappings.get(suggestion_type, "Let's communicate constructively.")

def get_fallback_suggestions(context_type: str) -> list:
    """Fallback suggestions when trained data is not available."""
    
    fallback_templates = {
        'work_deadline_urgent': [
            "I'm concerned about meeting tomorrow's deadline.",
            "The deadline tomorrow is challenging but manageable."
        ],
        'work_deadline': [
            "This deadline is creating pressure but I'll manage.",
            "I'm working to meet the upcoming deadline."
        ],
        'academic_urgent': [
            "I'm worried about the exam tomorrow.",
            "I need more time to study for tomorrow's test."
        ],
        'academic_pressure': [
            "I'm feeling overwhelmed by the academic workload.",
            "The study schedule is quite demanding."
        ],
        'time_pressure_frustration': [
            "I'm feeling frustrated about the time pressure.",
            "The deadline is creating significant stress."
        ],
        'personal_frustration': [
            "I'm feeling quite frustrated about this.",
            "This situation is really challenging."
        ],
        'work': [
            "Let's address this professionally.",
            "I'd like to discuss this constructively."
        ],
        'general': [
            "Let's communicate constructively.",
            "I'd like to express this differently."
        ]
    }
    
    return fallback_templates.get(context_type, [
        "Let's communicate constructively.",
        "I'd like to express this differently."
    ])

# 3. Test the enhanced system
def test_enhanced_ml_system():
    """Test the enhanced ML system with complex phrases."""
    
    # Initialize and inject training patterns
    init_learning_db()
    
    test_phrases = [
        "Tomorrow is the deadline,we're fucked",
        "I'm fucked for the exam tomorrow", 
        "This project deadline is fucking me",
        "We're totally screwed for the presentation",
        "The deadline today is fucking impossible"
    ]
    
    print("\nTesting Enhanced ML System:")
    print("=" * 50)
    
    for phrase in test_phrases:
        print(f"\nOriginal: '{phrase}'")
        
        # Detect context
        context = detect_enhanced_context(phrase, ["fuck"])
        print(f"Detected context: {context}")
        
        # Get enhanced suggestions
        enhanced_suggestions = get_enhanced_context_suggestions(context, phrase)
        print(f"Enhanced suggestions:")
        for i, sugg in enumerate(enhanced_suggestions[:4]):
            print(f"  {i+1}. {sugg}")
        
        # Test current ML system
        try:
            current_suggestions = generate_ml_suggestions(1, phrase, ["fuck"])
            print(f"Current ML suggestions:")
            for i, sugg in enumerate(current_suggestions[:2]):
                print(f"  ML{i+1}. {sugg['text']}")
        except Exception as e:
            print(f"  ML system error: {e}")

# 4. Create enhanced suggestion generator
def create_enhanced_suggestion_generator():
    """Create an enhanced suggestion generator that combines ML with context templates."""
    
    def enhanced_generate_suggestions(user_id: int, message: str, toxic_words: list) -> list:
        """Enhanced suggestion generation combining ML and context templates."""
        
        # Get context
        context = detect_enhanced_context(message, toxic_words)
        
        # Get context-specific suggestions
        context_suggestions = get_enhanced_context_suggestions(context, message)
        
        # Get ML suggestions (if available)
        try:
            ml_suggestions = generate_ml_suggestions(user_id, message, toxic_words)
        except:
            ml_suggestions = []
        
        # Combine and return best suggestions
        combined = []
        
        # Add 2 context-specific suggestions
        for sugg in context_suggestions[:2]:
            combined.append({
                'text': sugg,
                'hint': f'Context-aware ({context})',
                'type': 'enhanced_context',
                'confidence': 0.9
            })
        
        # Add 2 ML suggestions
        for sugg in ml_suggestions[:2]:
            combined.append({
                'text': sugg['text'],
                'hint': sugg.get('hint', 'ML-generated'),
                'type': 'ml_generated',
                'confidence': sugg.get('confidence', 0.7)
            })
        
        return combined
    
    return enhanced_generate_suggestions

# Main execution
if __name__ == "__main__":
    print("1. Testing enhanced system...")
    test_enhanced_ml_system()
    
    print("\n" + "=" * 50)
    print("2. Creating enhanced suggestion generator...")
    enhanced_generator = create_enhanced_suggestion_generator()
    
    # Test the enhanced generator
    print("\nTesting Enhanced Generator:")
    test_phrase = "Tomorrow is the deadline,we're fucked"
    suggestions = enhanced_generator(1, test_phrase, ["fuck"])
    
    print(f"Phrase: '{test_phrase}'")
    print("Enhanced suggestions:")
    for i, sugg in enumerate(suggestions):
        print(f"  {i+1}. {sugg['text']} (confidence: {sugg['confidence']:.2f})")
        print(f"      Type: {sugg['type']}, Hint: {sugg['hint']}")
    
    print("\n" + "=" * 50)
    print("Enhanced ML System Ready!")
    print("Features:")
    print("- Enhanced context detection")
    print("- Context-specific suggestion templates")
    print("- Combined ML + template approach")
    print("- Handles complex phrases like 'deadline, we're fucked'")
