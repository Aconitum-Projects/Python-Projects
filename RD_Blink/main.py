import os
import time
import ctypes
import sys
import threading
import tkinter as tk


class PauseNotifier:
    """Affiche un popup non-bloquant indiquant l'état pause ou reprise."""

    def show(self, paused: bool):
        text = "\u23f8  EN PAUSE" if paused else "\u25b6  REPRIS"
        bg = "#E67E22" if paused else "#27AE60"
        self.show_message(text=text, bg=bg)

    def show_message(self, text: str, bg: str = "#2C3E50"):
        threading.Thread(target=self._show, args=(text, bg), daemon=True).start()

    def _show(self, text: str, bg: str):
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.92)

            label = tk.Label(
                root, text=text, bg=bg, fg="white",
                font=("Arial", 28, "bold"), padx=40, pady=24
            )
            label.pack()

            root.update_idletasks()
            w  = root.winfo_reqwidth()
            h  = root.winfo_reqheight()
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

            # Force le passage au premier plan via Win32 — nécessaire contre les jeux plein écran
            root.update()
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                HWND_TOPMOST   = -1
                SWP_NOMOVE     = 0x0002
                SWP_NOSIZE     = 0x0001
                SWP_NOACTIVATE = 0x0010
                # Récupère le HWND de la fenêtre Tkinter via son ID wm
                tk_hwnd = ctypes.windll.user32.FindWindowW(None, None)
                # Utilise l'id interne Tkinter pour forcer HWND_TOPMOST
                wid = root.winfo_id()
                ctypes.windll.user32.SetWindowPos(
                    wid, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
            except Exception:
                pass

            root.after(2500, root.destroy)
            root.mainloop()
        except Exception:
            pass


class BlinkKeyboardTrigger:
    def __init__(self, config: dict):
        self.enabled = bool(config.get("enabled", True))
        self.window_title = str(config.get("window_title", "Rhythm Doctor"))
        self.key = str(config.get("key", "space"))
        self.hold_ms = int(config.get("hold_ms", 50))
        self.cooldown_ms = int(config.get("cooldown_ms", 120))
        self.focus_window = bool(config.get("focus_window", True))
        self.focus_delay_ms = int(config.get("focus_delay_ms", 80))
        self.send_method = str(config.get("send_method", "auto")).lower()
        self.allow_method_fallback = bool(config.get("allow_method_fallback", True))
        self.debug_logs = bool(config.get("debug_logs", True))
        self._last_trigger_time = 0.0
        self._ready = False

        if not self.enabled:
            return

        try:
            import pyautogui
            import pygetwindow as gw
        except ModuleNotFoundError:
            print("[Keyboard] pyautogui/pygetwindow manquants. Trigger clavier désactivé.")
            return

        try:
            import pydirectinput
            self.pydirectinput = pydirectinput
        except ModuleNotFoundError:
            self.pydirectinput = None

        self.pyautogui = pyautogui
        self.gw = gw
        self.pyautogui.FAILSAFE = False
        self.user32 = ctypes.windll.user32
        self._ready = True
        print(
            "[Keyboard] Trigger actif: "
            f"key={self.key}, window='{self.window_title}', method={self.send_method}"
        )

    def _resolve_send_method(self) -> str:
        if self.send_method == "win32":
            return "win32"
        if self.send_method in ("directinput", "pydirectinput"):
            return "directinput"
        if self.send_method == "pyautogui":
            return "pyautogui"

        # auto: prefer DirectInput for better compatibility with many games.
        if self.pydirectinput is not None:
            return "directinput"
        return "win32"

    def _method_candidates(self) -> list[str]:
        preferred = self._resolve_send_method()
        if not self.allow_method_fallback:
            return [preferred]

        methods = [preferred]
        for method in ("directinput", "win32", "pyautogui"):
            if method not in methods:
                methods.append(method)
        return methods

    def _vk_from_key(self, key: str) -> int:
        key_norm = key.strip().lower()
        special = {
            "space": 0x20,
            "enter": 0x0D,
            "left": 0x25,
            "up": 0x26,
            "right": 0x27,
            "down": 0x28,
        }
        if key_norm in special:
            return special[key_norm]
        if len(key_norm) == 1 and "a" <= key_norm <= "z":
            return ord(key_norm.upper())
        if key_norm.startswith("f") and key_norm[1:].isdigit():
            fn = int(key_norm[1:])
            if 1 <= fn <= 24:
                return 0x70 + (fn - 1)
        raise ValueError(f"Touche non supportee pour win32: {key}")

    def _send_key_win32(self):
        vk = self._vk_from_key(self.key)
        key_up_flag = 0x0002
        hold_seconds = max(self.hold_ms, 1) / 1000.0
        self.user32.keybd_event(vk, 0, 0, 0)
        time.sleep(hold_seconds)
        self.user32.keybd_event(vk, 0, key_up_flag, 0)

    def _send_key(self, method: str):
        hold_seconds = max(self.hold_ms, 1) / 1000.0

        if method == "directinput":
            if self.pydirectinput is None:
                raise RuntimeError("pydirectinput n'est pas installé")
            self.pydirectinput.keyDown(self.key)
            time.sleep(hold_seconds)
            self.pydirectinput.keyUp(self.key)
            return

        if method == "win32":
            self._send_key_win32()
            return

        self.pyautogui.keyDown(self.key)
        time.sleep(hold_seconds)
        self.pyautogui.keyUp(self.key)

    def _focus_game_window(self):
        windows = self.gw.getWindowsWithTitle(self.window_title)
        if not windows:
            raise RuntimeError(f"Fenetre introuvable: '{self.window_title}'")

        game_window = windows[0]
        game_window.activate()

        # Force foreground in case activate() is ignored by Windows focus rules.
        hwnd = getattr(game_window, "_hWnd", None)
        if hwnd:
            self.user32.ShowWindow(hwnd, 5)
            self.user32.SetForegroundWindow(hwnd)

        time.sleep(max(self.focus_delay_ms, 0) / 1000.0)

    def on_blink(self) -> bool:
        if not self.enabled or not self._ready:
            return False

        now = time.time() * 1000.0
        if now - self._last_trigger_time < self.cooldown_ms:
            return False

        self._last_trigger_time = now

        try:
            if self.focus_window:
                self._focus_game_window()

            sent_method = None
            last_error = None
            for method in self._method_candidates():
                try:
                    self._send_key(method)
                    sent_method = method
                    break
                except Exception as exc:
                    last_error = exc

            if sent_method is None:
                raise RuntimeError(f"Echec envoi touche. Derniere erreur: {last_error}")

            if self.debug_logs:
                active_title = ""
                try:
                    active = self.gw.getActiveWindow()
                    active_title = "" if active is None else str(active.title)
                except Exception:
                    active_title = ""
                print(f"[Keyboard] Blink -> touche envoyee ({sent_method}), active='{active_title}'")
            return True
        except Exception as exc:
            print(f"[Keyboard] Erreur trigger: {exc}")
            return False


def _check_gaze(direction: str, yaw: float, pitch: float, yaw_thr: float, pitch_thr: float) -> bool:
    """Vérifie si le regard est dans une direction donnée.
    direction: bottom_left, bottom_right, top_left, top_right, left, right, up, down
    yaw: négatif = gauche, positif = droite  (en degrés)
    pitch: signe dépend de la config MediaPipe — calibrer avec debug_logs: true
    """
    d = direction.replace("_", " ").lower()
    if "left"   in d and yaw  > -yaw_thr:   return False
    if "right"  in d and yaw  <  yaw_thr:   return False
    if "bottom" in d and pitch > -pitch_thr: return False
    if "top"    in d and pitch <  pitch_thr: return False
    return True


def main():
    print("--- DÉMARRAGE DU RELAIS (BLINK CAM -> OSC) ---")

    try:
        import yaml
        from src.Captation.mediapipe_processor import MediaPipeFaceProcessor
        from src.Network.osc_sender import OSCSender
    except ModuleNotFoundError:
        print("[Erreur] Dépendances Python manquantes.")
        print("Lance le projet avec uv:")
        print('  uv run --project "d:/Repository/Python Projects/RD_Blink" python "d:/Repository/Python Projects/RD_Blink/main.py"')
        return

    # 1. Chargement de la configuration
    if getattr(sys, "frozen", False):
        project_root = os.path.dirname(sys.executable)
    else:
        project_root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(project_root, "config", "Network.yaml")
    if not os.path.exists(config_path):
        print(f"[Erreur] Fichier introuvable : {config_path}")
        return

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    config["project_root"] = project_root

    # 2. Initialisation des modules
    # Le processeur va lire la section 'mediapipe_info' dans le yaml
    processor = MediaPipeFaceProcessor(config)
    
    # On configure l'envoi avec la section 'OSC_output' du yaml
    sender_ip = config['OSC_output']['ip']
    sender_port = config['OSC_output']['port']
    sender_address = config['OSC_output']['base_address']

    sender = OSCSender(ip=sender_ip, port=sender_port, base_address=sender_address)

    blink_cfg = config.get("blink_detection", {})
    blink_threshold     = float(blink_cfg.get("threshold", 0.6))
    blink_off_threshold = float(blink_cfg.get("threshold_off", 0.35))
    keyboard_cfg = config.get("keyboard_trigger", {})
    keyboard_trigger = BlinkKeyboardTrigger(keyboard_cfg)
    pause_notifier   = PauseNotifier()

    gaze_cfg      = config.get("gaze_pause", {})
    gaze_enabled  = bool(gaze_cfg.get("enabled", True))
    gaze_dir_pause  = str(gaze_cfg.get("direction_pause",  "right")).lower()
    gaze_dir_resume = str(gaze_cfg.get("direction_resume", "left" )).lower()
    gaze_yaw_thr   = float(gaze_cfg.get("yaw_threshold", 20.0))
    gaze_pitch_thr = float(gaze_cfg.get("pitch_threshold", 0.0))
    gaze_cooldown  = float(gaze_cfg.get("cooldown_seconds", 1.5))
    gaze_debug     = bool(gaze_cfg.get("debug_logs", True))

    print("--- SYSTÈME ACTIF ---")
    print("Appuyez sur Ctrl+C pour quitter.")
    if gaze_enabled:
        print(f"[Pause] Regard '{gaze_dir_pause}' = pause | '{gaze_dir_resume}' = reprise.")
        if gaze_debug:
            print("[Gaze] debug_logs actif — valeurs yaw/pitch affichées en temps réel.")

    premier_paquet          = False
    was_blinking            = False
    paused                  = False
    was_in_gaze_pause_pos   = False
    was_in_gaze_resume_pos  = False
    gaze_last_trigger       = 0.0
    _gaze_log_count         = 0

    # 3. Boucle principale
    try:
        while True:
            data_dict = processor.get_processed_data()

            if data_dict:
                blink_value = float(data_dict.get("blink", 0.0))
                gaze_yaw    = float(data_dict.get("gaze_yaw", 0.0))
                gaze_pitch  = float(data_dict.get("gaze_pitch", 0.0))

                # Hystérésis blink
                if blink_value >= blink_threshold:
                    is_blinking = True
                elif blink_value < blink_off_threshold:
                    is_blinking = False
                else:
                    is_blinking = was_blinking

                if not premier_paquet:
                    print("[SUCCES] Flux blink detecte, envoi OSC en cours...")
                    premier_paquet = True

                sender.send_dict(data_dict)

                # — Clignement court : déclenche la touche sur front descendant
                if not is_blinking and was_blinking and not paused:
                    keyboard_trigger.on_blink()
                was_blinking = is_blinking

                # — Debug gaze (toutes les ~30 trames ≈ 300ms)
                if gaze_debug and premier_paquet:
                    _gaze_log_count += 1
                    if _gaze_log_count % 30 == 0:
                        status = "EN PAUSE" if paused else "actif"
                        print(f"[Gaze] yaw={gaze_yaw:+.1f}°  pitch={gaze_pitch:+.1f}°  [{status}]")

                # — Pause/reprise via flick du regard (directions séparées)
                if gaze_enabled:
                    now = time.time()
                    in_pause_pos  = _check_gaze(gaze_dir_pause,  gaze_yaw, gaze_pitch, gaze_yaw_thr, gaze_pitch_thr)
                    in_resume_pos = _check_gaze(gaze_dir_resume, gaze_yaw, gaze_pitch, gaze_yaw_thr, gaze_pitch_thr)

                    if in_pause_pos and not was_in_gaze_pause_pos:
                        if not paused and now - gaze_last_trigger >= gaze_cooldown:
                            paused = True
                            pause_notifier.show(paused)
                            gaze_last_trigger = now
                            print("[Pause] EN PAUSE")

                    if in_resume_pos and not was_in_gaze_resume_pos:
                        if paused and now - gaze_last_trigger >= gaze_cooldown:
                            paused = False
                            pause_notifier.show(paused)
                            gaze_last_trigger = now
                            print("[Pause] REPRIS")

                    was_in_gaze_pause_pos  = in_pause_pos
                    was_in_gaze_resume_pos = in_resume_pos

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[Système] Arrêt demandé.")
    finally:
        processor.stop()
        print("[Système] Éteint proprement.")

if __name__ == "__main__":
    main()