"""
Touch keyboard TOY  (Step 1 prototype, Windows only)

What it does
  * Shows an on-screen QWERTY keyboard that stays on top and does NOT steal
    focus, so tapping a key types into whatever app you were using (Notepad...).
  * Lights up keys when you press them on a REAL keyboard too (and keys sent by
    tools that turn controller buttons into keystrokes).
  * Shift / Ctrl / Alt are "sticky": tap once, then tap the next key.

Privacy
  * The keyboard listener only lights up keys. Nothing is saved, logged, or
    sent anywhere. There is no network code in this file.

Needs only Python 3 (from the Microsoft Store). No extra packages.
Run:   python touch_keyboard_toy.py
Quit:  close the window.
"""
import sys
import tkinter as tk

# ----------------------------------------------------------------------------
# Layout.  Each key: (label, virtual-key-code, width-in-units, finger)
# Fingers: LP LR LM LI = left pinky/ring/middle/index, T = thumb, RI RM RR RP.
# ----------------------------------------------------------------------------
VK_BACK, VK_TAB, VK_RETURN, VK_CAPS, VK_SPACE = 0x08, 0x09, 0x0D, 0x14, 0x20
VK_SHIFT, VK_CTRL, VK_ALT = 0x10, 0x11, 0x12

LAYOUT = [
    [("`", 0xC0, 1, "LP"), ("1", 0x31, 1, "LP"), ("2", 0x32, 1, "LR"),
     ("3", 0x33, 1, "LM"), ("4", 0x34, 1, "LI"), ("5", 0x35, 1, "LI"),
     ("6", 0x36, 1, "RI"), ("7", 0x37, 1, "RI"), ("8", 0x38, 1, "RM"),
     ("9", 0x39, 1, "RR"), ("0", 0x30, 1, "RP"), ("-", 0xBD, 1, "RP"),
     ("=", 0xBB, 1, "RP"), ("Bksp", VK_BACK, 2, "RP")],
    [("Tab", VK_TAB, 1.5, "LP"), ("q", 0x51, 1, "LP"), ("w", 0x57, 1, "LR"),
     ("e", 0x45, 1, "LM"), ("r", 0x52, 1, "LI"), ("t", 0x54, 1, "LI"),
     ("y", 0x59, 1, "RI"), ("u", 0x55, 1, "RI"), ("i", 0x49, 1, "RM"),
     ("o", 0x4F, 1, "RR"), ("p", 0x50, 1, "RP"), ("[", 0xDB, 1, "RP"),
     ("]", 0xDD, 1, "RP"), ("\\", 0xDC, 1.5, "RP")],
    [("Caps", VK_CAPS, 1.75, "LP"), ("a", 0x41, 1, "LP"), ("s", 0x53, 1, "LR"),
     ("d", 0x44, 1, "LM"), ("f", 0x46, 1, "LI"), ("g", 0x47, 1, "LI"),
     ("h", 0x48, 1, "RI"), ("j", 0x4A, 1, "RI"), ("k", 0x4B, 1, "RM"),
     ("l", 0x4C, 1, "RR"), (";", 0xBA, 1, "RP"), ("'", 0xDE, 1, "RP"),
     ("Enter", VK_RETURN, 2.25, "RP")],
    [("Shift", VK_SHIFT, 2.25, "LP"), ("z", 0x5A, 1, "LP"), ("x", 0x58, 1, "LR"),
     ("c", 0x43, 1, "LM"), ("v", 0x56, 1, "LI"), ("b", 0x42, 1, "LI"),
     ("n", 0x4E, 1, "RI"), ("m", 0x4D, 1, "RI"), (",", 0xBC, 1, "RM"),
     (".", 0xBE, 1, "RR"), ("/", 0xBF, 1, "RP"), ("Shift", VK_SHIFT, 2.75, "RP")],
    [("Ctrl", VK_CTRL, 1.5, "LP"), ("Alt", VK_ALT, 1.5, "T"),
     ("Space", VK_SPACE, 9, "T"), ("Alt", VK_ALT, 1.5, "T"),
     ("Ctrl", VK_CTRL, 1.5, "RP")],
]
ROW_UNITS = 15  # every row adds up to this many units wide

# Labels shown when Shift is on (letters are just upper-cased).
SHIFT_LABELS = {"`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
                "6": "^", "7": "&", "8": "*", "9": "(", "0": ")", "-": "_",
                "=": "+", "[": "{", "]": "}", "\\": "|", ";": ":", "'": '"',
                ",": "<", ".": ">", "/": "?"}

MODIFIERS = {VK_SHIFT, VK_CTRL, VK_ALT}

# Left/right modifier codes from the keyboard listener -> one shared code.
VK_NORMALIZE = {0xA0: VK_SHIFT, 0xA1: VK_SHIFT,
                0xA2: VK_CTRL, 0xA3: VK_CTRL,
                0xA4: VK_ALT, 0xA5: VK_ALT}

# Colours
BG = "#1e1e1e"
KEY = "#3a3a3a"
TEXT = "#f2f2f2"
PRESSED = "#4da3ff"   # finger on key, or key held on a real keyboard
LATCHED = "#ffb347"   # sticky modifier waiting for the next key

# Finger colours: set USE_FINGER_COLORS = True to preview (typing-trainer idea).
USE_FINGER_COLORS = False
FINGER_COLORS = {"LP": "#7a3b5e", "LR": "#7a5a2c", "LM": "#4f7a2c",
                 "LI": "#2c6f7a", "T": "#4a4a4a", "RI": "#2c4f7a",
                 "RM": "#4f2c7a", "RR": "#7a2c4f", "RP": "#7a4f2c"}

# ----------------------------------------------------------------------------
# Windows plumbing (only defined on Windows)
# ----------------------------------------------------------------------------
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # --- sending keys (SendInput) ---
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_size_t)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    user32.MapVirtualKeyW.restype = wintypes.UINT

    def send_key_events(events):
        """events = list of (vk, is_key_up). Sent together so they stay in order."""
        arr = (INPUT * len(events))()
        for i, (vk, up) in enumerate(events):
            arr[i].type = INPUT_KEYBOARD
            arr[i].ki = KEYBDINPUT(vk, user32.MapVirtualKeyW(vk, 0),
                                   KEYEVENTF_KEYUP if up else 0, 0, 0)
        user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))

    # --- "don't steal focus" window style ---
    GWL_EXSTYLE = -20
    WS_EX_NOACTIVATE = 0x08000000
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND

    def make_no_activate(tk_root):
        """Tapping this window will no longer pull focus away from your app."""
        tk_root.update_idletasks()
        child = tk_root.winfo_id()
        hwnd = user32.GetParent(child) or child
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)

    # --- listening to the real keyboard (low-level hook; watch only) ---
    WH_KEYBOARD_LL = 13
    WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_size_t)]

    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                  wintypes.WPARAM, wintypes.LPARAM)
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                         wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                      wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = ctypes.c_ssize_t
    user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class KeyboardToy:
    def __init__(self, root):
        self.root = root
        root.title("Keyboard toy")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        root.geometry("900x330+100+100")
        root.minsize(450, 170)

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.keys = []             # one dict per key on screen
        self.by_vk = {}            # vk -> list of key indexes
        self.latched = set()       # sticky modifiers from touch
        self.phys_down = set()     # keys held on a real keyboard
        self.touch_idx = None      # key currently under a finger
        self._hook = None
        self._hook_cb = None       # keep a reference or Python frees it

        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        root.protocol("WM_DELETE_WINDOW", self.close)

        if sys.platform == "win32":
            root.after(150, self.start_windows_bits)

    # ---------------- drawing ----------------
    def shift_on(self):
        return VK_SHIFT in self.latched or VK_SHIFT in self.phys_down

    def label_for(self, key):
        text = key["label"]
        if self.shift_on():
            if len(text) == 1:
                return SHIFT_LABELS.get(text, text.upper())
        return text

    def base_color(self, key):
        return FINGER_COLORS[key["finger"]] if USE_FINGER_COLORS else KEY

    def color_for(self, idx):
        key = self.keys[idx]
        vk = key["vk"]
        if vk in MODIFIERS and vk in self.latched:
            return LATCHED
        if idx == self.touch_idx or vk in self.phys_down:
            return PRESSED
        return self.base_color(key)

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.keys.clear()
        self.by_vk.clear()
        w, h = max(c.winfo_width(), 1), max(c.winfo_height(), 1)
        unit = min(w / ROW_UNITS, h / len(LAYOUT))
        pad = max(unit * 0.05, 1)
        x0 = (w - unit * ROW_UNITS) / 2
        font_size = max(int(unit * 0.28), 7)
        for r, row in enumerate(LAYOUT):
            x = x0
            for label, vk, width, finger in row:
                key = {"label": label, "vk": vk, "finger": finger,
                       "x1": x + pad, "y1": r * unit + pad,
                       "x2": x + width * unit - pad, "y2": (r + 1) * unit - pad}
                idx = len(self.keys)
                self.keys.append(key)
                self.by_vk.setdefault(vk, []).append(idx)
                key["rect"] = c.create_rectangle(
                    key["x1"], key["y1"], key["x2"], key["y2"],
                    fill=self.color_for(idx), outline="")
                key["text"] = c.create_text(
                    (key["x1"] + key["x2"]) / 2, (key["y1"] + key["y2"]) / 2,
                    text=self.label_for(key), fill=TEXT,
                    font=("Segoe UI", font_size))
                x += width * unit

    def repaint(self, vk=None):
        """Recolour keys (all, or just those with this vk)."""
        idxs = self.by_vk.get(vk, []) if vk is not None else range(len(self.keys))
        for i in idxs:
            self.canvas.itemconfig(self.keys[i]["rect"], fill=self.color_for(i))

    def relabel(self):
        for k in self.keys:
            self.canvas.itemconfig(k["text"], text=self.label_for(k))

    # ---------------- touch / mouse ----------------
    def key_at(self, x, y):
        for i, k in enumerate(self.keys):
            if k["x1"] <= x <= k["x2"] and k["y1"] <= y <= k["y2"]:
                return i
        return None

    def on_press(self, event):
        idx = self.key_at(event.x, event.y)
        if idx is None:
            return
        self.touch_idx = idx
        vk = self.keys[idx]["vk"]
        self.repaint(vk)
        if vk in MODIFIERS:
            return  # toggled on release
        self.type_key(vk)

    def on_release(self, event):
        idx, self.touch_idx = self.touch_idx, None
        if idx is None:
            return
        vk = self.keys[idx]["vk"]
        if vk in MODIFIERS:
            self.latched ^= {vk}   # toggle sticky on/off
            if vk == VK_SHIFT:
                self.relabel()
        self.repaint(vk)

    def type_key(self, vk):
        """Press the key, holding any sticky modifiers, then clear them."""
        if sys.platform != "win32":
            return
        mods = sorted(self.latched)
        events = [(m, False) for m in mods] + [(vk, False), (vk, True)] \
                 + [(m, True) for m in reversed(mods)]
        send_key_events(events)
        if mods:
            self.latched.clear()
            self.relabel()
            self.repaint()

    # ---------------- real keyboard listener ----------------
    def start_windows_bits(self):
        make_no_activate(self.root)

        def hook(n_code, w_param, l_param):
            try:
                if n_code == 0:
                    info = KBDLLHOOKSTRUCT.from_address(l_param)
                    vk = VK_NORMALIZE.get(info.vkCode, info.vkCode)
                    if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        self.on_phys(vk, True)
                    elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                        self.on_phys(vk, False)
            except Exception:
                pass  # never let a bug here interfere with your typing
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        self._hook_cb = HOOKPROC(hook)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._hook_cb, kernel32.GetModuleHandleW(None), 0)

    def on_phys(self, vk, down):
        before = self.shift_on()
        if down:
            if vk in self.phys_down:
                return  # key auto-repeat
            self.phys_down.add(vk)
        else:
            self.phys_down.discard(vk)
        self.repaint(vk)
        if before != self.shift_on():
            self.relabel()

    def close(self):
        if sys.platform == "win32" and self._hook:
            user32.UnhookWindowsHookEx(self._hook)
        self.root.destroy()


def main():
    if sys.platform != "win32":
        print("This toy only works on Windows (it uses Windows key APIs).")
        return
    try:  # sharp text on high-DPI screens like the Surface
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    root = tk.Tk()
    KeyboardToy(root)
    root.mainloop()


if __name__ == "__main__":
    main()
