# Simple CSV Training Script
# ==========================

print("GuardianText CSV Training Script")
print("=" * 40)

import csv
import os
from learning_suggestions import init_learning_db, learn_from_user_choice

def train_from_csv(csv_file_path):
    """Train GuardianText ML system from CSV file."""
    
    # Check if file exists
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file '{csv_file_path}' not found!")
        print("Please make sure your CSV file is in the backend directory.")
        return
    
    print(f"Loading training data from: {csv_file_path}")
    
    # Initialize ML database
    print("Initializing ML database...")
    init_learning_db()
    
    examples_loaded = 0
    examples_injected = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Parse data
                    original_message = row['original_message']
                    toxic_words = [w.strip() for w in row['toxic_words'].split(',')]
                    context = row['context']
                    
                    # Get all 4 responses
                    responses = [
                        row['ideal_response_1'],
                        row['ideal_response_2'], 
                        row['ideal_response_3'],
                        row['ideal_response_4']
                    ]
                    
                    # Get effectiveness scores
                    effectiveness = [
                        float(row.get('effectiveness_1', 0.7)),
                        float(row.get('effectiveness_2', 0.6)),
                        float(row.get('effectiveness_3', 0.5)),
                        float(row.get('effectiveness_4', 0.4))
                    ]
                    
                    examples_loaded += 1
                    
                    # Inject each response into ML system
                    for i, (response, score) in enumerate(zip(responses, effectiveness)):
                        # Simulate user acceptance based on effectiveness
                        user_choice = 'accepted' if score >= 0.7 else 'rejected'
                        
                        learn_from_user_choice(
                            user_id=0,  # Training user ID
                            original=original_message,
                            toxic_words=toxic_words,
                            suggested_type=f"csv_training_{i}",
                            suggested_text=response,
                            user_choice=user_choice
                        )
                    
                    examples_injected += 1
                    
                    # Progress indicator
                    if row_num % 10 == 0:
                        print(f"Processed {row_num} examples...")
                
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    continue
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    print(f"\nTraining completed!")
    print(f"Examples loaded: {examples_loaded}")
    print(f"Examples injected: {examples_injected}")
    print(f"Total ML interactions: {examples_injected * 4}")
    print("\nYour GuardianText ML system is now trained!")

# Main execution
if __name__ == "__main__":
    # Look for CSV file
    csv_file = "training_data.csv"
    
    if not os.path.exists(csv_file):
        print(f"No '{csv_file}' found.")
        print("You can:")
        print("1. Use the template: training_data_template.csv")
        print("2. Create your own CSV with the same format")
        print("3. Place your CSV file as 'training_data.csv' in this directory")
        print("\nTemplate columns:")
        print("original_message,toxic_words,context,ideal_response_1,ideal_response_2,ideal_response_3,ideal_response_4,effectiveness_1,effectiveness_2,effectiveness_3,effectiveness_4")
    else:
        train_from_csv(csv_file)
