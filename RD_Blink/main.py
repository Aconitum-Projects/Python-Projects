import os
import time
import ctypes
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk


class AddonState:
    """Gère l'état de l'addon et notifie les observateurs."""

    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.is_blinking = False
        self.is_left_hand_detected = False
        self.is_left_hand_closed = False
        self.is_left_thumb_closed = False
        self.is_right_hand_detected = False
        self.is_right_hand_closed = False
        self.is_right_thumb_closed = False
        self.status_message = "Addon arrete"
        self.blink_cooldown = 0.3
        self.last_blink_time = 0.0
        self.input_flash_window_seconds = 0.22
        self.last_input_times = {
            "L": 0.0,
            "R": 0.0,
            "U": 0.0,
            "D": 0.0,
        }
        self.input_history = []
        self.observers = []

    def add_observer(self, callback):
        """Ajoute un observateur pour les changements d'état."""
        self.observers.append(callback)

    def notify_observers(self):
        """Notifie tous les observateurs."""
        for callback in self.observers:
            try:
                callback(self)
            except Exception:
                pass

    def set_running(self, running: bool):
        if self.is_running != running:
            self.is_running = running
            if not running:
                self.is_paused = False
                self.is_blinking = False
                self.is_left_hand_detected = False
                self.is_left_hand_closed = False
                self.is_left_thumb_closed = False
                self.is_right_hand_detected = False
                self.is_right_hand_closed = False
                self.is_right_thumb_closed = False
                self.last_input_times = {"L": 0.0, "R": 0.0, "U": 0.0, "D": 0.0}
                self.input_history = []
            self.notify_observers()

    def set_paused(self, paused: bool):
        if self.is_paused != paused:
            self.is_paused = paused
            self.notify_observers()

    def set_blinking(self, blinking: bool):
        if blinking:
            if not self.is_blinking:
                now = time.time()
                if now - self.last_blink_time >= self.blink_cooldown:
                    self.is_blinking = True
                    self.last_blink_time = now
                    self.notify_observers()
                    timer = threading.Timer(0.2, self._reset_blink)
                    timer.daemon = True
                    timer.start()
            return

        if self.is_blinking:
            self.is_blinking = False
            self.notify_observers()

    def set_status_message(self, message: str):
        if self.status_message != message:
            self.status_message = message
            self.notify_observers()

    def set_left_hand_state(self, detected: bool, closed: bool, thumb_closed: bool = False):
        closed = bool(closed and detected)
        thumb_closed = bool(thumb_closed and detected)
        if (
            self.is_left_hand_detected != bool(detected)
            or self.is_left_hand_closed != closed
            or self.is_left_thumb_closed != thumb_closed
        ):
            self.is_left_hand_detected = bool(detected)
            self.is_left_hand_closed = closed
            self.is_left_thumb_closed = thumb_closed
            self.notify_observers()

    def set_right_hand_state(self, detected: bool, closed: bool, thumb_closed: bool = False):
        closed = bool(closed and detected)
        thumb_closed = bool(thumb_closed and detected)
        if (
            self.is_right_hand_detected != bool(detected)
            or self.is_right_hand_closed != closed
            or self.is_right_thumb_closed != thumb_closed
        ):
            self.is_right_hand_detected = bool(detected)
            self.is_right_hand_closed = closed
            self.is_right_thumb_closed = thumb_closed
            self.notify_observers()

    def register_game_input(self, action: str):
        token = str(action).upper()
        if token not in self.last_input_times:
            return

        now = time.time()
        self.last_input_times[token] = now
        timestamp = time.strftime("%H:%M:%S", time.localtime(now))
        self.input_history.append(f"{timestamp} {token}")
        self.input_history = self.input_history[-8:]
        self.notify_observers()

    def _reset_blink(self):
        self.set_blinking(False)


class AddonGUI:
    """Interface graphique pour le Rhythm Doctor Accessibility Addon."""

    def __init__(self, root, state: AddonState, on_toggle_callback=None):
        self.root = root
        self.state = state
        self.on_toggle_callback = on_toggle_callback
        self._popup_window = None
        self._popup_destroy_job = None
        self._popup_bounce_job = None
        self._periodic_refresh_job = None
        self._toggle_bounce_job = None
        self._toggle_bounce_anim_job = None
        self._toggle_bounce_interval_ms = 4800
        self._toggle_bounce_step_delay_ms = 55
        self._toggle_base_pady = 12
        self._toggle_btn_base_y = 10
        self._eye_idle_anim_job = None
        self._eye_anim_running = False
        self._eye_idle_delay_ms = 3200
        self._eye_anim_frame_delay_ms = 90
        self._eye_anim_sequence_keys = []
        self._ui_initialized = False
        self._last_running = state.is_running
        self._last_paused = state.is_paused
        self._background_label = None
        self._background_image = None
        self._widget_bg = "#2C3E50"

        self.root.title("Rhythm Doctor Accessibility Addon")
        self.root.geometry("760x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#2C3E50")

        # Charger les icônes
        self.icon_size = (64, 64)
        self.icon_size_large = (96, 96)  # Larger size for toggle button
        self.icon_size_toggle = (132, 132)
        self.icons = self._load_icons()
        try:
            if self.icons.get("main") is not None:
                self.root.iconphoto(True, self.icons.get("main"))
        except Exception:
            pass

        self._setup_background_image()

        # Observer aux changements d'état
        self.state.add_observer(self._on_state_changed)

        self._build_ui()
        self._apply_widget_backgrounds()
        self._schedule_periodic_refresh()
        self._schedule_toggle_bounce()
        self._schedule_eye_idle_animation()

    def _apply_widget_backgrounds(self):
        """Apply a unified widget background color to reduce panel-like blocks over the background image."""
        def _apply(widget):
            if widget is self._background_label:
                return

            try:
                if isinstance(widget, (tk.Frame, tk.Label, tk.Button)):
                    widget.configure(bg=self._widget_bg)
                if isinstance(widget, tk.Button):
                    widget.configure(activebackground=self._widget_bg)
            except Exception:
                pass

            for child in widget.winfo_children():
                _apply(child)

        _apply(self.root)

    def _schedule_periodic_refresh(self):
        """Refresh UI regularly for transient visual cues (e.g. input flash)."""
        self._update_ui()
        self._periodic_refresh_job = self.root.after(120, self._schedule_periodic_refresh)

    def _set_toggle_bounce_offset(self, offset: int):
        if hasattr(self, "toggle_button_frame") and self.toggle_button_frame is not None:
            self.toggle_btn.place_configure(y=max(self._toggle_btn_base_y + int(offset), 0))

    def _play_toggle_bounce(self):
        if not self.state.is_running:
            self._set_toggle_bounce_offset(0)
            self._toggle_bounce_anim_job = None
            return

        # Two short in-place jumps before waiting for the next cycle.
        single_jump = (-3, -8, -12, -8, -3, 1, 0)
        offsets = single_jump + (0, 0, 0) + single_jump

        def _step(idx: int):
            if not self.state.is_running:
                self._set_toggle_bounce_offset(0)
                self._toggle_bounce_anim_job = None
                return

            self._set_toggle_bounce_offset(offsets[idx])
            if idx + 1 < len(offsets):
                self._toggle_bounce_anim_job = self.root.after(
                    self._toggle_bounce_step_delay_ms,
                    lambda: _step(idx + 1),
                )
            else:
                self._set_toggle_bounce_offset(0)
                self._toggle_bounce_anim_job = None

        _step(0)

    def _schedule_toggle_bounce(self):
        if self.state.is_running and self._toggle_bounce_anim_job is None:
            self._play_toggle_bounce()
        elif not self.state.is_running:
            self._set_toggle_bounce_offset(0)

        self._toggle_bounce_job = self.root.after(
            self._toggle_bounce_interval_ms,
            self._schedule_toggle_bounce,
        )

    def _can_play_eye_idle_animation(self) -> bool:
        return bool(self.state.is_running and (not self.state.is_paused) and (not self.state.is_blinking))

    def _schedule_eye_idle_animation(self):
        if self._eye_idle_anim_job is not None:
            try:
                self.root.after_cancel(self._eye_idle_anim_job)
            except Exception:
                pass
            self._eye_idle_anim_job = None

        self._eye_idle_anim_job = self.root.after(self._eye_idle_delay_ms, self._maybe_play_eye_idle_animation)

    def _maybe_play_eye_idle_animation(self):
        self._eye_idle_anim_job = None

        # If the required sprites are missing, keep normal behavior.
        has_sequence = len(self._eye_anim_sequence_keys) > 0 and all(
            self.icons.get(key) is not None for key in self._eye_anim_sequence_keys
        )
        if not has_sequence:
            self._schedule_eye_idle_animation()
            return

        if self._eye_anim_running or (not self._can_play_eye_idle_animation()):
            self._schedule_eye_idle_animation()
            return

        self._play_eye_idle_animation()

    def _play_eye_idle_animation(self):
        self._eye_anim_running = True

        def _step(idx: int):
            if not self._can_play_eye_idle_animation():
                self._eye_anim_running = False
                self.blink_btn.config(image=self.icons.get("eye_open"))
                self.blink_btn.image = self.icons.get("eye_open")
                self._schedule_eye_idle_animation()
                return

            if idx < len(self._eye_anim_sequence_keys):
                icon_key = self._eye_anim_sequence_keys[idx]
                icon = self.icons.get(icon_key)
                if icon is not None:
                    self.blink_btn.config(image=icon)
                    self.blink_btn.image = icon
                self.root.after(self._eye_anim_frame_delay_ms, lambda: _step(idx + 1))
                return

            self.blink_btn.config(image=self.icons.get("eye_open"))
            self.blink_btn.image = self.icons.get("eye_open")
            self._eye_anim_running = False
            self._schedule_eye_idle_animation()

        _step(0)

    def _close_action_popup(self):
        if self._popup_destroy_job is not None:
            self.root.after_cancel(self._popup_destroy_job)
            self._popup_destroy_job = None

        if self._popup_bounce_job is not None:
            self.root.after_cancel(self._popup_bounce_job)
            self._popup_bounce_job = None

        if self._popup_window is not None:
            try:
                self._popup_window.destroy()
            except Exception:
                pass
            self._popup_window = None

    def _schedule_pause_blink(self):
        """Fait clignoter le popup tant que l'etat pause est actif."""
        if self._popup_window is None or not self.state.is_running or not self.state.is_paused:
            self._popup_bounce_job = None
            return

        try:
            current_alpha = float(self._popup_window.attributes("-alpha"))
            next_alpha = 0.28 if current_alpha > 0.5 else 0.72
            self._popup_window.attributes("-alpha", next_alpha)
        except Exception:
            pass

        self._popup_bounce_job = self.root.after(420, self._schedule_pause_blink)

    def _show_action_popup(self, action: str, duration_ms: int = 2200, persistent: bool = False):
        """Affiche un popup d'action discret en haut-gauche."""
        popup_icon = {
            "on": "on_large",
            "off": "off_large",
            "pause": "pause_large",
            "play": "play_large",
        }

        try:
            self._close_action_popup()

            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.attributes("-alpha", 0.72)
            popup.configure(bg="#000000")

            icon_key = popup_icon.get(action, "play_large")
            icon = self.icons.get(icon_key)
            label = tk.Label(
                popup,
                image=icon,
                bg="#000000",
                padx=12,
                pady=12,
            )
            label.image = icon
            label.pack()

            popup.update_idletasks()
            w = popup.winfo_reqwidth()
            h = popup.winfo_reqheight()
            popup.geometry(f"{w}x{h}+22+22")

            # Renforce le top-most via Win32 pour les applis plein écran.
            try:
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_SHOWWINDOW = 0x0040
                wid = popup.winfo_id()
                ctypes.windll.user32.SetWindowPos(
                    wid,
                    HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
                )
            except Exception:
                pass

            try:
                popup.lift()
            except Exception:
                pass

            self._popup_window = popup

            def _close_popup():
                self._close_action_popup()

            if persistent:
                self._schedule_pause_blink()
            else:
                self._popup_destroy_job = self.root.after(duration_ms, _close_popup)
        except Exception as exc:
            print(f"[GUI] Erreur popup: {exc}")

    def _load_icons(self):
        """Charge les icônes PNG depuis le dossier icons."""
        icons = {}
        icon_files = {
            "main": "Main.png",
            "on": "On.png",
            "off": "Off.png",
            "pause": "Pause.png",
            "pause_disabled": "Pause_Disabled.png",
            "play": "Play.png",
            "play_disabled": "Play_Disabled.png",
            "eye_open": "Eye_open.png",
            "eye_open_disabled": "Eye_open_Disabled.png",
            "eye_closed": "Eye_Closed.png",
            "eye_closed_disabled": "Eye_Closed_Disabled.png",
            "hand_l_open": "Hand_L_Open.png",
            "hand_l_closed": "Hand_L_Closed.png",
            "hand_l_thumb_closed": "Hand_L_ThumbClosed.png",
            "hand_l_disabled": "Hand_L_Disabled.png",
            "hand_r_open": "Hand_R_Open.png",
            "hand_r_closed": "Hand_R_Closed.png",
            "hand_r_thumb_closed": "Hand_R_ThumbClosed.png",
            "hand_r_disabled": "Hand_R_Disabled.png",
        }

        project_root = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(project_root, "icons")

        # Load regular and large icons
        for size_name, size in [(None, self.icon_size), ("_large", self.icon_size_large), ("_toggle", self.icon_size_toggle)]:
            for key, filename in icon_files.items():
                try:
                    filepath = os.path.join(icons_dir, filename)
                    if os.path.exists(filepath):
                        img = Image.open(filepath)
                        if img.size != size:
                            # Keep sprite rendering crisp: no smoothing filter.
                            img = img.resize(size, Image.Resampling.NEAREST)
                        icon_key = f"{key}{size_name}" if size_name else key
                        icons[icon_key] = ImageTk.PhotoImage(img)
                    elif size_name is None:
                        print(f"[GUI] Icone manquante: {filepath}")
                except Exception as e:
                    if size_name is None:
                        print(f"[GUI] Erreur chargement icone {key}: {e}")

        # Idle eye animation frames are loaded from icons/animEye in sorted order.
        self._eye_anim_sequence_keys = []
        anim_eye_dir = os.path.join(icons_dir, "animEye")
        try:
            if os.path.isdir(anim_eye_dir):
                valid_ext = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
                frame_files = sorted(
                    f for f in os.listdir(anim_eye_dir)
                    if os.path.splitext(f)[1].lower() in valid_ext
                )

                for idx, filename in enumerate(frame_files, start=1):
                    frame_path = os.path.join(anim_eye_dir, filename)
                    img = Image.open(frame_path)
                    if img.size != self.icon_size:
                        img = img.resize(self.icon_size, Image.Resampling.NEAREST)
                    icon_key = f"eye_look_{idx:02d}"
                    icons[icon_key] = ImageTk.PhotoImage(img)
                    self._eye_anim_sequence_keys.append(icon_key)
            else:
                print(f"[GUI] Dossier animation oeil introuvable: {anim_eye_dir}")
        except Exception as e:
            print(f"[GUI] Erreur chargement animEye: {e}")

        return icons

    def _setup_background_image(self):
        """Sets a background image behind all widgets when available."""
        try:
            project_root = os.path.dirname(os.path.abspath(__file__))
            icons_dir = os.path.join(project_root, "icons")
            candidates = [
                "Background.png",
                "Background.jpg",
                "Background.jpeg",
                "background.png",
                "background.jpg",
                "background.jpeg",
            ]
            background_path = None

            for filename in candidates:
                candidate = os.path.join(icons_dir, filename)
                if os.path.exists(candidate):
                    background_path = candidate
                    break

            if background_path is None:
                return

            bg_img = Image.open(background_path)
            target_size = (760, 520)
            if bg_img.size != target_size:
                bg_img = bg_img.resize(target_size, Image.Resampling.NEAREST)

            # Use center pixel as the UI background key color to avoid visible blue panels.
            sample = bg_img.convert("RGB").getpixel((target_size[0] // 2, target_size[1] // 2))
            self._widget_bg = f"#{sample[0]:02x}{sample[1]:02x}{sample[2]:02x}"
            self.root.configure(bg=self._widget_bg)

            self._background_image = ImageTk.PhotoImage(bg_img)
            self._background_label = tk.Label(self.root, image=self._background_image, bd=0)
            self._background_label.place(x=0, y=0, relwidth=1, relheight=1)
            self._background_label.lower()
        except Exception as exc:
            print(f"[GUI] Erreur fond: {exc}")

    def _build_ui(self):
        """Construit l'interface utilisateur."""
        # Titre
        title_font = tkfont.Font(family="Arial", size=17, weight="bold")
        title_label = tk.Label(
            self.root,
            text="Rhythm Doctor Accessibility Addon",
            font=title_font,
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        title_label.pack(pady=(18, 14))

        self.state_frame = tk.Frame(self.root, bg="#2C3E50")
        self.state_frame.pack(pady=(4, 8))

        self.hand_col = tk.Frame(self.state_frame, bg="#2C3E50")
        self.hand_col.pack(side="left", padx=(8, 18))

        self.center_col = tk.Frame(self.state_frame, bg="#2C3E50")
        self.center_col.pack(side="left", padx=6)

        self.right_hand_col = tk.Frame(self.state_frame, bg="#2C3E50")
        self.right_hand_col.pack(side="left", padx=(18, 8))

        self.pause_col = tk.Frame(self.center_col, bg="#2C3E50")
        self.pause_col.pack(pady=(0, 8))

        self.pause_title = tk.Label(
            self.pause_col,
            text="Playing",
            font=("Arial", 11, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.pause_title.pack(pady=(0, 8))

        # Bouton Pause
        self.pause_btn = tk.Label(
            self.pause_col,
            image=self.icons.get("play"),
            bg="#2C3E50",
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.pause_btn.image = self.icons.get("play")
        self.pause_btn.pack(pady=8)

        # Pause help texts with formatting
        self.pause_help_frame = tk.Frame(self.pause_col, bg="#2C3E50")
        self.pause_help_frame.pack(pady=(4, 0))

        self.left_label = tk.Label(
            self.pause_help_frame,
            text="Turn head ",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.left_label.pack(side="left")

        self.left_bold = tk.Label(
            self.pause_help_frame,
            text="left",
            font=("Arial", 9, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.left_bold.pack(side="left")

        self.to_pause = tk.Label(
            self.pause_help_frame,
            text=" to PAUSE",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.to_pause.pack(side="left")

        # Second pause help line
        self.pause_help_frame2 = tk.Frame(self.pause_col, bg="#2C3E50")
        self.pause_help_frame2.pack(pady=(2, 0))

        self.right_label = tk.Label(
            self.pause_help_frame2,
            text="Turn head ",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.right_label.pack(side="left")

        self.right_bold = tk.Label(
            self.pause_help_frame2,
            text="right",
            font=("Arial", 9, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.right_bold.pack(side="left")

        self.to_play = tk.Label(
            self.pause_help_frame2,
            text=" to PLAY",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.to_play.pack(side="left")

        # Bouton On/Off centré entre Play et Blink
        self.toggle_button_frame = tk.Frame(self.center_col, bg="#2C3E50")
        self.toggle_button_frame.config(width=184, height=156)
        self.toggle_button_frame.pack_propagate(False)
        self.toggle_button_frame.pack(pady=self._toggle_base_pady)

        self.toggle_btn = tk.Button(
            self.toggle_button_frame,
            image=self.icons.get("off_toggle"),
            bg="#2C3E50",
            activebackground="#2C3E50",
            bd=0,
            highlightthickness=0,
            command=self._on_toggle,
            cursor="hand2"
        )
        self.toggle_btn.image = self.icons.get("off_toggle")
        self.toggle_btn.place(relx=0.5, y=self._toggle_btn_base_y, anchor="n")

        self.blink_col = tk.Frame(self.center_col, bg="#2C3E50")
        self.blink_col.pack(pady=(8, 0))

        self.blink_title = tk.Label(
            self.blink_col,
            text="Blinking",
            font=("Arial", 11, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.blink_title.pack(pady=(0, 8))

        # Bouton Blink
        self.blink_btn = tk.Label(
            self.blink_col,
            image=self.icons.get("eye_open"),
            bg="#2C3E50",
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.blink_btn.image = self.icons.get("eye_open")
        self.blink_btn.pack(pady=8)

        self.blink_help = tk.Label(
            self.blink_col,
            text="Blink to CLICK",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.blink_help.pack(pady=(4, 0))

        self.hand_title = tk.Label(
            self.hand_col,
            text="Left Hand",
            font=("Arial", 11, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.hand_title.pack(pady=(0, 8))

        self.hand_state_label = tk.Label(
            self.hand_col,
            text="Left Hand",
            font=("Arial", 8, "bold"),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.hand_state_label.pack(pady=(4, 0))

        self.hand_btn = tk.Label(
            self.hand_col,
            image=self.icons.get("hand_l_disabled"),
            bg="#2C3E50",
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.hand_btn.image = self.icons.get("hand_l_disabled")
        self.hand_btn.pack(pady=8)

        self.hand_status_help = tk.Label(
            self.hand_col,
            text="Disabled / Open / Closed / Thumb",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.hand_status_help.pack(pady=(2, 0))

        self.right_hand_title = tk.Label(
            self.right_hand_col,
            text="Right Hand",
            font=("Arial", 11, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.right_hand_title.pack(pady=(0, 8))

        self.right_hand_state_label = tk.Label(
            self.right_hand_col,
            text="Right Hand",
            font=("Arial", 8, "bold"),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.right_hand_state_label.pack(pady=(4, 0))

        self.right_hand_btn = tk.Label(
            self.right_hand_col,
            image=self.icons.get("hand_r_disabled"),
            bg="#2C3E50",
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.right_hand_btn.image = self.icons.get("hand_r_disabled")
        self.right_hand_btn.pack(pady=8)

        self.right_hand_status_help = tk.Label(
            self.right_hand_col,
            text="Disabled / Open / Closed / Thumb",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.right_hand_status_help.pack(pady=(2, 0))

        self.input_debug_frame = tk.Frame(self.root, bg="#2C3E50")
        self.input_debug_frame.pack(pady=(8, 0))

        self.input_debug_title = tk.Label(
            self.input_debug_frame,
            text="Game Inputs",
            font=("Arial", 10, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.input_debug_title.pack(pady=(0, 4))

        self.input_lights_frame = tk.Frame(self.input_debug_frame, bg="#2C3E50")
        self.input_lights_frame.pack()

        self.input_light_labels = {}
        for token in ("L", "D", "U", "R"):
            lbl = tk.Label(
                self.input_lights_frame,
                text=token,
                font=("Arial", 9, "bold"),
                width=3,
                bg="#4A5568",
                fg="#ECF0F1",
                relief="flat",
                padx=4,
                pady=2,
            )
            lbl.pack(side="left", padx=4)
            self.input_light_labels[token] = lbl

        self.input_debug_history = tk.Label(
            self.input_debug_frame,
            text="No input sent yet",
            font=("Arial", 8),
            bg="#2C3E50",
            fg="#7F8C8D"
        )
        self.input_debug_history.pack(pady=(5, 0))

    def _on_toggle(self):
        """Appelle le callback de basculement."""
        if self.on_toggle_callback:
            self.on_toggle_callback(not self.state.is_running)

    def _on_state_changed(self, state: AddonState):
        """Appelé quand l'état change."""
        self.root.after(0, self._update_ui)

    def _update_ui(self):
        """Met à jour l'interface en fonction de l'état."""
        try:
            # Couleurs pour les états
            normal_color = "#ECF0F1"
            normal_gray = "#7F8C8D"
            faded_color = "#4A5568"
            faded_gray = "#354560"

            # Bouton On/Off
            if self.state.is_running:
                self.toggle_btn.config(image=self.icons.get("on_toggle"))
                self.toggle_btn.image = self.icons.get("on_toggle")
            else:
                self.toggle_btn.config(image=self.icons.get("off_toggle"))
                self.toggle_btn.image = self.icons.get("off_toggle")
                self._set_toggle_bounce_offset(0)

            # Si OFF: tout grisé/peu visible
            if not self.state.is_running:
                # Pause column
                self.pause_title.config(fg=faded_color)
                self.left_label.config(fg=faded_gray)
                self.left_bold.config(fg=faded_color)
                self.to_pause.config(fg=faded_gray)
                self.right_label.config(fg=faded_gray)
                self.right_bold.config(fg=faded_color)
                self.to_play.config(fg=faded_gray)
                self.pause_btn.config(image=self.icons.get("play_disabled"))
                self.pause_btn.image = self.icons.get("play_disabled")
                # Blink column
                self.blink_title.config(fg=faded_color)
                self.blink_help.config(fg=faded_gray)
                self.blink_btn.config(image=self.icons.get("eye_open_disabled"))
                self.blink_btn.image = self.icons.get("eye_open_disabled")
                self.hand_title.config(fg=faded_color)
                self.hand_state_label.config(fg=faded_color)
                self.hand_status_help.config(fg=faded_gray)
                self.hand_btn.config(image=self.icons.get("hand_l_disabled"))
                self.hand_btn.image = self.icons.get("hand_l_disabled")
                self.right_hand_title.config(fg=faded_color)
                self.right_hand_state_label.config(fg=faded_color)
                self.right_hand_status_help.config(fg=faded_gray)
                self.right_hand_btn.config(image=self.icons.get("hand_r_disabled"))
                self.right_hand_btn.image = self.icons.get("hand_r_disabled")
            else:
                # Si ON et Playing: fade right text, blink normal
                if not self.state.is_paused:
                    self.pause_title.config(fg=normal_color)
                    self.left_label.config(fg=normal_gray)
                    self.left_bold.config(fg=normal_color)
                    self.to_pause.config(fg=normal_gray)
                    # Fade right text
                    self.right_label.config(fg=faded_gray)
                    self.right_bold.config(fg=faded_color)
                    self.to_play.config(fg=faded_gray)
                    # Play button normal
                    self.pause_btn.config(image=self.icons.get("play"))
                    self.pause_btn.image = self.icons.get("play")
                    # Blink normal
                    self.blink_title.config(fg=normal_color)
                    self.blink_help.config(fg=normal_gray)
                    if not self._eye_anim_running:
                        self.blink_btn.config(image=self.icons.get("eye_open"))
                        self.blink_btn.image = self.icons.get("eye_open")
                    self.hand_title.config(fg=normal_color)
                    self.hand_state_label.config(fg=normal_color)
                    self.hand_status_help.config(fg=normal_gray)
                    self.right_hand_title.config(fg=normal_color)
                    self.right_hand_state_label.config(fg=normal_color)
                    self.right_hand_status_help.config(fg=normal_gray)
                else:
                    # Si ON et Pause: fade left text, blink faded
                    self.left_label.config(fg=faded_gray)
                    self.left_bold.config(fg=faded_color)
                    self.to_pause.config(fg=faded_gray)
                    self.right_label.config(fg=normal_gray)
                    self.right_bold.config(fg=normal_color)
                    self.to_play.config(fg=normal_gray)
                    self.pause_title.config(fg=normal_color)
                    # Pause button normal
                    self.pause_btn.config(image=self.icons.get("pause"))
                    self.pause_btn.image = self.icons.get("pause")
                    # Blink faded
                    self.blink_title.config(fg=faded_color)
                    self.blink_help.config(fg=faded_gray)
                    self.blink_btn.config(image=self.icons.get("eye_open_disabled"))
                    self.blink_btn.image = self.icons.get("eye_open_disabled")
                    self.hand_title.config(fg=faded_color)
                    self.hand_state_label.config(fg=faded_color)
                    self.hand_status_help.config(fg=faded_gray)
                    self.right_hand_title.config(fg=faded_color)
                    self.right_hand_state_label.config(fg=faded_color)
                    self.right_hand_status_help.config(fg=faded_gray)

                left_icon_key = "hand_l_disabled"
                if self.state.is_running and not self.state.is_paused and self.state.is_left_hand_detected:
                    if self.state.is_left_thumb_closed:
                        left_icon_key = "hand_l_thumb_closed"
                    elif self.state.is_left_hand_closed:
                        left_icon_key = "hand_l_closed"
                    else:
                        left_icon_key = "hand_l_open"
                self.hand_btn.config(image=self.icons.get(left_icon_key))
                self.hand_btn.image = self.icons.get(left_icon_key)

                right_icon_key = "hand_r_disabled"
                if self.state.is_running and not self.state.is_paused and self.state.is_right_hand_detected:
                    if self.state.is_right_thumb_closed:
                        right_icon_key = "hand_r_thumb_closed"
                    elif self.state.is_right_hand_closed:
                        right_icon_key = "hand_r_closed"
                    else:
                        right_icon_key = "hand_r_open"
                self.right_hand_btn.config(image=self.icons.get(right_icon_key))
                self.right_hand_btn.image = self.icons.get(right_icon_key)

            # Bouton Blink state change
            if self.state.is_blinking:
                # Show eye closed, but fade if paused
                if self.state.is_running and self.state.is_paused:
                    self.blink_btn.config(image=self.icons.get("eye_closed_disabled"))
                    self.blink_btn.image = self.icons.get("eye_closed_disabled")
                else:
                    self.blink_btn.config(image=self.icons.get("eye_closed"))
                    self.blink_btn.image = self.icons.get("eye_closed")
            else:
                # Handled above based on pause state
                pass

            # Update pause title text
            if self.state.is_paused:
                self.pause_title.config(text="Pause")
            else:
                self.pause_title.config(text="Playing")

            # Popups d'actions (pas de popup pour blink)
            if not self._ui_initialized:
                self._ui_initialized = True
            else:
                if self.state.is_running != self._last_running:
                    self._show_action_popup("on" if self.state.is_running else "off")
                elif self.state.is_running and self.state.is_paused != self._last_paused:
                    if self.state.is_paused:
                        self._show_action_popup("pause", persistent=True)
                    else:
                        self._show_action_popup("play")

            self._last_running = self.state.is_running
            self._last_paused = self.state.is_paused

            # Debug visuel des inputs jeu (L/R/U/D)
            active_color = "#27AE60" if self.state.is_running else "#4A5568"
            idle_color = "#4A5568"
            now = time.time()
            for token, label in self.input_light_labels.items():
                is_active = (
                    self.state.is_running
                    and (now - float(self.state.last_input_times.get(token, 0.0)))
                    <= self.state.input_flash_window_seconds
                )
                label.config(bg=active_color if is_active else idle_color)

            if self.state.input_history:
                history_tail = " | ".join(self.state.input_history[-5:])
                self.input_debug_history.config(text=history_tail)
            else:
                self.input_debug_history.config(text="No input sent yet")
        except Exception as e:
            print(f"[GUI] Erreur mise à jour: {e}")


class PauseNotifier:
    """Affiche un popup non-bloquant indiquant l'état pause ou reprise."""

    def __init__(self):
        self.pause_window = None
        self.pause_window_lock = threading.Lock()
        self.popup_icon_size = (128, 128)
        self.popup_icons = self._load_popup_icons()

    def _load_popup_icons(self):
        """Charge les icônes PNG pour le popup."""
        icons = {}
        icon_files = {
            "pause": "Pause.png",
            "play": "Play.png",
        }

        project_root = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(project_root, "icons")

        for key, filename in icon_files.items():
            try:
                filepath = os.path.join(icons_dir, filename)
                if os.path.exists(filepath):
                    img = Image.open(filepath)
                    img = img.resize(self.popup_icon_size, Image.Resampling.LANCZOS)
                    icons[key] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"[Popup] Erreur chargement icone {key}: {e}")

        return icons

    def show(self, paused: bool):
        icon_key = "pause" if paused else "play"
        bg = "#E67E22" if paused else "#27AE60"
        self.show_message(icon_key=icon_key, bg=bg, is_pause=paused)

    def show_message(self, icon_key: str = "play", bg: str = "#2C3E50", is_pause: bool = False):
        threading.Thread(target=self._show, args=(icon_key, bg, is_pause), daemon=True).start()

    def _close_pause_window(self):
        """Ferme complètement la fenêtre de pause."""
        with self.pause_window_lock:
            if self.pause_window is not None:
                try:
                    self.pause_window.destroy()
                except Exception:
                    pass
                self.pause_window = None

    def _show(self, icon_key: str, bg: str, is_pause: bool = False):
        try:
            # Si c'est la reprise, ferme d'abord le pop-up de pause
            if not is_pause:
                self._close_pause_window()

            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.92)

            # Affiche l'icône
            icon = self.popup_icons.get(icon_key)
            if icon:
                label = tk.Label(
                    root, image=icon, bg=bg, padx=20, pady=20
                )
                label.image = icon
                label.pack()
            else:
                label = tk.Label(
                    root, text="", bg=bg, fg="white",
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

            # Si c'est la pause, garde la fenêtre affichée (ne pas la détruire)
            # Si c'est la reprise, détruis-la après 2500ms
            if is_pause:
                with self.pause_window_lock:
                    if self.pause_window is not None:
                        try:
                            self.pause_window.destroy()
                        except Exception:
                            pass
                    self.pause_window = root
                root.mainloop()
            else:
                root.after(2500, root.destroy)
                root.mainloop()
        except Exception:
            pass

    def close(self):
        self._close_pause_window()


class BlinkKeyboardTrigger:
    def __init__(self, config: dict):
        self.enabled = bool(config.get("enabled", True))
        self.window_title = str(config.get("window_title", "Rhythm Doctor"))
        excluded = config.get("exclude_window_substrings", ["accessibility addon"])
        if isinstance(excluded, str):
            excluded = [excluded]
        self.exclude_window_substrings = [str(x).strip().lower() for x in excluded if str(x).strip()]
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
            "esc": 0x1B,
            "escape": 0x1B,
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

        target = self.window_title.strip().lower()
        candidates = []
        for window in windows:
            title = str(getattr(window, "title", "") or "")
            title_l = title.lower()
            if any(excl in title_l for excl in self.exclude_window_substrings):
                continue

            if title_l == target:
                score = 300
            elif title_l.startswith(target):
                score = 200
            else:
                score = 100
            score += min(len(title), 99)
            candidates.append((score, window, title))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, game_window, game_title = candidates[0]
        else:
            # Dernier recours: prend le premier resultat si tous les autres sont exclus.
            game_window = windows[0]
            game_title = str(getattr(game_window, "title", "") or "")

        game_window.activate()

        # Force foreground in case activate() is ignored by Windows focus rules.
        hwnd = getattr(game_window, "_hWnd", None)
        if hwnd:
            self.user32.ShowWindow(hwnd, 9)
            self.user32.SetForegroundWindow(hwnd)

        if self.debug_logs:
            print(f"[Keyboard] Focus cible='{game_title}'")

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
                print(f"[Keyboard] Trigger -> touche envoyee ({sent_method}), active='{active_title}'")
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


class AddonController:
    """Pilote la boucle de detection en arriere-plan et met a jour l'UI."""

    def __init__(self, state: AddonState):
        self.state = state
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._thread_lock = threading.Lock()

    def set_enabled(self, enabled: bool):
        if enabled:
            self.start()
        else:
            self.stop()

    def start(self):
        with self._thread_lock:
            if self._worker_thread and self._worker_thread.is_alive():
                return

            self._stop_event.clear()
            self.state.set_status_message("Demarrage en cours...")
            self.state.set_running(True)
            self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._worker_thread.start()

    def stop(self):
        with self._thread_lock:
            self._stop_event.set()
            worker = self._worker_thread

        if worker and worker.is_alive():
            worker.join(timeout=2.0)

        self.state.set_running(False)
        self.state.set_paused(False)
        self.state.set_blinking(False)
        self.state.set_left_hand_state(False, False)
        self.state.set_right_hand_state(False, False)
        self.state.set_status_message("Addon arrete")

    def _run_loop(self):
        processor = None

        try:
            try:
                import yaml
                from src.Captation.mediapipe_processor import MediaPipeFaceProcessor
                from src.Network.osc_sender import OSCSender
            except ModuleNotFoundError:
                self.state.set_status_message("Erreur: dependances Python manquantes")
                self.state.set_running(False)
                return

            if getattr(sys, "frozen", False):
                project_root = os.path.dirname(sys.executable)
            else:
                project_root = os.path.dirname(os.path.abspath(__file__))

            config_path = os.path.join(project_root, "config", "Network.yaml")
            if not os.path.exists(config_path):
                self.state.set_status_message("Erreur: Network.yaml introuvable")
                self.state.set_running(False)
                return

            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            config["project_root"] = project_root

            self.state.set_status_message("Initialisation camera...")
            processor = MediaPipeFaceProcessor(config)

            sender_ip = config["OSC_output"]["ip"]
            sender_port = config["OSC_output"]["port"]
            sender_address = config["OSC_output"]["base_address"]
            sender = OSCSender(ip=sender_ip, port=sender_port, base_address=sender_address)

            blink_cfg = config.get("blink_detection", {})
            blink_threshold = float(blink_cfg.get("threshold", 0.6))
            blink_off_threshold = float(blink_cfg.get("threshold_off", 0.35))
            blink_trigger_edge = str(blink_cfg.get("trigger_edge", "press")).lower()
            loop_sleep_seconds = float(blink_cfg.get("loop_sleep_seconds", 0.005))
            blink_rearm_threshold = float(
                blink_cfg.get("rearm_threshold", max(blink_off_threshold, blink_threshold - 0.12))
            )
            blink_min_trigger_interval_ms = int(blink_cfg.get("min_trigger_interval_ms", 70))
            keyboard_cfg = config.get("keyboard_trigger", {})
            keyboard_trigger = BlinkKeyboardTrigger(keyboard_cfg)

            hand_trigger_cfg = config.get("hand_trigger", {})
            hand_trigger_enabled = bool(hand_trigger_cfg.get("enabled", True))
            hand_trigger_allow_when_paused = bool(hand_trigger_cfg.get("allow_when_paused", False))

            pause_trigger_cfg = config.get("pause_trigger", {})
            pause_trigger_enabled = bool(pause_trigger_cfg.get("enabled", True))
            pause_force_win32 = bool(pause_trigger_cfg.get("force_win32", True))
            pause_fallback_win32_direct = bool(pause_trigger_cfg.get("fallback_win32_direct", True))

            pause_key_cfg = dict(keyboard_cfg)
            pause_key_cfg["enabled"] = pause_trigger_enabled
            pause_key_cfg["key"] = str(pause_trigger_cfg.get("key", "esc"))
            for field in (
                "window_title",
                "hold_ms",
                "cooldown_ms",
                "focus_window",
                "focus_delay_ms",
                "send_method",
                "allow_method_fallback",
                "debug_logs",
            ):
                if field in pause_trigger_cfg:
                    pause_key_cfg[field] = pause_trigger_cfg[field]
            if pause_force_win32:
                pause_key_cfg["send_method"] = "win32"
                pause_key_cfg["allow_method_fallback"] = False
            pause_key_trigger = BlinkKeyboardTrigger(pause_key_cfg)

            def _send_pause_escape() -> bool:
                """Try configured pause trigger, then direct Win32 ESC fallback."""
                if pause_key_trigger.on_blink():
                    return True

                if not pause_fallback_win32_direct:
                    return False

                try:
                    user32 = ctypes.windll.user32
                    vk_escape = 0x1B
                    key_up_flag = 0x0002
                    hold_seconds = max(int(pause_key_cfg.get("hold_ms", 45)), 1) / 1000.0
                    user32.keybd_event(vk_escape, 0, 0, 0)
                    time.sleep(hold_seconds)
                    user32.keybd_event(vk_escape, 0, key_up_flag, 0)
                    print("[Pause] ESC envoye via fallback win32 direct")
                    return True
                except Exception as exc:
                    print(f"[Pause] Echec envoi ESC fallback: {exc}")
                    return False

            def _build_hand_trigger(action_key: str) -> BlinkKeyboardTrigger:
                cfg = dict(keyboard_cfg)
                cfg["enabled"] = hand_trigger_enabled
                cfg["key"] = action_key

                for field in (
                    "window_title",
                    "hold_ms",
                    "cooldown_ms",
                    "focus_window",
                    "focus_delay_ms",
                    "send_method",
                    "allow_method_fallback",
                    "debug_logs",
                ):
                    if field in hand_trigger_cfg:
                        cfg[field] = hand_trigger_cfg[field]
                return BlinkKeyboardTrigger(cfg)

            left_hand_trigger = _build_hand_trigger(str(hand_trigger_cfg.get("left_hand_key", "left")))
            right_hand_trigger = _build_hand_trigger(str(hand_trigger_cfg.get("right_hand_key", "right")))
            left_thumb_trigger = _build_hand_trigger(str(hand_trigger_cfg.get("left_thumb_key", "down")))
            right_thumb_trigger = _build_hand_trigger(str(hand_trigger_cfg.get("right_thumb_key", "up")))

            gaze_cfg = config.get("gaze_pause", {})
            gaze_enabled = bool(gaze_cfg.get("enabled", True))
            gaze_dir_pause = str(gaze_cfg.get("direction_pause", "right")).lower()
            gaze_dir_resume = str(gaze_cfg.get("direction_resume", "left")).lower()
            gaze_yaw_thr = float(gaze_cfg.get("yaw_threshold", 20.0))
            gaze_pitch_thr = float(gaze_cfg.get("pitch_threshold", 0.0))
            gaze_cooldown = float(gaze_cfg.get("cooldown_seconds", 1.5))
            gaze_debug = bool(gaze_cfg.get("debug_logs", False))

            was_blinking = False
            blink_press_armed = True
            last_blink_trigger_ms = 0.0
            was_left_hand_closed = False
            was_right_hand_closed = False
            was_left_thumb_closed = False
            was_right_thumb_closed = False
            paused = False
            was_in_gaze_pause_pos = False
            was_in_gaze_resume_pos = False
            gaze_last_trigger = 0.0
            gaze_log_count = 0

            self.state.set_status_message("Actif - blink + regard + mains gauche/droite")

            while not self._stop_event.is_set():
                data_dict = processor.get_processed_data()
                if not data_dict:
                    time.sleep(max(loop_sleep_seconds, 0.001))
                    continue

                blink_value = float(data_dict.get("blink", 0.0))
                gaze_yaw = float(data_dict.get("gaze_yaw", 0.0))
                gaze_pitch = float(data_dict.get("gaze_pitch", 0.0))
                left_hand_detected = bool(data_dict.get("left_hand_detected", 0.0) >= 0.5)
                left_hand_closed = bool(data_dict.get("left_hand_closed", 0.0) >= 0.5)
                left_thumb_closed = bool(data_dict.get("left_thumb_closed", 0.0) >= 0.5)
                right_hand_detected = bool(data_dict.get("right_hand_detected", 0.0) >= 0.5)
                right_hand_closed = bool(data_dict.get("right_hand_closed", 0.0) >= 0.5)
                right_thumb_closed = bool(data_dict.get("right_thumb_closed", 0.0) >= 0.5)

                pause_gesture_pending = False
                if gaze_enabled and not paused:
                    pause_gesture_pending = _check_gaze(
                        gaze_dir_pause,
                        gaze_yaw,
                        gaze_pitch,
                        gaze_yaw_thr,
                        gaze_pitch_thr,
                    )

                self.state.set_left_hand_state(left_hand_detected, left_hand_closed, left_thumb_closed)
                self.state.set_right_hand_state(right_hand_detected, right_hand_closed, right_thumb_closed)

                can_trigger_hand_inputs = (hand_trigger_allow_when_paused or (not paused)) and (not pause_gesture_pending)
                if can_trigger_hand_inputs:
                    if left_hand_closed and not was_left_hand_closed:
                        if left_hand_trigger.on_blink():
                            self.state.register_game_input("L")
                    if right_hand_closed and not was_right_hand_closed:
                        if right_hand_trigger.on_blink():
                            self.state.register_game_input("R")
                    if left_thumb_closed and not was_left_thumb_closed:
                        if left_thumb_trigger.on_blink():
                            self.state.register_game_input("D")
                    if right_thumb_closed and not was_right_thumb_closed:
                        if right_thumb_trigger.on_blink():
                            self.state.register_game_input("U")

                was_left_hand_closed = left_hand_closed
                was_right_hand_closed = right_hand_closed
                was_left_thumb_closed = left_thumb_closed
                was_right_thumb_closed = right_thumb_closed

                if blink_value >= blink_threshold:
                    is_blinking = True
                elif blink_value < blink_off_threshold:
                    is_blinking = False
                else:
                    is_blinking = was_blinking

                sender.send_dict(data_dict)

                blink_rising_edge = is_blinking and not was_blinking
                blink_falling_edge = (not is_blinking) and was_blinking
                now_ms = time.time() * 1000.0

                should_trigger_blink = False
                if blink_trigger_edge in ("press", "rising", "close", "closed"):
                    if blink_value <= blink_rearm_threshold:
                        blink_press_armed = True
                    if blink_value >= blink_threshold and blink_press_armed:
                        should_trigger_blink = True
                        blink_press_armed = False
                elif blink_trigger_edge in ("release", "falling", "open"):
                    should_trigger_blink = blink_falling_edge
                else:
                    # Fallback sécurisé: comportement instantané.
                    if blink_value <= blink_rearm_threshold:
                        blink_press_armed = True
                    if blink_value >= blink_threshold and blink_press_armed:
                        should_trigger_blink = True
                        blink_press_armed = False

                if now_ms - last_blink_trigger_ms < blink_min_trigger_interval_ms:
                    should_trigger_blink = False

                if should_trigger_blink and not paused:
                    if keyboard_trigger.on_blink():
                        last_blink_trigger_ms = now_ms
                        self.state.set_blinking(True)
                was_blinking = is_blinking

                if gaze_enabled:
                    now = time.time()
                    in_pause_pos = _check_gaze(
                        gaze_dir_pause,
                        gaze_yaw,
                        gaze_pitch,
                        gaze_yaw_thr,
                        gaze_pitch_thr,
                    )
                    in_resume_pos = _check_gaze(
                        gaze_dir_resume,
                        gaze_yaw,
                        gaze_pitch,
                        gaze_yaw_thr,
                        gaze_pitch_thr,
                    )

                    if in_pause_pos and not was_in_gaze_pause_pos:
                        if not paused and now - gaze_last_trigger >= gaze_cooldown:
                            paused = True
                            self.state.set_paused(True)
                            self.state.set_status_message("En pause - regard vers la reprise")
                            _send_pause_escape()
                            gaze_last_trigger = now

                    if in_resume_pos and not was_in_gaze_resume_pos:
                        if paused and now - gaze_last_trigger >= gaze_cooldown:
                            paused = False
                            self.state.set_paused(False)
                            self.state.set_status_message("Actif - clignez pour declencher")
                            gaze_last_trigger = now

                    was_in_gaze_pause_pos = in_pause_pos
                    was_in_gaze_resume_pos = in_resume_pos

                if gaze_debug:
                    gaze_log_count += 1
                    if gaze_log_count % 30 == 0:
                        print(f"[Gaze] yaw={gaze_yaw:+.1f} pitch={gaze_pitch:+.1f} paused={paused}")

                time.sleep(max(loop_sleep_seconds, 0.001))

        except Exception as exc:
            self.state.set_status_message(f"Erreur: {exc}")
        finally:
            if processor is not None:
                try:
                    processor.stop()
                except Exception:
                    pass

            self.state.set_running(False)
            self.state.set_paused(False)
            self.state.set_blinking(False)
            self.state.set_left_hand_state(False, False)
            self.state.set_right_hand_state(False, False)

            if not self._stop_event.is_set() and not self.state.status_message.startswith("Erreur"):
                self.state.set_status_message("Addon arrete")


def main():
    root = tk.Tk()
    state = AddonState()
    controller = AddonController(state)

    gui = AddonGUI(root=root, state=state, on_toggle_callback=controller.set_enabled)
    gui._update_ui()

    def _on_close():
        controller.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()

if __name__ == "__main__":
    main()