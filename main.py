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

# ──────────────────────────────────────────────
# Floating Badge (like IME indicator)
# ──────────────────────────────────────────────
class StatusBadge:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PF")
        self.root.overrideredirect(True)       # No title bar
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-alpha", 0.88)
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.w = 40
        self.h = 40
        self.root.geometry(f"{self.w}x{self.h}+{screen_w - self.w - 16}+{screen_h - self.h - 48}")
        
        self.label = tk.Label(
            self.root, text="🛡", font=("Segoe UI Emoji", 16),
            bg="#22c55e", fg="white",
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
        self.label.config(bg="#22c55e", text="🛡")  # Green shield
    
    def set_original(self):
        """Clipboard currently contains original (unfiltered) text"""
        self._cancel_flash()
        self.label.config(bg="#f59e0b", text="🔓")  # Orange unlocked
    
    def flash_filtered(self):
        """Brief flash: something just got filtered"""
        self._cancel_flash()
        self.label.config(bg="#16a34a", text="⚡")
        self._flash_job = self.root.after(600, self.set_protected)
    
    def flash_settings(self):
        """Brief flash: config opened"""
        self._cancel_flash()
        self.label.config(bg="#3b82f6", text="⚙")
        self._flash_job = self.root.after(800, self.set_protected)
    
    def flash_no_data(self):
        """Brief flash: nothing to swap"""
        self._cancel_flash()
        self.label.config(bg="#ef4444", text="—")
        self._flash_job = self.root.after(500, self.set_protected)
    
    def _cancel_flash(self):
        if self._flash_job:
            self.root.after_cancel(self._flash_job)
            self._flash_job = None

# ──────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────
def swap_clipboard():
    """Toggle clipboard between filtered ↔ original text with safety lock"""
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
    
    # Set swap lock
    AppState.is_swapping = True
    try:
        if AppState.showing_original:
            # Switch back to filtered
            target = AppState.filtered_text
            pyperclip.copy(target)
            AppState.last_content = target
            AppState.showing_original = False
            print(f"[{time.strftime('%H:%M:%S')}] 🛡️ Mode: Filtered")
            if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.set_protected)
        else:
            # Switch to original
            target = AppState.original_text
            pyperclip.copy(target)
            AppState.last_content = target
            AppState.showing_original = True
            print(f"[{time.strftime('%H:%M:%S')}] 🔓 Mode: Original")
            if AppState.overlay: AppState.overlay.root.after(0, AppState.overlay.set_original)
    finally:
        # Keep lock for a small bit to let Windows finish clipboard write
        time.sleep(0.1)
        AppState.is_swapping = False

def open_config():
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
        if os.name == 'nt':
            os.startfile(config_path)
        if AppState.overlay:
            AppState.overlay.root.after(0, AppState.overlay.flash_settings)
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
            
            if current and current != AppState.last_content:
                # If content is exactly what we just swapped, ignore
                if current == AppState.original_text or current == AppState.filtered_text:
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
                    print(f"[{time.strftime('%H:%M:%S')}] Filtered ({duration:.2f}s)")
                    if AppState.overlay:
                        AppState.overlay.root.after(0, AppState.overlay.flash_filtered)
                else:
                    # New normal content copied
                    AppState.last_content = current
                    # If this is not what we stored, clear the swap memory to avoid confusion
                    if current != AppState.original_text:
                        AppState.original_text = None
                        AppState.filtered_text = None
                        AppState.showing_original = False
                    
            time.sleep(0.5)
        except Exception:
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
        # Try to use a small popup if possible, otherwise exit
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            from tkinter import messagebox
            messagebox.showwarning("Privacy Filter", "Another instance of Privacy Filter is already running.\nCheck your system tray or task manager.")
            temp_root.destroy()
        except:
            pass
        sys.exit(1)

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    check_single_instance()
    print("==========================================")
    print("   CLIPBOARD PRIVACY FILTER v1.0.3         ")
    print("==========================================")
    print(f"  Alt+F9  = Swap (filtered ↔ original)")
    print(f"  Alt+F10 = Open settings")
    print(f"  Drag the green badge to reposition it.")
    print("==========================================")

    try:
        AppState.manager = PIIManager()
    except Exception as e:
        print(f"Error: {e}")
        return

    keyboard.add_hotkey(HOTKEY_SWAP, swap_clipboard, suppress=False)
    keyboard.add_hotkey(HOTKEY_CONFIG, open_config, suppress=False)

    AppState.last_content = pyperclip.paste()

    # Background monitor
    threading.Thread(target=monitor_loop, daemon=True).start()

    # Badge on main thread (tkinter requirement)
    AppState.overlay = StatusBadge()
    print("Ready!")
    AppState.overlay.root.mainloop()

if __name__ == "__main__":
    main()
