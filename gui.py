#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NUX Mighty Plug Pro – QR Preset Generator GUI
----------------------------------------------
Features:
  • Open a .toml preset file via file dialog → converts to QR .png
  • Drag-and-drop .toml files onto the window (requires tkinterdnd2)
  • Paste TOML text from clipboard and convert
  • Display the generated / opened QR image
  • Open existing .png QR images for viewing
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from toml_parse import convert_toml_file, convert_toml_string, load_preset_from_string

# ---------------------------------------------------------------------------
# Try to import drag-and-drop support (optional dependency)
# ---------------------------------------------------------------------------
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

OUTPUT_DIR = "presets"
QR_DISPLAY_SIZE = 400  # pixels (display size in the GUI)


class QRPresetApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NUX MPP – QR Preset Generator")
        self.root.resizable(False, False)

        self._photo_ref = None  # prevent GC of displayed image

        self._build_toolbar()
        self._build_paste_bar()
        self._build_canvas()
        self._build_status_bar()

        if HAS_DND:
            self._setup_dnd()

        # Global Ctrl+V: convert clipboard text unless the entry is focused
        self.root.bind("<Control-v>", self._on_global_paste)

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------
    def _build_toolbar(self):
        bar = tk.Frame(self.root)
        bar.pack(fill=tk.X, padx=6, pady=(6, 0))

        tk.Button(bar, text="Open TOML…", width=14, command=self._on_open_toml).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="Open PNG…", width=14, command=self._on_open_png).pack(side=tk.LEFT, padx=2)

    def _build_paste_bar(self):
        bar = tk.Frame(self.root)
        bar.pack(fill=tk.X, padx=6, pady=4)

        # tk.Label(bar, text="TOML:").pack(side=tk.LEFT)
        self._paste_entry = tk.Entry(bar)
        # self._paste_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        # self._paste_entry.bind("<Return>", lambda _e: self._on_paste_convert())
        # tk.Button(bar, text="Paste & Convert", command=self._on_paste_clipboard).pack(side=tk.LEFT, padx=2)
        # tk.Button(bar, text="Convert Text", command=self._on_paste_convert).pack(side=tk.LEFT, padx=2)

    def _build_canvas(self):
        frame = tk.Frame(self.root, bd=2, relief=tk.SUNKEN,
                         width=QR_DISPLAY_SIZE, height=QR_DISPLAY_SIZE)
        frame.pack(padx=6, pady=4)
        frame.pack_propagate(False)

        self._image_label = tk.Label(frame, bg="#f0f0f0")
        self._image_label.pack(expand=True)

        if HAS_DND:
            self._drop_hint = tk.Label(
                frame, text="Drop a .toml file here",
                fg="#999999", bg="#f0f0f0", font=("Segoe UI", 10, "italic"))
            self._drop_hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self._drop_hint = None

    def _build_status_bar(self):
        self._status = tk.Label(self.root, text="Ready", anchor=tk.W,
                                relief=tk.SUNKEN, padx=4)
        self._status.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=(0, 6))

    # -----------------------------------------------------------------------
    # Drag-and-drop (tkinterdnd2)
    # -----------------------------------------------------------------------
    def _setup_dnd(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        raw = event.data
        # tkinterdnd2 wraps paths with spaces in braces: {C:\path with spaces\file.toml}
        if raw.startswith("{") and raw.endswith("}"):
            paths = [raw[1:-1]]
        else:
            paths = self.root.tk.splitlist(raw)

        for path in paths:
            path = path.strip()
            if path.lower().endswith(".toml"):
                self._convert_file(path)
                return
            elif path.lower().endswith(".png"):
                self._show_image(path)
                return

        self._set_status("Dropped file is not a .toml or .png")

    # -----------------------------------------------------------------------
    # Global Ctrl+V handler
    # -----------------------------------------------------------------------
    def _on_global_paste(self, event):
        # If the entry widget is focused, let the default paste behaviour work
        if self.root.focus_get() is self._paste_entry:
            return
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            self._set_status("Clipboard is empty or not text")
            return
        if not text:
            self._set_status("Clipboard text is empty")
            return
        self._paste_entry.delete(0, tk.END)
        self._paste_entry.insert(0, text)
        self._convert_string(text)
        return "break"  # suppress default handling

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------
    def _on_open_toml(self):
        path = filedialog.askopenfilename(
            title="Select TOML Preset",
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")])
        if path:
            self._convert_file(path)

    def _on_open_png(self):
        path = filedialog.askopenfilename(
            title="Select QR Image",
            filetypes=[("PNG images", "*.png"), ("All files", "*.*")])
        if path:
            self._show_image(path)

    def _on_paste_clipboard(self):
        """Grab TOML text from the system clipboard, put it in the entry, and convert."""
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            self._set_status("Clipboard is empty or not text")
            return
        text = text.strip()
        if not text:
            self._set_status("Clipboard text is empty")
            return
        self._paste_entry.delete(0, tk.END)
        self._paste_entry.insert(0, text)
        self._convert_string(text)

    def _on_paste_convert(self):
        """Convert whatever is currently in the text entry."""
        text = self._paste_entry.get().strip()
        if not text:
            self._set_status("Text field is empty – paste or type TOML content first")
            return
        self._convert_string(text)

    # -----------------------------------------------------------------------
    # Conversion helpers
    # -----------------------------------------------------------------------
    def _convert_file(self, path: str):
        self._set_status(f"Converting {os.path.basename(path)} …")
        self.root.update_idletasks()
        try:
            png_path = convert_toml_file(path, OUTPUT_DIR)
        except Exception as exc:
            messagebox.showerror("Conversion Error", str(exc))
            self._set_status("Conversion failed")
            return
        self._show_image(png_path)
        self._set_status(f"Saved: {png_path}")

    @staticmethod
    def _unique_path(path: str) -> str:
        """Return *path* if it doesn't exist, otherwise append _1, _2, … before the extension."""
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        n = 1
        while os.path.exists(f"{base}_{n}{ext}"):
            n += 1
        return f"{base}_{n}{ext}"

    def _convert_string(self, toml_text: str):
        self._set_status("Converting pasted TOML …")
        self.root.update_idletasks()
        try:
            png_path = convert_toml_string(toml_text, OUTPUT_DIR)
        except Exception as exc:
            messagebox.showerror("Conversion Error", str(exc))
            self._set_status("Conversion failed")
            return

        # Save the pasted TOML text alongside the QR image
        try:
            preset = load_preset_from_string(toml_text)
            toml_name = preset.get("title", "preset") + ".toml"
            toml_path = self._unique_path(os.path.join(OUTPUT_DIR, toml_name))
            with open(toml_path, "w", encoding="utf-8") as f:
                f.write(toml_text)
        except Exception as exc:
            messagebox.showwarning("TOML Save Warning",
                                  f"QR generated but could not save .toml:\n{exc}")

        self._show_image(png_path)
        self._set_status(f"Saved: {png_path}")

    # -----------------------------------------------------------------------
    # Image display
    # -----------------------------------------------------------------------
    def _show_image(self, path: str):
        try:
            img = Image.open(path)
        except Exception as exc:
            messagebox.showerror("Image Error", str(exc))
            return

        img = img.resize((QR_DISPLAY_SIZE, QR_DISPLAY_SIZE), Image.NEAREST)
        photo = ImageTk.PhotoImage(img)
        self._image_label.configure(image=photo)
        self._photo_ref = photo  # prevent garbage-collection

        if self._drop_hint is not None:
            self._drop_hint.place_forget()

        self._set_status(f"Showing: {os.path.basename(path)}")

    # -----------------------------------------------------------------------
    # Status bar
    # -----------------------------------------------------------------------
    def _set_status(self, text: str):
        self._status.configure(text=text)
        self.root.update_idletasks()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    QRPresetApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
