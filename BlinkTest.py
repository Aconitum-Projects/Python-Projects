import tkinter as tk
import pyautogui
import pygetwindow as gw
import time

def envoyer_signal():
    try:
        # 1. Trouver la fenêtre du jeu
        # Remplace "Rhythm Doctor" par le nom exact de la fenêtre si besoin
        jeu = gw.getWindowsWithTitle('Rhythm Doctor')[0]
        
        # 2. Forcer le focus sur le jeu
        jeu.activate()
        time.sleep(0.05) # Court délai pour le changement de focus
        
        # 3. Simuler un appui long (plus fiable pour les jeux de rythme)
        pyautogui.keyDown('space')
        time.sleep(0.05) 
        pyautogui.keyUp('space')
        
        print("Coup de défibrillateur envoyé !")
    except IndexError:
        print("Erreur : Le jeu Rhythm Doctor n'est pas lancé.")

# Interface
root = tk.Tk()
root.title("RD Assistant")
root.attributes('-topmost', True) # Reste au-dessus du jeu

btn = tk.Button(root, text="🔥 HIT !", command=envoyer_signal, 
                width=20, height=5, bg="red", fg="white", font=('bold', 12))
btn.pack(padx=20, pady=20)

root.mainloop()