# glitch_image.pyw

import os
import random
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image


def is_image_valid(path):
    """Vérifie si l'image est lisible."""
    try:
        with Image.open(path) as img:
            img.load()
        return True
    except Exception as e:
        print(f"Image invalide : {path} ({e})")
        return False


def get_image_file():
    """Ouvre un dialogue pour sélectionner un fichier image."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Choisis une image à glitcher",
        filetypes=[("Images", "*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff")]
    )
    root.destroy()
    if not file_path:
        sys.exit("Aucun fichier sélectionné.")
    return file_path


def get_parameters(default_glitches=100, default_images=10):
    """Demande à l'utilisateur le nombre de glitches et d'images à créer."""
    def submit():
        try:
            glitches = int(glitches_entry.get())
            images = int(images_entry.get())
            if glitches < 1 or images < 1:
                raise ValueError
            root.param_values = (glitches, images)
            root.destroy()
        except ValueError:
            messagebox.showerror("Erreur", "Merci d’entrer des nombres valides > 0")

    root = tk.Tk()
    root.title("Paramètres du glitch")

    tk.Label(root, text="Nombre de glitches :").grid(row=0, column=0, padx=10, pady=5)
    glitches_entry = tk.Entry(root)
    glitches_entry.insert(0, str(default_glitches))
    glitches_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(root, text="Nombre d’images à créer :").grid(row=1, column=0, padx=10, pady=5)
    images_entry = tk.Entry(root)
    images_entry.insert(0, str(default_images))
    images_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Button(root, text="OK", command=submit).grid(row=2, column=0, columnspan=2, pady=10)
    root.mainloop()

    return getattr(root, "param_values", (default_glitches, default_images))


def glitch_image(original_content, glitches_count):
    """Retourne un bytearray glitché à partir du contenu original."""
    data = bytearray(original_content)
    start_idx = min(200, len(data))  # ne pas toucher à l'en-tête
    for _ in range(glitches_count):
        idx = random.randint(start_idx, len(data) - 1)
        data[idx] = random.randint(0, 255)
    return data

def create_video_from_images(out_dir, base_name, ext, framerate=10):
    """Utilise FFmpeg pour convertir les images glitchées en vidéo."""
    video_path = os.path.join(out_dir, f"{base_name}_GLITCH_VIDEO.mp4")
    pattern = os.path.join(out_dir, f"{base_name}_GLITCH_%03d{ext}").replace("\\", "/")
    try:
        subprocess.run([
            "ffmpeg",
            "-y",  # overwrite
            "-framerate", str(framerate),
            "-i", pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            video_path
        ], check=True)
        print(f"Vidéo créée : {video_path}")
        return video_path
    except subprocess.CalledProcessError as e:
        print(f"Erreur FFmpeg : {e}")
        return None

def main():
    file_path = get_image_file()
    number_of_glitches, number_of_images = get_parameters()

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    ext = os.path.splitext(file_path)[1]

    out_dir = os.path.join(os.path.dirname(file_path), "GLITCHED")
    os.makedirs(out_dir, exist_ok=True)

    with open(file_path, "rb") as f:
        original_content = f.read()

    for frame in range(number_of_images):
        valid = False
        attempt = 0
        while not valid:
            attempt += 1
            data = glitch_image(original_content, number_of_glitches)
            out_path = os.path.join(out_dir, f"{base_name}_GLITCH_{frame:03d}{ext}")
            with open(out_path, "wb") as out_f:
                out_f.write(data)
            valid = is_image_valid(out_path)
            if not valid:
                os.remove(out_path)
                print(f"Tentative {attempt} échouée pour l'image {frame}")

        print(f"Créé : {out_path}")

    # Génération de la vidéo
    video_file = create_video_from_images(out_dir, base_name, ext)
    if video_file:
        messagebox.showinfo("Terminé", f"Images glitchées et vidéo créées :\n{video_file}")
    else:
        messagebox.showinfo("Terminé", f"Images glitchées sauvegardées dans :\n{out_dir}")


if __name__ == "__main__":
    main()
