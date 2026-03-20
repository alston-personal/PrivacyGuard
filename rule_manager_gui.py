import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import yaml
import os
import re
from pii_manager import PIIManager

class RuleManagerGUI:
    def __init__(self, root, config_path='config.yaml'):
        self.root = root
        self.root.title("Privacy Guard - Rule Manager & Preview")
        self.root.geometry("1000x700")
        self.config_path = config_path
        
        self.manager = PIIManager(config_path=config_path)
        self.rules = [] # List of dicts: {name, regex, score, widget_row}
        
        self.setup_ui()
        self.load_rules_to_ui()

    def setup_ui(self):
        # Main container
        main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top: Rule Management
        rules_frame = ttk.LabelFrame(main_paned, text="Step 1: Manage Detection Rules")
        main_paned.add(rules_frame, weight=1)

        # Scrollable area for rules
        self.rules_canvas = tk.Canvas(rules_frame)
        scrollbar = ttk.Scrollbar(rules_frame, orient="vertical", command=self.rules_canvas.yview)
        self.rules_scroll_frame = ttk.Frame(self.rules_canvas)

        self.rules_scroll_frame.bind(
            "<Configure>",
            lambda e: self.rules_canvas.configure(scrollregion=self.rules_canvas.bbox("all"))
        )

        self.rules_canvas.create_window((0, 0), window=self.rules_scroll_frame, anchor="nw")
        self.rules_canvas.configure(yscrollcommand=scrollbar.set)

        self.rules_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Headers for rules
        headers = ["Entity Name", "Regex Pattern", "Score (0.1-1.0)", "Actions"]
        for i, h in enumerate(headers):
            ttk.Label(self.rules_scroll_frame, text=h, font=('Arial', 10, 'bold')).grid(row=0, column=i, padx=5, pady=5)

        # Bottom: Preview Area
        preview_frame = ttk.LabelFrame(main_paned, text="Step 2: Real-time Preview")
        main_paned.add(preview_frame, weight=1)

        preview_grid = ttk.Frame(preview_frame)
        preview_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(preview_grid, text="Original Text:").grid(row=0, column=0, sticky="nw")
        self.input_text = scrolledtext.ScrolledText(preview_grid, height=10, width=50)
        self.input_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.input_text.bind("<<Modified>>", self.on_input_change)

        ttk.Label(preview_grid, text="Filtered Result:").grid(row=0, column=1, sticky="nw")
        self.output_text = scrolledtext.ScrolledText(preview_grid, height=10, width=50, bg="#f0fdf4")
        self.output_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        preview_grid.columnconfigure(0, weight=1)
        preview_grid.columnconfigure(1, weight=1)
        preview_grid.rowconfigure(1, weight=1)

        # Bottom Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="+ Add Rule", command=self.add_new_rule_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Apply & Save Config", style="Accent.TButton", command=self.save_and_apply).pack(side=tk.RIGHT, padx=5)
        
        # Style
        style = ttk.Style()
        style.configure("Accent.TButton", font=('Arial', 10, 'bold'))

    def load_rules_to_ui(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        custom_patterns = config.get('custom_patterns', [])
        for cp in custom_patterns:
            self.add_rule_row(cp['name'], cp['regex'], cp['score'])

    def add_rule_row(self, name="", regex="", score=0.5):
        row = len(self.rules) + 1
        
        name_var = tk.StringVar(value=name)
        regex_var = tk.StringVar(value=regex)
        score_var = tk.DoubleVar(value=score)
        
        name_ent = ttk.Entry(self.rules_scroll_frame, textvariable=name_var, width=20)
        name_ent.grid(row=row, column=0, padx=5, pady=2)
        
        regex_ent = ttk.Entry(self.rules_scroll_frame, textvariable=regex_var, width=50)
        regex_ent.grid(row=row, column=1, padx=5, pady=2)
        regex_ent.bind("<KeyRelease>", lambda e: self.trigger_preview())
        
        score_spin = ttk.Spinbox(self.rules_scroll_frame, from_=0.1, to=1.0, increment=0.1, textvariable=score_var, width=5)
        score_spin.grid(row=row, column=2, padx=5, pady=2)
        score_spin.bind("<ButtonRelease-1>", lambda e: self.trigger_preview())
        score_spin.bind("<KeyRelease>", lambda e: self.trigger_preview())

        del_btn = ttk.Button(self.rules_scroll_frame, text="🗑", width=3, command=lambda r=row: self.delete_rule(r))
        del_btn.grid(row=row, column=3, padx=5, pady=2)

        self.rules.append({
            'name_var': name_var,
            'regex_var': regex_var,
            'score_var': score_var,
            'widgets': [name_ent, regex_ent, score_spin, del_btn]
        })

    def add_new_rule_row(self):
        self.add_rule_row("NEW_RULE", "", 0.5)

    def delete_rule(self, row_idx):
        # Simplified: find the rule and destroy widgets
        # For a robust implementation, we'd need more complex state management
        for i, rule in enumerate(self.rules):
            if i + 1 == row_idx:
                for w in rule['widgets']:
                    w.destroy()
                self.rules.pop(i)
                break
        self.trigger_preview()

    def on_input_change(self, event=None):
        if self.input_text.edit_modified():
            self.trigger_preview()
            self.input_text.edit_modified(False)

    def trigger_preview(self):
        # Update current manager rules from UI
        ui_custom_patterns = []
        for r in self.rules:
            if r['name_var'].get() and r['regex_var'].get():
                try:
                    re.compile(r['regex_var'].get()) # Validate regex
                    ui_custom_patterns.append({
                        'name': r['name_var'].get(),
                        'regex': r['regex_var'].get(),
                        'score': r['score_var'].get()
                    })
                except:
                    continue
        
        # Inject into manager directly for preview
        self.manager.custom_patterns = ui_custom_patterns
        self.manager.setup_custom_recognizers()
        
        text = self.input_text.get("1.0", tk.END).strip()
        if text:
            filtered, _ = self.manager.anonymize_text(text)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", filtered)

    def save_and_apply(self):
        # 1. Collect from UI
        ui_custom_patterns = []
        for r in self.rules:
            if r['name_var'].get() and r['regex_var'].get():
                ui_custom_patterns.append({
                    'name': r['name_var'].get(),
                    'regex': r['regex_var'].get(),
                    'score': r['score_var'].get()
                })
        
        # 2. Update config.yaml
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        config['custom_patterns'] = ui_custom_patterns
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            
        messagebox.showinfo("Success", "Configuration saved and applied!")
        self.trigger_preview()

if __name__ == "__main__":
    root = tk.Tk()
    app = RuleManagerGUI(root)
    root.mainloop()
