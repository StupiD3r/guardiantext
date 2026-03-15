# GuardianText CSV Dataset Training System
# ======================================

print("GuardianText CSV Dataset Training System")
print("=" * 50)

import csv
import json
from learning_suggestions import init_learning_db, learn_from_user_choice

## 🎯 **CSV Dataset Format Expected**

# Your CSV should have these columns:
# original_message,toxic_words,context,ideal_response_1,ideal_response_2,ideal_response_3,ideal_response_4,effectiveness_1,effectiveness_2,effectiveness_3,effectiveness_4

# Example CSV format:
"""
original_message,toxic_words,context,ideal_response_1,ideal_response_2,ideal_response_3,ideal_response_4,effectiveness_1,effectiveness_2,effectiveness_3,effectiveness_4
"this is fucking stupid","fucking,stupid",personal_frustration,"I'm feeling frustrated about this.","This situation is really challenging.","Let's find a constructive way forward.","I'd like to approach this differently.",0.9,0.8,0.7,0.6
"Tomorrow is the deadline,we're fucked","fuck",work_deadline_urgent,"I'm concerned about meeting tomorrow's deadline.","The deadline tomorrow is challenging but manageable.","Let's focus on completing the work by tomorrow.","I need help to prepare for tomorrow's deadline.",0.95,0.9,0.85,0.8
"""

## 🔧 **CSV Data Ingestion Functions**

def load_csv_dataset(csv_file_path):
    """Load and validate CSV dataset."""
    dataset = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Parse toxic words from CSV (comma-separated)
                    toxic_words = [w.strip() for w in row['toxic_words'].split(',')]
                    
                    # Parse effectiveness scores
                    effectiveness_scores = [
                        float(row.get('effectiveness_1', 0.7)),
                        float(row.get('effectiveness_2', 0.6)),
                        float(row.get('effectiveness_3', 0.5)),
                        float(row.get('effectiveness_4', 0.4))
                    ]
                    
                    # Extract ideal responses
                    ideal_responses = [
                        row['ideal_response_1'],
                        row['ideal_response_2'],
                        row['ideal_response_3'],
                        row['ideal_response_4']
                    ]
                    
                    dataset.append({
                        'original_message': row['original_message'],
                        'toxic_words': toxic_words,
                        'context': row['context'],
                        'ideal_responses': ideal_responses,
                        'effectiveness_scores': effectiveness_scores,
                        'row_number': row_num
                    })
                    
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    continue
                    
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file_path}' not found!")
        return []
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []
    
    return dataset

def validate_dataset(dataset):
    """Validate the loaded dataset."""
    if not dataset:
        print("No data to validate!")
        return False
    
    issues = []
    
    for i, example in enumerate(dataset):
        # Check required fields
        if not example.get('original_message'):
            issues.append(f"Row {example['row_number']}: Missing original_message")
        
        if not example.get('toxic_words'):
            issues.append(f"Row {example['row_number']}: Missing toxic_words")
        
        if not example.get('context'):
            issues.append(f"Row {example['row_number']}: Missing context")
        
        # Check responses
        responses = example.get('ideal_responses', [])
        if len(responses) < 4:
            issues.append(f"Row {example['row_number']}: Need 4 ideal responses, got {len(responses)}")
        
        # Check effectiveness scores
        scores = example.get('effectiveness_scores', [])
        if len(scores) < 4:
            issues.append(f"Row {example['row_number']}: Need 4 effectiveness scores, got {len(scores)}")
    
    if issues:
        print("Dataset validation issues:")
        for issue in issues[:10]:  # Show first 10 issues
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")
        return False
    else:
        print("Dataset validation: PASSED")
        return True

def inject_csv_into_ml_system(dataset, batch_size=100):
    """Inject CSV dataset into GuardianText ML system."""
    
    if not validate_dataset(dataset):
        print("Cannot inject invalid dataset!")
        return
    
    print(f"Initializing ML system...")
    init_learning_db()
    
    total_examples = len(dataset)
    successful_injections = 0
    
    print(f"Injecting {total_examples} training examples...")
    
    for i, example in enumerate(dataset):
        try:
            # For each ideal response, simulate user acceptance
            for j, response in enumerate(example['ideal_responses']):
                effectiveness = example['effectiveness_scores'][j]
                
                # Simulate user choice based on effectiveness
                user_choice = 'accepted' if effectiveness >= 0.7 else 'rejected'
                
                # Inject into ML system
                learn_from_user_choice(
                    user_id=0,  # Training user ID
                    original=example['original_message'],
                    toxic_words=example['toxic_words'],
                    suggested_type=f"csv_training_{j}",
                    suggested_text=response,
                    user_choice=user_choice
                )
            
            successful_injections += 1
            
            # Progress indicator
            if (i + 1) % batch_size == 0:
                progress = ((i + 1) / total_examples) * 100
                print(f"Progress: {progress:.1f}% ({i + 1}/{total_examples})")
                
        except Exception as e:
            print(f"Error injecting example {i + 1}: {e}")
            continue
    
    print(f"\nTraining injection completed!")
    print(f"Successfully injected: {successful_injections}/{total_examples} examples")
    print(f"Total ML interactions: {successful_injections * 4}")

def analyze_dataset_statistics(dataset):
    """Analyze dataset statistics."""
    if not dataset:
        print("No dataset to analyze!")
        return
    
    print("\nDataset Statistics:")
    print("=" * 30)
    
    # Context distribution
    contexts = {}
    toxic_word_counts = {}
    
    for example in dataset:
        context = example['context']
        contexts[context] = contexts.get(context, 0) + 1
        
        for word in example['toxic_words']:
            toxic_word_counts[word] = toxic_word_counts.get(word, 0) + 1
    
    print(f"Total examples: {len(dataset)}")
    print(f"Unique contexts: {len(contexts)}")
    print(f"Unique toxic words: {len(toxic_word_counts)}")
    
    print("\nContext distribution:")
    for context, count in sorted(contexts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {context}: {count} examples")
    
    print("\nMost common toxic words:")
    for word, count in sorted(toxic_word_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {word}: {count} occurrences")

## 🚀 **Usage Example**

def main_training_pipeline(csv_file_path):
    """Complete training pipeline for CSV dataset."""
    
    print("Starting GuardianText CSV Training Pipeline")
    print("=" * 50)
    
    # Step 1: Load dataset
    print("1. Loading CSV dataset...")
    dataset = load_csv_dataset(csv_file_path)
    
    if not dataset:
        print("Failed to load dataset!")
        return
    
    # Step 2: Analyze dataset
    print("2. Analyzing dataset...")
    analyze_dataset_statistics(dataset)
    
    # Step 3: Validate dataset
    print("3. Validating dataset...")
    if not validate_dataset(dataset):
        print("Dataset validation failed!")
        return
    
    # Step 4: Inject into ML system
    print("4. Injecting into ML system...")
    inject_csv_into_ml_system(dataset)
    
    print("\n" + "=" * 50)
    print("CSV Training Pipeline: COMPLETED!")
    print("Your GuardianText ML system is now trained with your dataset!")

## 📝 **How to Use**

# 1. Prepare your CSV file with the required columns
# 2. Save it as 'training_data.csv' in the backend directory
# 3. Run this script

if __name__ == "__main__":
    # Example usage
    csv_file = "training_data.csv"  # Replace with your CSV file path
    
    print("GuardianText CSV Training System Ready!")
    print(f"Expected CSV format: see comments in this script")
    print(f"To train: main_training_pipeline('{csv_file}')")
    
    # Uncomment to run training
    # main_training_pipeline(csv_file)
