import pyperclip
import time
import sys
import os
import keyboard
import threading
import tkinter as tk
import socket
from pii_manager import PIIManager

# Hotkeys
HOTKEY_SWAP   = "alt+f9"   # Swap filtered ↔ original
HOTKEY_CONFIG = "alt+f10"  # Open settings

class AppState:
    running = True
    last_content = ""
    manager = None
    overlay = None
    # Swap state: keep both versions so user can toggle between them
    original_text = None
    filtered_text = None
    showing_original = False
    is_swapping = False
    last_swap_time = 0

# ──────────────────────────────────────────────
# Floating Badge (like IME indicator)
# ──────────────────────────────────────────────
class StatusBadge:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PrivacyGuard")
        self.root.overrideredirect(True)       # No title bar
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-alpha", 0.85)
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.w = 44
        self.h = 44
        self.root.geometry(f"{self.w}x{self.h}+{screen_w - self.w - 20}+{screen_h - self.h - 60}")
        
        self.label = tk.Label(
            self.root, text="🛡️", font=("Segoe UI Emoji", 18),
            bg="#16a34a", fg="white",
            cursor="hand2",
            relief="flat", bd=0
        )
        self.label.pack(fill=tk.BOTH, expand=True)
        
        # Drag + Click support
        self.label.bind("<ButtonPress-1>", self._start_drag)
        self.label.bind("<B1-Motion>", self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        # Right-click = settings
        self.label.bind("<Button-3>", lambda e: self._open_config())
        
        # Tkinter Fallback Bindings (works when app is focused)
        self.root.bind_all("<Alt-F9>", lambda e: swap_clipboard())
        self.root.bind_all("<Alt-F10>", lambda e: self._open_config())
        
        self._dx = 0
        self._dy = 0
        self._moved = False
        self._flash_job = None
    
    def _start_drag(self, event):
        self._dx = event.x
        self._dy = event.y
        self._moved = False
    
    def _on_drag(self, event):
        if abs(event.x - self._dx) > 3 or abs(event.y - self._dy) > 3:
            self._moved = True
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")
        
    def _on_release(self, event):
        if not self._moved:
            # If mouse didn't move much, it's a click: toggle/swap
            swap_clipboard()
    
    def _open_config(self):
        open_config()
    
    # ── Visual states ──
    def set_protected(self):
        """Normal state: filter is active, clipboard is safe"""
        self._cancel_flash()
        self.label.config(bg="#16a34a", text="🛡️")  # Green shield
    
    def set_original(self):
        """Clipboard currently contains original (unfiltered) text"""
        self._cancel_flash()
        self.label.config(bg="#ea580c", text="🔓")  # Orange unlocked
    
    def flash_filtered(self):
        """Brief flash: something just got filtered"""
        self._cancel_flash()
        self.label.config(bg="#22c55e", text="⚡")
        self._flash_job = self.root.after(800, self.set_protected)
    
    def flash_swapped(self):
        """Brief flash for hotkey feedback"""
        orig_bg = self.label.cget("bg")
        self.label.config(bg="#3b82f6") # Blue flash
        self.root.after(150, lambda: self.label.config(bg=orig_bg))

    def flash_settings(self):
        """Brief flash: config opened"""
        self._cancel_flash()
        self.label.config(bg="#2563eb", text="⚙️")
        self._flash_job = self.root.after(800, self.set_protected)
    
    def flash_no_data(self):
        """Brief flash: nothing to swap"""
        self._cancel_flash()
        self.label.config(bg="#dc2626", text="❌")
        self._flash_job = self.root.after(600, self.set_protected)
    
    def _cancel_flash(self):
        if self._flash_job:
            self.root.after_cancel(self._flash_job)
            self._flash_job = None

# ──────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────
# Helper to standardize clipboard text comparison to avoid Windows carriage-return gotchas
def normalize_text(text):
    if text is None:
        return ""
    return text.replace('\r\n', '\n').strip()

def is_text_equal(t1, t2):
    return normalize_text(t1) == normalize_text(t2)

# ──────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────
def swap_clipboard():
    """Toggle clipboard between filtered ↔ original text with safety lock"""
    # Debounce: don't allow swapping more than once every 300ms
    now = time.time()
    if now - AppState.last_swap_time < 0.3:
        return
    AppState.last_swap_time = now

    if AppState.original_text is None or AppState.filtered_text is None:
        # Check if current clipboard has tags we can restore manually
        current = pyperclip.paste()
        if "<" in current and ">" in current:
            restored, was_restored = AppState.manager.restore_text(current)
            if was_restored:
                AppState.original_text = restored
                AppState.filtered_text = current
                AppState.showing_original = False # Base state is filtered
            else:
                if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.flash_no_data)
                return
        else:
            if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.flash_no_data)
            return
    
    # Visual feedback for the hotkey press
    if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.flash_swapped)

    # Set swap lock
    AppState.is_swapping = True
    try:
        if AppState.showing_original:
            # Switch back to filtered
            target = AppState.filtered_text
            pyperclip.copy(target)
            AppState.last_content = target
            AppState.showing_original = False
            print(f"[{time.strftime('%H:%M:%S')}] 🛡️ Shield ON: Clipboard Filtered")
            if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.set_protected)
        else:
            # Switch to original
            target = AppState.original_text
            pyperclip.copy(target)
            AppState.last_content = target
            AppState.showing_original = True
            print(f"[{time.strftime('%H:%M:%S')}] 🔓 Shield OFF: Original Restored")
            if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.set_original)
    finally:
        # Keep lock for a small bit to let OS finish clipboard write
        time.sleep(0.15)
        AppState.is_swapping = False

def open_config():
    try:
        if AppState.overlay:
            AppState.overlay.root.after(0, AppState.overlay.flash_settings)
        
        # Launch Rule Manager in a separate window
        config_window = tk.Toplevel(AppState.overlay.root)
        from rule_manager_gui import RuleManagerGUI
        
        # Always resolve configuration path relative to the application's actual directory
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(app_dir, 'config.yaml')
        
        RuleManagerGUI(config_window, config_path=config_path)
    except Exception as e:
        print(f"Config error: {e}")

# ──────────────────────────────────────────────
# Monitor Loop (background thread)
# ──────────────────────────────────────────────
def monitor_loop():
    while AppState.running:
        try:
            if AppState.is_swapping:
                time.sleep(0.1)
                continue
                
            if os.path.exists('.pause_filter'):
                time.sleep(1)
                try:
                    os.remove('.pause_filter')
                except OSError:
                    pass
                AppState.last_content = pyperclip.paste()
                continue

            current = pyperclip.paste()
            if not current:
                time.sleep(0.5)
                continue
            
            if not is_text_equal(current, AppState.last_content):
                # If content is exactly what we just swapped, ignore
                if is_text_equal(current, AppState.original_text) or is_text_equal(current, AppState.filtered_text):
                    AppState.last_content = current
                    continue

                start = time.time()
                filtered, was_filtered = AppState.manager.anonymize_text(current)
                
                if was_filtered:
                    # Store both versions for swap
                    AppState.original_text = current
                    AppState.filtered_text = filtered
                    AppState.showing_original = False
                    
                    pyperclip.copy(filtered)
                    AppState.last_content = filtered
                    
                    duration = time.time() - start
                    print(f"[{time.strftime('%H:%M:%S')}] ⚡ PII Detected & Masked ({duration:.2f}s)")
                    if AppState.overlay:
                        AppState.overlay.root.after(0, AppState.overlay.flash_filtered)
                else:
                    # New normal content copied
                    AppState.last_content = current
                    # If this is not what we stored, clear the swap memory to avoid confusion
                    if not is_text_equal(current, AppState.original_text):
                        AppState.original_text = None
                        AppState.filtered_text = None
                        AppState.showing_original = False
                    
            time.sleep(0.5)
        except Exception as e:
            # print(f"Monitor error: {e}")
            time.sleep(1)

def check_single_instance():
    """Ensure only one instance of the app is running using a socket lock."""
    # Use a dummy global variable to keep the socket alive
    global _instance_lock
    _instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to a specific high port
        _instance_lock.bind(('127.0.0.1', 65433))
    except socket.error as e:
        print(f"\n[ERROR] Binding failed: {e}")
        print("This usually means another instance is already running.")
        sys.exit(1)

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    check_single_instance()
    print("==========================================")
    print("   CLIPBOARD PRIVACY FILTER v1.0.5         ")
    print("==========================================")
    print(f"  Alt+F9  = Swap (filtered ↔ original)")
    print(f"  Alt+F10 = Open settings")
    print(f"  Drag the badge to reposition.")
    print("==========================================")

    try:
        AppState.manager = PIIManager()
    except Exception as e:
        print(f"Error initializing PIIManager: {e}")
        return

    # Hotkey Registration
    try:
        keyboard.add_hotkey(HOTKEY_SWAP, swap_clipboard, suppress=False)
        keyboard.add_hotkey(HOTKEY_CONFIG, open_config, suppress=False)
        print("✅ Global Hotkeys [Alt+F9/F10] registered.")
    except Exception as e:
        print(f"⚠️ Global Hotkey Error: {e}")
        print("   If you are on Linux, try running with sudo.")
        print("   Fallback: Alt+F9 works when the green badge is focused.")

    AppState.last_content = pyperclip.paste()

    # Background monitor
    threading.Thread(target=monitor_loop, daemon=True).start()

    # Badge on main thread (tkinter requirement)
    AppState.overlay = StatusBadge()
    print("🚀 Privacy Guard is Active!")
    AppState.overlay.root.mainloop()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
