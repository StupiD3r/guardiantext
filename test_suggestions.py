#!/usr/bin/env python3
"""
test_suggestions.py - Test the 4-option suggestion system with ML integration
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from nlp_filter import analyze_message

def test_ml_suggestion_system():
    """Test the 4-option suggestion system with ML integration."""
    
    test_messages = [
        "You are such an idiot!",
        "This fucking homework is stupid", 
        "I hate my stupid boss",
        "You dumb piece of shit",
        "This crap is garbage",
        "Shut up you moron"
    ]
    
    print("=" * 60)
    print("Testing GuardianText 4-Option ML Suggestion System")
    print("=" * 60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message}")
        print("-" * 40)
        
        # Analyze the message
        result = analyze_message(message)
        
        print(f"Toxicity Score: {result.toxicity_score:.3f}")
        print(f"Action: {result.action}")
        print(f"Toxic Words: {result.toxic_words}")
        print(f"Cleaned Message: {result.cleaned_message}")
        print(f"Suggestion: {result.suggestion}")
        
        # Test the ML suggestion generation from app.py
        try:
            from app import _create_filtered_version, _generate_alternative_paraphrase, _generate_contextual_alternative
            from learning_suggestions import generate_ml_suggestions
            from enhanced_ml_system import detect_enhanced_context, get_enhanced_context_suggestions
            
            # Generate filtered version
            filtered = _create_filtered_version(message, result.toxic_words)
            
            # Get ML suggestions
            user_id = 0  # Test user
            ml_suggestions = []
            try:
                ml_suggestions = generate_ml_suggestions(user_id, message, result.toxic_words)
            except Exception as e:
                print(f"ML suggestions error: {e}")
            
            # If not enough ML suggestions, use enhanced ML
            if len(ml_suggestions) < 2:
                try:
                    enhanced_context = detect_enhanced_context(message, result.toxic_words)
                    enhanced_suggestions = get_enhanced_context_suggestions(enhanced_context, message)
                    for sugg in enhanced_suggestions:
                        if len(ml_suggestions) >= 2:
                            break
                        if not any(opt.get("text", "") == sugg for opt in ml_suggestions):
                            ml_suggestions.append({
                                "text": sugg,
                                "type": f"enhanced_{len(ml_suggestions)}",
                                "confidence": 0.7
                            })
                except Exception as e:
                    print(f"Enhanced ML error: {e}")
            
            print(f"\nML Suggestions Found: {len(ml_suggestions)}")
            for j, sugg in enumerate(ml_suggestions):
                print(f"  ML {j+1}: {sugg.get('text', 'N/A')} (confidence: {sugg.get('confidence', 0):.2f})")
            
            # Build the 4 options as the app would
            options = [
                {
                    "id": "filtered",
                    "label": "Same sentence without toxic words",
                    "text": filtered,
                    "hint": "Original sentence structure preserved"
                }
            ]
            
            # Add ML suggestions as options 2 and 3
            if len(ml_suggestions) >= 1:
                options.append({
                    "id": "ml_paraphrase1",
                    "label": "ML-generated paraphrase",
                    "text": ml_suggestions[0]["text"],
                    "hint": "Machine learning rephrasing",
                    "confidence": ml_suggestions[0].get("confidence", 0.8)
                })
            
            if len(ml_suggestions) >= 2:
                options.append({
                    "id": "ml_paraphrase2", 
                    "label": "Alternative ML paraphrase",
                    "text": ml_suggestions[1]["text"],
                    "hint": "Alternative ML rephrasing",
                    "confidence": ml_suggestions[1].get("confidence", 0.8)
                })
            
            # Fill remaining slots with fallbacks
            if len(options) < 3:
                options.append({
                    "id": "paraphrase1",
                    "label": "Paraphrased version",
                    "text": result.cleaned_message,
                    "hint": "Rephrased to be non-toxic"
                })
            
            if len(options) < 4:
                paraphrase2 = _generate_alternative_paraphrase(message, result.toxic_words)
                options.append({
                    "id": "paraphrase2",
                    "label": "Alternative paraphrase", 
                    "text": paraphrase2,
                    "hint": "Different non-toxic phrasing"
                })
            
            # Ensure exactly 4 options
            options = options[:4]
            
            print("\n4 Suggestion Options:")
            for j, opt in enumerate(options, 1):
                confidence = f" (confidence: {opt.get('confidence', 0):.2f})" if 'confidence' in opt else ""
                print(f"{j}. [{opt['id']}] {opt['label']}{confidence}")
                print(f"   {opt['text']}")
                print(f"   Hint: {opt['hint']}")
            
        except ImportError as e:
            print(f"Could not import suggestion functions: {e}")
        
        print()

if __name__ == "__main__":
    test_ml_suggestion_system()
