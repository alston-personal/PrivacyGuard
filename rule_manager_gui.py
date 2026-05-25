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
    def __init__(self, root, config_path='config.yaml', manager=None):
        self.root = root
        self.root.title("🛡️ Privacy Guard - Pattern Studio")
        self.root.geometry("1100x850")
        self.root.configure(bg=COLOR_BG)
        
        # Resolve config_path relative to this script's directory if relative
        if not os.path.isabs(config_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(base_dir, config_path)
        else:
            self.config_path = config_path
            
        self.manager = manager if manager else PIIManager(config_path=self.config_path)
        self.rules = [] # List of dicts representing each rule row
        
        self.dragged_index = None
        self.drag_start_y = None
        
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
        
        # Header with Add button
        header_frame = tk.Frame(rules_side, bg=COLOR_BG)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Detection Rules Architecture", style="Header.TLabel").pack(side=tk.LEFT)
        tk.Button(header_frame, text="➕ Add Rule", bg=COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2, command=self.add_new_rule_row).pack(side=tk.RIGHT)
        
        ttk.Label(rules_side, text="💡 Rules are applied in the order shown below. Drag '⠿' handle to reorder.", font=("Segoe UI", 9), foreground="#64748b").pack(anchor="nw", pady=(0, 10))

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
        
        # Selection Suggestion Assistant Panel
        self.suggestion_panel = tk.Frame(preview_side, bg="#eff6ff", bd=1, relief="solid", pady=8, padx=12)
        # Packed dynamically on text selection
        
        self.suggestion_lbl = tk.Label(self.suggestion_panel, text="", font=("Segoe UI", 9), bg="#eff6ff", fg="#1e40af", justify=tk.LEFT, anchor="w")
        self.suggestion_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.add_suggested_btn = tk.Button(self.suggestion_panel, text="➕ Add as Rule", bg=COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, command=self.add_selected_as_rule)
        self.add_suggested_btn.pack(side=tk.RIGHT)
        
        # Bind input text selection events
        self.input_text.bind("<<Selection>>", self.on_text_selection)

        ttk.Label(preview_side, text="Filtered Result Output:", font=FONT_BOLD, foreground=COLOR_SUCCESS).pack(anchor="nw", pady=(10, 0))
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
                content = f.read()
                config = yaml.safe_load(content) or {}
            
            enabled_patterns = config.get('custom_patterns', []) or []
            
            # Extract both active and commented out rules
            patterns = []
            for cp in enabled_patterns:
                patterns.append({'name': cp['name'], 'regex': cp['regex'], 'score': cp['score'], 'enabled': True})
            
            # Simple line parsing to detect commented out rules
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#') and ('- name:' in line or 'name:' in line):
                    try:
                        block_lines = []
                        for j in range(i, min(i+5, len(lines))):
                            l = lines[j].strip()
                            if l.startswith('#'):
                                idx = lines[j].find('#')
                                l_content = lines[j][idx+1:]
                                if l_content.startswith(' '):
                                    l_content = l_content[1:]
                                
                                l_stripped = l_content.strip()
                                if l_stripped.startswith('- ') or l_stripped.startswith('name:') or l_stripped.startswith('regex:') or l_stripped.startswith('score:'):
                                    block_lines.append(l_content)
                                else:
                                    break
                            else:
                                break
                        
                        block_text = "\n".join(block_lines)
                        if not block_text.strip().startswith('-'):
                            block_text = "- " + block_text.strip()
                        parsed = yaml.safe_load(block_text)
                        if parsed and isinstance(parsed, list) and len(parsed) > 0:
                            item = parsed[0]
                            if 'name' in item and 'regex' in item:
                                # Ensure we don't duplicate if already loaded
                                if not any(ep['name'] == item['name'] for ep in enabled_patterns):
                                    patterns.append({
                                        'name': item['name'],
                                        'regex': item['regex'],
                                        'score': item.get('score', 0.5),
                                        'enabled': False
                                    })
                                    i += len(block_lines) - 1
                    except Exception:
                        pass
                i += 1
            
            for cp in patterns:
                self.add_rule_row(cp['name'], cp['regex'], cp['score'], cp['enabled'])
            
            self.refresh_rule_visuals()
            self.trigger_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rules: {e}")

    def add_rule_row(self, name="", regex="", score=0.5, enabled=True):
        frame = tk.Frame(self.rules_scroll_frame, bg="white", bd=1, relief="solid", pady=5)
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 1. Enable/Disable Checkbox
        enabled_var = tk.BooleanVar(value=enabled)
        cb = tk.Checkbutton(frame, variable=enabled_var, bg="white", activebackground="white", selectcolor="white", command=self.trigger_preview)
        cb.pack(side=tk.LEFT, padx=(5, 0))

        # 2. Tactile drag grip handle
        grip = tk.Label(frame, text="⠿", font=("Arial", 12), fg="#94a3b8", bg="white", cursor="fleur")
        grip.pack(side=tk.LEFT, padx=5)
        
        # Bind Drag and Drop Events to the Grip
        grip.bind("<ButtonPress-1>", lambda e, f=frame: self.start_drag(e, f))
        grip.bind("<B1-Motion>", self.drag_motion)
        grip.bind("<ButtonRelease-1>", self.end_drag)

        # 3. Order Buttons (Fallback/Traditional)
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

        # Labels + Entries
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
            'enabled_var': enabled_var,
            'frame': frame
        })
        self.refresh_rule_visuals()

    # --- Drag & Drop Reordering Logic ---
    def start_drag(self, event, frame):
        self.dragged_index = None
        for i, r in enumerate(self.rules):
            if r['frame'] == frame:
                self.dragged_index = i
                break
        if self.dragged_index is None:
            return
        
        # Highlight card during drag
        frame.config(bg="#eff6ff", bd=1, relief="ridge")
        for child in frame.winfo_children():
            try:
                child.config(bg="#eff6ff")
            except:
                pass
        
        self.drag_start_y = event.y_root

    def drag_motion(self, event):
        if self.dragged_index is None:
            return
        
        mouse_y = event.y_root
        
        # Dynamic swapping checks
        target_idx = None
        for i, r in enumerate(self.rules):
            if i == self.dragged_index:
                continue
            
            f = r['frame']
            f_y = f.winfo_rooty()
            f_h = f.winfo_height()
            f_center = f_y + f_h / 2
            
            if i < self.dragged_index and mouse_y < f_center:
                target_idx = i
                break
            elif i > self.dragged_index and mouse_y > f_center:
                target_idx = i
                # Check all successors
        
        if target_idx is not None:
            # Swap in the internal list
            self.rules[self.dragged_index], self.rules[target_idx] = self.rules[target_idx], self.rules[self.dragged_index]
            self.dragged_index = target_idx
            self.refresh_rule_visuals()
            self.trigger_preview()

    def end_drag(self, event):
        if self.dragged_index is not None:
            frame = self.rules[self.dragged_index]['frame']
            frame.config(bg="white", bd=1, relief="solid")
            for child in frame.winfo_children():
                try:
                    child.config(bg="white")
                except:
                    pass
            self.dragged_index = None
            self.refresh_rule_visuals()
            self.trigger_preview()

    # --- Selection Induction Helper ---
    def on_text_selection(self, event=None):
        try:
            if self.input_text.tag_ranges(tk.SEL):
                selected_text = self.input_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if selected_text:
                    from regex_helper import RegexHelper
                    if not hasattr(self, 'regex_helper'):
                         self.regex_helper = RegexHelper()
                    
                    pattern, score = self.regex_helper.suggest_regex(selected_text)
                    self.current_suggested_pattern = pattern
                    self.current_suggested_score = score
                    self.current_selected_text = selected_text
                    
                    # Update panel text
                    disp_text = selected_text[:15] + "..." if len(selected_text) > 15 else selected_text
                    self.suggestion_lbl.config(
                        text=f"💡 Highlight: '{disp_text}' ➔ Suggested: {pattern} (Conf: {score:.2f})"
                    )
                    self.suggestion_panel.pack(fill=tk.X, pady=(0, 10), after=self.input_text)
                    return
        except tk.TclError:
            pass
        self.suggestion_panel.pack_forget()

    def add_selected_as_rule(self):
        if hasattr(self, 'current_suggested_pattern') and self.current_suggested_pattern:
            label = "CUSTOM_RULE"
            text_lower = self.current_selected_text.lower()
            if "@" in self.current_selected_text:
                label = "EMAIL_RULE"
            elif self.current_selected_text.isdigit():
                label = "NUMBER_RULE"
            elif any(char in self.current_selected_text for char in "市區縣路街號"):
                label = "ADDRESS_RULE"
            
            self.add_rule_row(label, self.current_suggested_pattern, self.current_suggested_score, enabled=True)
            self.trigger_preview()
            self.suggestion_panel.pack_forget()
            self.input_text.tag_remove(tk.SEL, "1.0", tk.END)

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
        self.add_rule_row("NEW_PATTERN", "", 0.8, enabled=True)

    def on_input_change(self, event=None):
        if self.input_text.edit_modified():
            self.trigger_preview()
            self.input_text.edit_modified(False)

    def trigger_preview(self):
        ui_patterns = []
        for r in self.rules:
            # ONLY include checked/enabled rules in preview
            if not r['enabled_var'].get():
                continue
                
            name, regex = r['name_var'].get().strip(), r['regex_var'].get().strip()
            if name and regex:
                try:
                    re.compile(regex)
                    ui_patterns.append({'name': name, 'regex': regex, 'score': r['score_var'].get()})
                except: continue
        
        # Hot-reload manager with these patterns
        self.manager.custom_patterns = ui_patterns
        
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
        config_meta = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                try:
                    old_conf = yaml.safe_load(f) or {}
                    for k, v in old_conf.items():
                        if k != 'custom_patterns':
                            config_meta[k] = v
                except:
                    pass
        
        if 'entities' not in config_meta:
            config_meta['entities'] = self.manager.entities
        if 'score_threshold' not in config_meta:
            config_meta['score_threshold'] = self.manager.score_threshold
        
        enabled_list = []
        disabled_list = []
        for r in self.rules:
            name = r['name_var'].get().strip()
            regex = r['regex_var'].get().strip()
            score = r['score_var'].get()
            enabled = r['enabled_var'].get()
            if name and regex:
                rule_dict = {'name': name, 'regex': regex, 'score': score}
                if enabled:
                    enabled_list.append(rule_dict)
                else:
                    disabled_list.append(rule_dict)
        
        # Manual serialization to store disabled rules as comments in config.yaml
        with open(path, 'w', encoding='utf-8') as f:
            if config_meta:
                meta_dump = yaml.dump(config_meta, allow_unicode=True, sort_keys=False).strip()
                f.write(meta_dump + "\n\n")
            
            f.write("custom_patterns:\n")
            
            if enabled_list:
                f.write("  # 🟢 Enabled detection patterns\n")
                for r in enabled_list:
                    f.write(f"  - name: \"{r['name']}\"\n")
                    regex_dump = json.dumps(r['regex'], ensure_ascii=False)
                    f.write(f"    regex: {regex_dump}\n")
                    f.write(f"    score: {r['score']}\n\n")
            
            if disabled_list:
                f.write("  # 🔴 Disabled detection patterns (commented out)\n")
                for r in disabled_list:
                    f.write(f"  # - name: \"{r['name']}\"\n")
                    regex_dump = json.dumps(r['regex'], ensure_ascii=False)
                    f.write(f"  #   regex: {regex_dump}\n")
                    f.write(f"  #   score: {r['score']}\n\n")
        
        messagebox.showinfo("Success", f"Rules saved to {os.path.basename(path)}")

    def save_and_apply(self):
        self.serialize_to_file(self.config_path)
        self.trigger_preview()

if __name__ == "__main__":
    root = tk.Tk()
    app = RuleManagerGUI(root)
    root.mainloop()
