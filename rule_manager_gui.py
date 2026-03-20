import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import yaml
import os
import re
import json
from pii_manager import PIIManager

# Modern UI Constants
COLOR_BG = "#f8fafc"
COLOR_HEADER = "#1e293b"
COLOR_ACCENT = "#3b82f6"
COLOR_SUCCESS = "#22c55e"
COLOR_DANGER = "#ef4444"
FONT_MAIN = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")

class RuleManagerGUI:
    def __init__(self, root, config_path='config.yaml'):
        self.root = root
        self.root.title("Privacy Guard - Enterprise Rule Manager")
        self.root.geometry("1100x800")
        self.root.configure(bg=COLOR_BG)
        
        self.config_path = config_path
        self.manager = PIIManager(config_path=config_path)
        self.rules = []
        
        self.setup_styles()
        self.setup_ui()
        self.load_rules_to_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, font=FONT_MAIN)
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=COLOR_HEADER)
        style.configure("Action.TButton", font=FONT_BOLD, padding=5)
        style.configure("Apply.TButton", font=FONT_BOLD, foreground="white", background=COLOR_SUCCESS)
        style.map("Apply.TButton", background=[('active', '#16a34a')])

    def setup_ui(self):
        # 1. Top Control Bar
        top_bar = ttk.Frame(self.root, padding=10)
        top_bar.pack(fill=tk.X)
        
        ttk.Label(top_bar, text="🛡️ Rule Configuration & Preview", style="Header.TLabel").pack(side=tk.LEFT)
        
        # File Operations Menu
        file_btn_frame = ttk.Frame(top_bar)
        file_btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(file_btn_frame, text="📁 Load Rules", command=self.load_external_rules).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="💾 Save Rules As", command=self.save_rules_as).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="📂 Load Sample", command=self.load_sample_file).pack(side=tk.LEFT, padx=5)

        # 2. Main Paned Content
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Rule List
        rules_container = ttk.LabelFrame(main_paned, text=" Detection Rules Management ", padding=10)
        main_paned.add(rules_container, weight=1)

        # Scrollable Rule Area
        self.rules_canvas = tk.Canvas(rules_container, bg=COLOR_BG, highlightthickness=0)
        v_scroll = ttk.Scrollbar(rules_container, orient="vertical", command=self.rules_canvas.yview)
        self.rules_scroll_frame = ttk.Frame(self.rules_canvas)

        self.rules_scroll_frame.bind(
            "<Configure>",
            lambda e: self.rules_canvas.configure(scrollregion=self.rules_canvas.bbox("all"))
        )

        self.rules_canvas.create_window((0, 0), window=self.rules_scroll_frame, anchor="nw")
        self.rules_canvas.configure(yscrollcommand=v_scroll.set)

        self.rules_canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # Right: Real-time Preview
        preview_container = ttk.LabelFrame(main_paned, text=" Real-time Redaction Preview ", padding=10)
        main_paned.add(preview_container, weight=1)

        # Preview Inputs/Outputs
        io_frame = ttk.Frame(preview_container)
        io_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(io_frame, text="Original Text (Input):", font=FONT_BOLD).pack(anchor="nw")
        self.input_text = scrolledtext.ScrolledText(io_frame, height=15, font=("Consolas", 10), undo=True)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.input_text.bind("<<Modified>>", self.on_input_change)

        ttk.Label(io_frame, text="Redacted Output:", font=FONT_BOLD).pack(anchor="nw")
        self.output_text = scrolledtext.ScrolledText(io_frame, height=15, font=("Consolas", 10), bg="#f1f5f9")
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 3. Bottom Footer
        footer = ttk.Frame(self.root, padding=10)
        footer.pack(fill=tk.X)

        ttk.Button(footer, text="+ Add New Rule", command=self.add_new_rule_row).pack(side=tk.LEFT)
        
        self.apply_btn = ttk.Button(footer, text="🚀 Apply & Save to Main Config", style="Apply.TButton", command=self.save_and_apply)
        self.apply_btn.pack(side=tk.RIGHT)

    def load_rules_to_ui(self, custom_source=None):
        # Clear existing
        for rule in self.rules:
            for w in rule['widgets']:
                w.destroy()
        self.rules = []

        try:
            path = custom_source if custom_source else self.config_path
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            custom_patterns = config.get('custom_patterns', [])
            for cp in custom_patterns:
                self.add_rule_row(cp['name'], cp['regex'], cp['score'])
            
            self.trigger_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rules: {e}")

    def add_rule_row(self, name="", regex="", score=0.5):
        frame = ttk.Frame(self.rules_scroll_frame, padding=5, style="TFrame")
        frame.pack(fill=tk.X, expand=True)
        
        tk.Label(frame, text=f"Rule {len(self.rules)+1}", font=FONT_BOLD, bg=COLOR_BG).grid(row=0, column=0, sticky="w", padx=5)
        
        name_var = tk.StringVar(value=name)
        regex_var = tk.StringVar(value=regex)
        score_var = tk.DoubleVar(value=score)

        # Name & Score Row
        ttk.Label(frame, text="Name:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=name_var, width=15).grid(row=1, column=1, sticky="w", padx=2)
        
        ttk.Label(frame, text=" Score:").grid(row=1, column=2, sticky="w")
        score_spin = ttk.Spinbox(frame, from_=0.1, to=1.0, increment=0.1, textvariable=score_var, width=5)
        score_spin.grid(row=1, column=3, sticky="w", padx=2)
        score_spin.bind("<ButtonRelease-1>", lambda e: self.trigger_preview())
        
        # Regex Row
        ttk.Label(frame, text="Regex:").grid(row=2, column=0, sticky="w")
        regex_ent = ttk.Entry(frame, textvariable=regex_var, width=40)
        regex_ent.grid(row=2, column=1, columnspan=3, sticky="we", padx=2, pady=2)
        regex_ent.bind("<KeyRelease>", lambda e: self.trigger_preview())

        # Delete btn
        del_btn = tk.Button(frame, text="X", fg="white", bg=COLOR_DANGER, command=lambda f=frame, v=name_var: self.remove_rule(f, v))
        del_btn.grid(row=0, column=3, sticky="e")

        self.rules.append({
            'name_var': name_var,
            'regex_var': regex_var,
            'score_var': score_var,
            'frame': frame,
            'widgets': [frame] # frame contains all children
        })

    def remove_rule(self, frame, name_var):
        for i, rule in enumerate(self.rules):
            if rule['name_var'] == name_var:
                rule['frame'].destroy()
                self.rules.pop(i)
                break
        self.trigger_preview()

    def add_new_rule_row(self):
        self.add_rule_row("NEW_RULE", "", 0.5)

    def on_input_change(self, event=None):
        if self.input_text.edit_modified():
            self.trigger_preview()
            self.input_text.edit_modified(False)

    def trigger_preview(self):
        ui_patterns = []
        for r in self.rules:
            name, regex = r['name_var'].get().strip(), r['regex_var'].get().strip()
            if name and regex:
                try:
                    re.compile(regex)
                    ui_patterns.append({'name': name, 'regex': regex, 'score': r['score_var'].get()})
                except: continue
        
        self.manager.custom_patterns = ui_patterns
        self.manager.setup_custom_recognizers()
        
        text = self.input_text.get("1.0", tk.END).strip()
        if text:
            filtered, _ = self.manager.anonymize_text(text)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", filtered)

    # --- File Operations ---
    def load_external_rules(self):
        path = filedialog.askopenfilename(filetypes=[("YAML Files", "*.yaml"), ("All Files", "*.*")])
        if path:
            self.load_rules_to_ui(custom_source=path)

    def save_rules_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".yaml", filetypes=[("YAML Files", "*.yaml")])
        if path:
            self.serialize_to_file(path)

    def load_sample_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt *.md *.log"), ("All Files", "*.*")])
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", f.read())
            self.trigger_preview()

    def serialize_to_file(self, path):
        ui_patterns = []
        for r in self.rules:
            if r['name_var'].get() and r['regex_var'].get():
                ui_patterns.append({
                    'name': r['name_var'].get(),
                    'regex': r['regex_var'].get(),
                    'score': r['score_var'].get()
                })
        
        # Load full config to preserve other settings
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        config['custom_patterns'] = ui_patterns
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        messagebox.showinfo("Success", f"Rules saved to {os.path.basename(path)}")

    def save_and_apply(self):
        self.serialize_to_file(self.config_path)
        self.trigger_preview()

if __name__ == "__main__":
    root = tk.Tk()
    app = RuleManagerGUI(root)
    root.mainloop()
