import sys
import os
from unittest.mock import MagicMock

# Mock tkinter modules before importing rule_manager_gui
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['tkinter.scrolledtext'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()

# Mock the Tkinter Var classes to work as normal Python value holders
class MockVar:
    def __init__(self, value=None):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value

import tkinter
tkinter.StringVar = MockVar
tkinter.DoubleVar = MockVar
tkinter.BooleanVar = MockVar

# Now we can import the GUI class
from rule_manager_gui import RuleManagerGUI

def test_pure_serialization():
    print("==========================================")
    print("Running Pure Python mock serialization test...")
    print("==========================================")
    
    # Create mock Tkinter widgets to avoid visual rendering calls
    mock_root = MagicMock()
    
    # Instantiate RuleManagerGUI with our config
    gui = RuleManagerGUI(mock_root, config_path='config.yaml')
    
    # Check loaded rules
    print(f"Loaded {len(gui.rules)} rules mock-successfully:")
    for i, r in enumerate(gui.rules):
        print(f"  - Rule {i}: Name={r['name_var'].get()}, Enabled={r['enabled_var'].get()}")
    
    # Toggle the first rule to disabled
    if len(gui.rules) > 0:
        target_name = gui.rules[0]['name_var'].get()
        gui.rules[0]['enabled_var'].set(False)
        print(f"\n[Action] Toggled rule '{target_name}' to DISABLED (enabled_var=False).")
        
    # Serialize rules to a temporary test file
    temp_path = 'temp_test_config.yaml'
    gui.serialize_to_file(temp_path)
    print(f"\n[File] Serialized rules successfully to: {temp_path}")
    
    # Inspect the saved file content to verify that the disabled rule is commented out
    print("\n[File Content] Checking commented-out rule inside the file:")
    with open(temp_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if target_name in line or "Disabled detection patterns" in line:
                print(f"    {line.rstrip()}")
                
    # Load back the temporary config file in a new GUI instance
    print("\n[Action] Re-loading from the serialized commented config file...")
    gui2 = RuleManagerGUI(mock_root, config_path=temp_path)
    print(f"Loaded {len(gui2.rules)} rules from temporary config:")
    for i, r in enumerate(gui2.rules):
        print(f"  - Rule {i}: Name={r['name_var'].get()}, Enabled={r['enabled_var'].get()}")
        
    # Verify that the toggled rule loaded back as disabled (enabled_var is False)
    found_rule = None
    for r in gui2.rules:
        if r['name_var'].get() == target_name:
            found_rule = r
            break
            
    assert found_rule is not None, f"Toggled rule '{target_name}' not found after loading!"
    assert not found_rule['enabled_var'].get(), f"Toggled rule '{target_name}' was NOT loaded as disabled!"
    print("\n✅ Verification SUCCESS: Toggled rule was saved as a comment and parsed back with Enabled=False!")
    
    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)
        print("Cleaned up temporary config file.")
    print("==========================================")

if __name__ == '__main__':
    test_pure_serialization()
