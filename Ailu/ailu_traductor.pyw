import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYMBOLS_PATH = os.path.join(BASE_DIR, "symbols")
BACKGROUND = "#1e1e1e"
TEXT_COLOR = "#dddddd"
DEFAULT_SYMBOL_SIZE = 40
DEFAULT_SPACING = 4

mapping = {
    "a": "a.png", "b": "b.png", "d": "d.png", "e": "è.png",
    "f": "f.png", "i": "ii.png", "j": "j.png", "k": "k.png",
    "l": "l.png", "m": "m.png", "n": "n.png", "o": "o.png",
    "p": "p.png", "r": "r.png", "s": "s.png", "t": "t.png",
    "u": "ou.png", "v": "v.png", "y": "y.png", "z": "z.png",
    ".": "dot.png", "!": "excl.png", "?": "quest.png"
}

# Stockage global des images
loaded_images = []


def update_output(*args):
    global loaded_images
    for widget in output_frame.winfo_children():
        widget.destroy()
    loaded_images = []

    text = input_var.get().lower()
    symbol_size = size_var.get()
    spacing = spacing_var.get()

    for char in text:
        if char == " ":
            # Crée un espace visuel ajustable
            spacer = tk.Label(output_frame, width=int(spacing / 4), bg=BACKGROUND)
            spacer.pack(side="left")
            continue

        if char in mapping:
            img_path = os.path.join(SYMBOLS_PATH, mapping[char])

            if os.path.exists(img_path):
                img = Image.open(img_path).convert("RGBA")
                img = img.resize((symbol_size, symbol_size), Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                loaded_images.append(img_tk)
                label = tk.Label(output_frame, image=img_tk, bg=BACKGROUND, bd=0)
                label.pack(side="left", padx=spacing)
            else:
                tk.Label(output_frame, text=char, fg="#888", bg=BACKGROUND).pack(side="left", padx=spacing)
        else:
            tk.Label(output_frame, text=char, fg="#555", bg=BACKGROUND).pack(side="left", padx=spacing)


# --- INTERFACE ---
root = tk.Tk()
root.title("Traducteur Ailu — Alphabet")
root.configure(bg=BACKGROUND)

title = tk.Label(root, text="Traducteur d'alphabet Ailu", fg=TEXT_COLOR, bg=BACKGROUND, font=("Consolas", 18))
title.pack(pady=(10, 10))

input_var = tk.StringVar()
input_var.trace_add("write", update_output)

entry = tk.Entry(root, textvariable=input_var, font=("Consolas", 16),
                 bg="#2a2a2a", fg=TEXT_COLOR, insertbackground="white", width=40)
entry.pack(pady=(0, 20))

# sliders
controls = tk.Frame(root, bg=BACKGROUND)
controls.pack(pady=(0, 20))

# Taille
tk.Label(controls, text="Taille :", fg=TEXT_COLOR, bg=BACKGROUND).pack(side="left", padx=(0, 5))
size_var = tk.IntVar(value=DEFAULT_SYMBOL_SIZE)
size_slider = tk.Scale(controls, from_=20, to=200, orient="horizontal",
                       variable=size_var, command=lambda e: update_output(),
                       bg=BACKGROUND, fg=TEXT_COLOR, troughcolor="#444", highlightthickness=0, length=150)
size_slider.pack(side="left", padx=(0, 20))

# Espacement
tk.Label(controls, text="Espacement :", fg=TEXT_COLOR, bg=BACKGROUND).pack(side="left", padx=(0, 5))
spacing_var = tk.IntVar(value=DEFAULT_SPACING)
spacing_slider = tk.Scale(controls, from_=0, to=40, orient="horizontal",
                          variable=spacing_var, command=lambda e: update_output(),
                          bg=BACKGROUND, fg=TEXT_COLOR, troughcolor="#444", highlightthickness=0, length=150)
spacing_slider.pack(side="left")

output_frame = tk.Frame(root, bg=BACKGROUND)
output_frame.pack(pady=10)

tk.Label(root, text="Tape quelque chose ci-dessus...", fg="#666", bg=BACKGROUND).pack(pady=(10, 10))

root.mainloop()
