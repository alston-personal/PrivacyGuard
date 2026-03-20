import os
import sys
from pii_manager import PIIManager

def test_pii_filter():
    print("Initializing PIIManager...")
    manager = PIIManager(config_path='config.yaml', vault_path='vault.json')
    
    with open('sample_report.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n--- Original Content ---")
    print(content)
    
    print("\n--- Anonymizing... ---")
    filtered_text, was_anonymized = manager.anonymize_text(content)
    
    if was_anonymized:
        print("Anonymization SUCCESS")
        print("\n--- Filtered Content ---")
        print(filtered_text)
        
        with open('sample_report_filtered.txt', 'w', encoding='utf-8') as f:
            f.write(filtered_text)
            
        print("\n--- Restoring... ---")
        restored_text, was_restored = manager.restore_text(filtered_text)
        
        if was_restored:
            print("Restoration SUCCESS")
            if restored_text == content:
                print("Verification SUCCESS: Original and restored content match.")
            else:
                print("Verification FAILURE: Content mismatch!")
                # Show differences if any
        else:
            print("Restoration FAILED")
    else:
        print("Anonymization FAILED (No PII detected?)")

if __name__ == "__main__":
    # Ensure we can find pii_manager
    sys.path.append(os.getcwd())
    test_pii_filter()
