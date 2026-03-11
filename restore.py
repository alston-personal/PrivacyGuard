import pyperclip
import time
from pii_manager import PIIManager

def main():
    print("--- Clipboard Restore Tool ---")
    
    try:
        manager = PIIManager()
    except Exception as e:
        print(f"Error: {e}")
        return

    current_content = pyperclip.paste()
    
    if not current_content:
        print("Clipboard is empty.")
        return

    restored_text, was_restored = manager.restore_text(current_content)
    
    if was_restored:
        # Create pause signal for the main monitor
        with open('.pause_filter', 'w') as f:
            f.write('pause')
        
        pyperclip.copy(restored_text)
        print("Privacy Restored! Original text moved back to clipboard.")
    else:
        print("No filter tags found in clipboard or tags not in vault.")

if __name__ == "__main__":
    main()
