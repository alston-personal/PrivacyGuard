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
        self.root.title("🛡️ Privacy Guard - Pattern Studio")
        self.root.geometry("1100x850")
        self.root.configure(bg=COLOR_BG)
        
        self.config_path = config_path
        self.manager = PIIManager(config_path=config_path)
        self.rules = [] # List of dicts representing each rule row
        
        self.setup_styles()
        self.setup_ui()
        self.load_rules_to_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, font=FONT_MAIN)
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=COLOR_HEADER)
        style.configure("Action.TButton", font=("Segoe UI", 9), padding=2)
        style.configure("Apply.TButton", font=FONT_BOLD, foreground="white", background=COLOR_SUCCESS)
        style.map("Apply.TButton", background=[('active', '#16a34a')])
        
        # Rule Row styling
        style.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        style.configure("Order.TButton", font=("Segoe UI", 8), width=3)

    def setup_ui(self):
        # 1. Top Control Bar
        top_bar = tk.Frame(self.root, bg=COLOR_HEADER, height=60)
        top_bar.pack(fill=tk.X)
        
        title_lbl = tk.Label(top_bar, text="🛡️ REGEX PATTERN STUDIO", font=("Segoe UI", 14, "bold"), bg=COLOR_HEADER, fg="white", padx=20)
        title_lbl.pack(side=tk.LEFT)
        
        # File Operations Menu
        file_btn_frame = tk.Frame(top_bar, bg=COLOR_HEADER)
        file_btn_frame.pack(side=tk.RIGHT, padx=10)
        
        btn_opts = {"bg": "#334155", "fg": "white", "relief": "flat", "padx": 10, "pady": 5, "font": ("Segoe UI", 9)}
        tk.Button(file_btn_frame, text="📁 Load YAML", command=self.load_external_rules, **btn_opts).pack(side=tk.LEFT, padx=5)
        tk.Button(file_btn_frame, text="💾 Save Copy", command=self.save_rules_as, **btn_opts).pack(side=tk.LEFT, padx=5)
        tk.Button(file_btn_frame, text="📂 Test Samples", command=self.load_sample_file, **btn_opts).pack(side=tk.LEFT, padx=5)

        # 2. Main Paned Content
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Left: Rule List
        rules_side = ttk.Frame(main_paned, padding=5)
        main_paned.add(rules_side, weight=2)
        
        ttk.Label(rules_side, text="Detection Rules Architecture", style="Header.TLabel").pack(anchor="nw", pady=(0, 10))
        ttk.Label(rules_side, text="💡 Rules are applied in the order shown below.", font=("Segoe UI", 9), foreground="#64748b").pack(anchor="nw", pady=(0, 10))

        # Scrollable Rule Area
        outer_frame = tk.Frame(rules_side, bg="#e2e8f0", bd=1, relief="solid")
        outer_frame.pack(fill=tk.BOTH, expand=True)
        
        self.rules_canvas = tk.Canvas(outer_frame, bg="#f1f5f9", highlightthickness=0)
        v_scroll = ttk.Scrollbar(outer_frame, orient="vertical", command=self.rules_canvas.yview)
        self.rules_scroll_frame = tk.Frame(self.rules_canvas, bg="#f1f5f9")

        self.rules_canvas.create_window((0, 0), window=self.rules_scroll_frame, anchor="nw", width=550) # Approx width
        self.rules_canvas.configure(yscrollcommand=v_scroll.set)

        self.rules_scroll_frame.bind("<Configure>", lambda e: self.rules_canvas.configure(scrollregion=self.rules_canvas.bbox("all")))
        
        self.rules_canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # Right: Real-time Preview
        preview_side = ttk.Frame(main_paned, padding=5)
        main_paned.add(preview_side, weight=3)

        ttk.Label(preview_side, text="Redaction Pipeline Preview", style="Header.TLabel").pack(anchor="nw", pady=(0, 10))

        # Preview Inputs/Outputs
        self.input_text = scrolledtext.ScrolledText(preview_side, height=18, font=("Consolas", 11), undo=True, bd=1, relief="solid")
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.input_text.insert("1.0", "Paste your test content here...")
        self.input_text.bind("<<Modified>>", self.on_input_change)

        ttk.Label(preview_side, text="Filtered Result Output:", font=FONT_BOLD, foreground=COLOR_SUCCESS).pack(anchor="nw")
        self.output_text = scrolledtext.ScrolledText(preview_side, height=18, font=("Consolas", 11), bg="#f8fafc", bd=1, relief="solid")
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 3. Bottom Footer
        footer = tk.Frame(self.root, bg="#f1f5f9", padding=15)
        footer.pack(fill=tk.X)

        tk.Button(footer, text="+ Add New Scraper Rule", bg=COLOR_ACCENT, fg="white", font=FONT_BOLD, relief="flat", padx=15, pady=8, command=self.add_new_rule_row).pack(side=tk.LEFT)
        
        self.apply_btn = tk.Button(footer, text="🚀 Save & Hot-Reload Config", bg=COLOR_SUCCESS, fg="white", font=FONT_BOLD, relief="flat", padx=20, pady=8, command=self.save_and_apply)
        self.apply_btn.pack(side=tk.RIGHT)

    def load_rules_to_ui(self, custom_source=None):
        # Clear existing
        for rule in self.rules:
            rule['frame'].destroy()
        self.rules = []

        try:
            path = custom_source if custom_source else self.config_path
            if not os.path.exists(path):
                # Init empty config if missing
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump({'custom_patterns': []}, f)
            
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            custom_patterns = config.get('custom_patterns', [])
            for cp in custom_patterns:
                self.add_rule_row(cp['name'], cp['regex'], cp['score'])
            
            self.refresh_rule_visuals()
            self.trigger_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rules: {e}")

    def add_rule_row(self, name="", regex="", score=0.5):
        frame = tk.Frame(self.rules_scroll_frame, bg="white", bd=1, relief="solid", pady=5)
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Order Buttons
        order_frame = tk.Frame(frame, bg="white")
        order_frame.pack(side=tk.LEFT, padx=5)
        up_btn = tk.Button(order_frame, text="▲", font=("Arial", 8), bg="#f1f5f9", command=lambda: self.move_rule(frame, -1))
        up_btn.pack(side=tk.TOP)
        dn_btn = tk.Button(order_frame, text="▼", font=("Arial", 8), bg="#f1f5f9", command=lambda: self.move_rule(frame, 1))
        dn_btn.pack(side=tk.TOP)

        content_frame = tk.Frame(frame, bg="white")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        name_var = tk.StringVar(value=name)
        regex_var = tk.StringVar(value=regex)
        score_var = tk.DoubleVar(value=score)

        # Labels + Entires
        row1 = tk.Frame(content_frame, bg="white")
        row1.pack(fill=tk.X)
        tk.Label(row1, text="Label:", bg="white", font=FONT_BOLD).pack(side=tk.LEFT)
        tk.Entry(row1, textvariable=name_var, font=FONT_MAIN, width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Label(row1, text="Confidence Sc:", bg="white", font=FONT_BOLD).pack(side=tk.LEFT, padx=(10,0))
        s_box = ttk.Spinbox(row1, from_=0.1, to=1.0, increment=0.1, textvariable=score_var, width=5)
        s_box.pack(side=tk.LEFT, padx=5)
        s_box.bind("<ButtonRelease-1>", lambda e: self.trigger_preview())

        row2 = tk.Frame(content_frame, bg="white")
        row2.pack(fill=tk.X, pady=(5,0))
        tk.Label(row2, text="Regex:", bg="white", font=FONT_BOLD).pack(side=tk.LEFT)
        reg_ent = tk.Entry(row2, textvariable=regex_var, font=("Consolas", 10), bd=1, relief="solid")
        reg_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        reg_ent.bind("<KeyRelease>", lambda e: self.trigger_preview())

        # Action Buttons
        act_frame = tk.Frame(frame, bg="white")
        act_frame.pack(side=tk.RIGHT, padx=5)
        tk.Button(act_frame, text="🗑️", bg="#fee2e2", fg=COLOR_DANGER, bd=0, command=lambda: self.remove_rule(frame)).pack()

        self.rules.append({
            'name_var': name_var,
            'regex_var': regex_var,
            'score_var': score_var,
            'frame': frame
        })
        self.refresh_rule_visuals()

    def remove_rule(self, frame):
        for i, rule in enumerate(self.rules):
            if rule['frame'] == frame:
                rule['frame'].destroy()
                self.rules.pop(i)
                break
        self.refresh_rule_visuals()
        self.trigger_preview()

    def move_rule(self, frame, direction):
        idx = -1
        for i, r in enumerate(self.rules):
            if r['frame'] == frame:
                idx = i; break
        
        if idx == -1: return
        new_idx = idx + direction
        if 0 <= new_idx < len(self.rules):
            # Swap in list
            self.rules[idx], self.rules[new_idx] = self.rules[new_idx], self.rules[idx]
            self.refresh_rule_visuals()
            self.trigger_preview()

    def refresh_rule_visuals(self):
        """Redraw all rule frames in correct order."""
        for r in self.rules:
            r['frame'].pack_forget()
        for r in self.rules:
            r['frame'].pack(fill=tk.X, padx=10, pady=5)

    def add_new_rule_row(self):
        self.add_rule_row("NEW_PATTERN", "", 0.8)

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
        
        # Hot-reload manager with these patterns
        self.manager.custom_patterns = ui_patterns
        # We need to recreate the analyzer/registry to ensure order
        from presidio_analyzer import RecognizerRegistry, AnalyzerEngine, Pattern, PatternRecognizer
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers()
        
        # Add custom ones in UI ORDER
        for cp in ui_patterns:
            p = Pattern(name=cp['name'], regex=cp['regex'], score=cp['score'])
            rec = PatternRecognizer(supported_entity=cp['name'], patterns=[p], supported_language='zh')
            registry.add_recognizer(rec)
            if cp['name'] not in self.manager.entities:
                self.manager.entities.append(cp['name'])
        
        self.manager.analyzer.registry = registry
        
        text = self.input_text.get("1.0", tk.END).strip()
        if text and text != "Paste your test content here...":
            filtered, _ = self.manager.anonymize_text(text)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", filtered)

    # --- File Operations ---
    def load_external_rules(self):
        path = filedialog.askopenfilename(filetypes=[("YAML Files", "*.yaml")])
        if path: self.load_rules_to_ui(custom_source=path)

    def save_rules_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".yaml", filetypes=[("YAML Files", "*.yaml")])
        if path: self.serialize_to_file(path)

    def load_sample_file(self):
        # Prefer the newly created test_samples.txt
        default_sample = "/home/ubuntu/privacy-guard/test_samples.txt"
        path = default_sample if os.path.exists(default_sample) else "sample_report.txt"
        
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", f.read())
            self.trigger_preview()
        else:
            messagebox.showinfo("Info", "No sample file found. Please paste manually.")

    def serialize_to_file(self, path):
        ui_patterns = []
        for r in self.rules:
            if r['name_var'].get() and r['regex_var'].get():
                ui_patterns.append({
                    'name': r['name_var'].get(),
                    'regex': r['regex_var'].get(),
                    'score': r['score_var'].get()
                })
        
        config = {'custom_patterns': ui_patterns, 'entities': self.manager.entities}
        # Try to keep existing config values like score_threshold
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                old_conf = yaml.safe_load(f) or {}
                for k, v in old_conf.items():
                    if k not in config: config[k] = v

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
