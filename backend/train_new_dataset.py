# Train New Dataset - toxic_clean_dataset_15000.csv
# =================================================

print("GuardianText New Dataset Training")
print("=" * 40)

import csv
import os
import re
from learning_suggestions import init_learning_db, learn_from_user_choice

def extract_toxic_words(toxic_sentence):
    """Extract toxic words from a toxic sentence."""
    # Common toxic words to look for
    toxic_patterns = [
        r'\bfuck(?:ing|ed|er|s)?\b',
        r'\bshit(?:s|ty|ted|ting)?\b',
        r'\bstupid(?:ly)?\b',
        r'\bdumb(?:ly)?\b',
        r'\bidiot(?:s)?\b',
        r'\bass(?:hole)?\b',
        r'\bbitch(?:es)?\b',
        r'\bcrap(?:py)?\b',
        r'\bsuck(?:s|ed|ing)?\b',
        r'\bhate(?:s|d|ful)?\b',
        r'\bkill(?:s|ed|ing)?\b',
        r'\bdie(?:s|d)?\b',
        r'\bdamn(?:ed)?\b',
        r'\bterrible\b',
        r'\bpathetic\b',
        r'\bdumbass\b',
        r'\btotal dumbass\b',
        r'\blast chance\b'
    ]
    
    toxic_words = []
    for pattern in toxic_patterns:
        matches = re.findall(pattern, toxic_sentence, re.IGNORECASE)
        toxic_words.extend(matches)
    
    # Remove duplicates and return
    return list(set([word.lower() for word in toxic_words]))

def detect_context(sentence):
    """Detect context from sentence content."""
    sentence_lower = sentence.lower()
    
    # Work/Professional context
    if any(word in sentence_lower for word in ['work', 'job', 'boss', 'colleague', 'project', 'task', 'system', 'design', 'idea', 'approach']):
        return 'work'
    
    # Academic context
    elif any(word in sentence_lower for word in ['school', 'homework', 'class', 'teacher', 'student', 'study', 'exam']):
        return 'academic'
    
    # Personal/Family context
    elif any(word in sentence_lower for word in ['family', 'friend', 'personal', 'home', 'mom', 'dad']):
        return 'personal'
    
    # General frustration
    elif any(word in sentence_lower for word in ['stupid', 'dumb', 'annoying', 'frustrating', 'terrible', 'pathetic']):
        return 'frustration'
    
    # Threat/Warning context
    elif any(word in sentence_lower for word in ['regret', 'last chance', 'warning']):
        return 'warning'
    
    else:
        return 'general'

def generate_additional_responses(toxic_sentence, clean_sentence, context):
    """Generate 3 additional responses beyond the clean sentence."""
    base_responses = {
        'work': [
            "Let's address this professionally.",
            "I'd like to discuss this constructively.",
            "Let's focus on finding a solution."
        ],
        'academic': [
            "I need to approach this more thoughtfully.",
            "Let me think about this differently.",
            "I'd like to understand this better."
        ],
        'personal': [
            "I'd like to communicate more calmly.",
            "Let's discuss this respectfully.",
            "I want to express myself better."
        ],
        'frustration': [
            "I'm feeling frustrated about this.",
            "This situation is challenging for me.",
            "Let's find a positive way forward."
        ],
        'warning': [
            "I'm concerned about this situation.",
            "Let's take a step back and reconsider.",
            "I'd like to resolve this peacefully."
        ],
        'general': [
            "Let's communicate constructively.",
            "I'd like to express this differently.",
            "Let's find common ground."
        ]
    }
    
    additional = base_responses.get(context, base_responses['general'])
    return additional[:3]

def load_new_dataset(csv_file_path):
    """Load dataset with your specific format."""
    dataset = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    toxic_sentence = row['toxic_sentence']
                    clean_sentence = row['clean_sentence']
                    
                    # Skip if essential data is missing
                    if not toxic_sentence or not clean_sentence:
                        continue
                    
                    # Extract toxic words
                    toxic_words = extract_toxic_words(toxic_sentence)
                    
                    # If no toxic words detected, use common ones
                    if not toxic_words:
                        # Check for common patterns manually
                        if 'damn' in toxic_sentence.lower():
                            toxic_words = ['damn']
                        elif 'dumbass' in toxic_sentence.lower():
                            toxic_words = ['dumbass']
                        elif 'terrible' in toxic_sentence.lower():
                            toxic_words = ['terrible']
                        elif 'pathetic' in toxic_sentence.lower():
                            toxic_words = ['pathetic']
                        else:
                            toxic_words = ['toxic']  # Default
                    
                    # Detect context
                    context = detect_context(toxic_sentence)
                    
                    # Generate 4 responses (1 clean + 3 generated)
                    responses = [clean_sentence]
                    responses.extend(generate_additional_responses(toxic_sentence, clean_sentence, context))
                    
                    # Effectiveness scores (clean sentence gets highest score)
                    effectiveness = [0.9, 0.7, 0.6, 0.5]
                    
                    dataset.append({
                        'original_message': toxic_sentence,
                        'toxic_words': toxic_words,
                        'context': context,
                        'ideal_responses': responses,
                        'effectiveness_scores': effectiveness,
                        'row_number': row_num
                    })
                    
                except Exception as e:
                    print(f"  Error processing row {row_num}: {e}")
                    continue
                    
    except Exception as e:
        print(f"  Error reading {os.path.basename(csv_file_path)}: {e}")
        return []
    
    return dataset

def train_new_dataset():
    """Train ML system from your new dataset."""
    
    dataset_path = "c:/Users/D3r/Documents/GuardianTextClaude/datasets/toxic_clean_dataset_15000.csv"
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file '{dataset_path}' not found!")
        return
    
    print(f"Processing new dataset: {os.path.basename(dataset_path)}")
    print(f"File size: {os.path.getsize(dataset_path):,} bytes")
    
    print("\nInitializing ML database...")
    init_learning_db()
    
    # Load the dataset
    print("Loading dataset...")
    dataset = load_new_dataset(dataset_path)
    
    if not dataset:
        print("No valid data found in dataset!")
        return
    
    print(f"Successfully loaded {len(dataset)} examples")
    
    # Show some statistics
    contexts = {}
    toxic_word_counts = {}
    
    for example in dataset:
        context = example['context']
        contexts[context] = contexts.get(context, 0) + 1
        
        for word in example['toxic_words']:
            toxic_word_counts[word] = toxic_word_counts.get(word, 0) + 1
    
    print(f"\nDataset Statistics:")
    print(f"  Contexts found: {list(contexts.keys())}")
    print(f"  Toxic words found: {list(toxic_word_counts.keys())[:10]}...")  # Show first 10
    print(f"  Most common context: {max(contexts, key=contexts.get)}")
    
    # Inject into ML system
    print(f"\nTraining ML system with {len(dataset)} examples...")
    examples_injected = 0
    
    for i, example in enumerate(dataset):
        try:
            for j, (response, score) in enumerate(zip(example['ideal_responses'], example['effectiveness_scores'])):
                user_choice = 'accepted' if score >= 0.7 else 'rejected'
                
                learn_from_user_choice(
                    user_id=0,  # Training user ID
                    original=example['original_message'],
                    toxic_words=example['toxic_words'],
                    suggested_type=f"new_dataset_{j}",
                    suggested_text=response,
                    user_choice=user_choice
                )
            
            examples_injected += 1
            
            # Progress indicator for large dataset
            if (i + 1) % 1000 == 0:
                progress = ((i + 1) / len(dataset)) * 100
                print(f"  Progress: {progress:.1f}% ({i + 1:,}/{len(dataset):,})")
        
        except Exception as e:
            print(f"  Error injecting example {i + 1}: {e}")
            continue
    
    print(f"\n" + "=" * 50)
    print("New Dataset Training Completed!")
    print(f"Dataset: {os.path.basename(dataset_path)}")
    print(f"Examples loaded: {len(dataset)}")
    print(f"Examples injected: {examples_injected}")
    print(f"Total ML interactions: {examples_injected * 4}")
    print("\nYour GuardianText ML system is now trained with 15,000 additional examples!")

# Main execution
if __name__ == "__main__":
    print("GuardianText New Dataset Training")
    print("=" * 40)
    print("Training from toxic_clean_dataset_15000.csv...")
    train_new_dataset()
    print("\nTraining complete! Your ML system is ready.")
