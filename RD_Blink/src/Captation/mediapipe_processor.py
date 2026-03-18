import math
import time
from pathlib import Path
from urllib.request import urlretrieve

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class MediaPipeFaceProcessor:
    def __init__(self, config: dict):
        mp_cfg = config.get("mediapipe_info", {})
        left_hand_cfg = dict(config.get("left_hand_detection", {}))
        right_hand_cfg = dict(left_hand_cfg)
        right_hand_cfg.update(config.get("right_hand_detection", {}))
        project_root = Path(config.get("project_root", Path.cwd()))

        camera_index = int(mp_cfg.get("camera_index", 0))
        camera_fallback_indexes = mp_cfg.get("camera_fallback_indexes", [1, 2, 3])
        camera_auto_scan_enabled = bool(mp_cfg.get("camera_auto_scan_enabled", True))
        camera_auto_scan_max_index = int(mp_cfg.get("camera_auto_scan_max_index", 8))
        camera_open_retries = int(mp_cfg.get("camera_open_retries", 3))
        camera_retry_delay_seconds = float(mp_cfg.get("camera_retry_delay_seconds", 0.6))
        camera_warmup_frames = int(mp_cfg.get("camera_warmup_frames", 3))
        camera_prefer_mjpg = bool(mp_cfg.get("camera_prefer_mjpg", True))
        backend_names_cfg = mp_cfg.get("camera_backends", ["dshow", "msmf", "any", "auto"])
        frame_width = mp_cfg.get("frame_width")
        frame_height = mp_cfg.get("frame_height")
        blink_mode = str(mp_cfg.get("blink_mode", "max")).lower()
        model_path = Path(mp_cfg.get("model_path", "config/face_landmarker.task"))
        model_url = mp_cfg.get(
            "model_url",
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
        )
        auto_download_model = bool(mp_cfg.get("auto_download_model", True))

        if not model_path.is_absolute():
            model_path = project_root / model_path

        if not model_path.exists():
            if auto_download_model:
                model_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"[MediaPipe] Téléchargement du modèle vers: {model_path}")
                urlretrieve(model_url, model_path)
            else:
                raise FileNotFoundError(
                    f"[MediaPipe] Modèle introuvable: {model_path}. "
                    "Ajoutez le fichier .task dans le dossier config/ ou activez auto_download_model."
                )

        self.capture = None

        # Build a robust candidate list: configured index first, then explicit fallbacks,
        # then auto-scan common camera indexes when enabled.
        candidate_indexes = []
        for idx in [camera_index] + [int(i) for i in camera_fallback_indexes]:
            if idx not in candidate_indexes:
                candidate_indexes.append(idx)

        if camera_auto_scan_enabled:
            for idx in range(max(0, camera_auto_scan_max_index) + 1):
                if idx not in candidate_indexes:
                    candidate_indexes.append(idx)

        backend_map = {
            "dshow": cv2.CAP_DSHOW,
            "msmf": cv2.CAP_MSMF,
            "any": cv2.CAP_ANY,
            "auto": None,
        }
        backend_candidates = []
        backend_name_pairs = []
        for name in backend_names_cfg:
            key = str(name).strip().lower()
            if key not in backend_map:
                continue
            backend_value = backend_map[key]
            if backend_value not in backend_candidates:
                backend_candidates.append(backend_value)
                backend_name_pairs.append((key.upper(), backend_value))

        if not backend_name_pairs:
            backend_name_pairs = [("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF), ("ANY", cv2.CAP_ANY), ("AUTO", None)]

        def _try_open_camera(index: int, backend_value):
            cap = cv2.VideoCapture(index) if backend_value is None else cv2.VideoCapture(index, backend_value)
            if not cap.isOpened():
                cap.release()
                return None

            if frame_width:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(frame_width))
            if frame_height:
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(frame_height))

            if camera_prefer_mjpg:
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                except Exception:
                    pass

            # Warmup reads improve compatibility on some drivers that need initial frames.
            warmup_reads = max(1, camera_warmup_frames)
            frame_ok = False
            for _ in range(warmup_reads):
                ok, _ = cap.read()
                if ok:
                    frame_ok = True
                    break
                time.sleep(0.03)

            if not frame_ok:
                cap.release()
                return None

            return cap

        for attempt in range(max(1, camera_open_retries)):
            for index in candidate_indexes:
                for backend_name, backend_value in backend_name_pairs:
                    cap = _try_open_camera(index, backend_value)
                    if cap is None:
                        continue

                    self.capture = cap
                    print(
                        "[MediaPipe] Camera ouverte: "
                        f"index={index}, backend={backend_name}, attempt={attempt + 1}"
                    )
                    break

                if self.capture is not None:
                    break

            if self.capture is not None:
                break

            if attempt + 1 < max(1, camera_open_retries):
                print(
                    "[MediaPipe] Echec ouverture camera, nouvelle tentative dans "
                    f"{camera_retry_delay_seconds:.1f}s (tentative {attempt + 2}/{max(1, camera_open_retries)})"
                )
                time.sleep(max(0.05, camera_retry_delay_seconds))

        if self.capture is None:
            raise RuntimeError(
                "[MediaPipe] Impossible d'ouvrir une camera. "
                f"Indexes testes: {candidate_indexes}. "
                "Verifiez permissions Windows camera, fermeture des applis qui utilisent deja la webcam, "
                "et testez un autre index dans Network.yaml."
            )

        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)
        self.blink_mode = blink_mode
        self.left_hand_enabled = bool(left_hand_cfg.get("enabled", True))
        self.right_hand_enabled = bool(right_hand_cfg.get("enabled", True))
        self.left_hand_finger_closed_margin = float(left_hand_cfg.get("finger_closed_margin", 0.015))
        self.right_hand_finger_closed_margin = float(right_hand_cfg.get("finger_closed_margin", 0.015))
        self.left_hand_min_closed_fingers = int(left_hand_cfg.get("min_closed_fingers", 4))
        self.right_hand_min_closed_fingers = int(right_hand_cfg.get("min_closed_fingers", 4))
        self.left_thumb_closed_ratio = float(left_hand_cfg.get("thumb_closed_ratio", 0.75))
        self.right_thumb_closed_ratio = float(right_hand_cfg.get("thumb_closed_ratio", 0.75))
        self.hand_invert_handedness = bool(left_hand_cfg.get("invert_handedness", False))
        self.hand_detector = None

        if self.left_hand_enabled or self.right_hand_enabled:
            hand_model_path = Path(left_hand_cfg.get("model_path", "config/hand_landmarker.task"))
            hand_model_url = left_hand_cfg.get(
                "model_url",
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
            )
            hand_auto_download_model = bool(left_hand_cfg.get("auto_download_model", True))

            if not hand_model_path.is_absolute():
                hand_model_path = project_root / hand_model_path

            if not hand_model_path.exists():
                if hand_auto_download_model:
                    hand_model_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"[MediaPipe] Telechargement du modele main vers: {hand_model_path}")
                    urlretrieve(hand_model_url, hand_model_path)
                else:
                    raise FileNotFoundError(
                        f"[MediaPipe] Modele main introuvable: {hand_model_path}. "
                        "Ajoutez le fichier .task ou activez auto_download_model."
                    )

            hand_options = vision.HandLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(hand_model_path)),
                running_mode=vision.RunningMode.IMAGE,
                num_hands=2,
                min_hand_detection_confidence=float(left_hand_cfg.get("min_detection_confidence", 0.6)),
                min_tracking_confidence=float(left_hand_cfg.get("min_tracking_confidence", 0.5)),
                min_hand_presence_confidence=float(left_hand_cfg.get("min_presence_confidence", 0.5)),
            )
            self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)

    def _is_finger_closed(self, landmarks, tip_idx: int, pip_idx: int, margin: float) -> bool:
        """A finger is considered closed when its tip is clearly below its PIP joint."""
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        return tip.y > (pip.y + margin)

    def _is_hand_closed(self, landmarks, margin: float, min_closed_fingers: int) -> bool:
        # index, middle, ring, pinky
        closed_count = 0
        finger_pairs = ((8, 6), (12, 10), (16, 14), (20, 18))
        for tip_idx, pip_idx in finger_pairs:
            if self._is_finger_closed(landmarks, tip_idx, pip_idx, margin):
                closed_count += 1
        return closed_count >= min_closed_fingers

    def _is_thumb_closed(self, landmarks, closed_ratio: float) -> bool:
        """Thumb is closed when tip is close enough to palm center, normalized by palm width."""
        thumb_tip = landmarks[4]
        wrist = landmarks[0]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        palm_center_x = (wrist.x + index_mcp.x + pinky_mcp.x) / 3.0
        palm_center_y = (wrist.y + index_mcp.y + pinky_mcp.y) / 3.0

        dist_tip_to_palm = math.hypot(thumb_tip.x - palm_center_x, thumb_tip.y - palm_center_y)
        palm_width = math.hypot(index_mcp.x - pinky_mcp.x, index_mcp.y - pinky_mcp.y)

        if palm_width <= 1e-6:
            return False

        return dist_tip_to_palm <= (palm_width * closed_ratio)

    def get_processed_data(self) -> dict:
        ok, frame = self.capture.read()
        if not ok:
            return {}

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.detector.detect(mp_image)

        if not result.face_blendshapes:
            return {}

        blendshapes = result.face_blendshapes[0]
        scores = {item.category_name: float(item.score) for item in blendshapes}
        left = scores.get("eyeBlinkLeft", 0.0)
        right = scores.get("eyeBlinkRight", 0.0)

        if self.blink_mode == "avg":
            blink_value = (left + right) / 2.0
        else:
            blink_value = max(left, right)

        # Direction du regard via matrice de transformation faciale
        # Colonne 2 de la matrice de rotation = vecteur "vers l'avant" de la face en espace caméra
        gaze_yaw   = 0.0
        gaze_pitch = 0.0
        if result.facial_transformation_matrixes:
            M = result.facial_transformation_matrixes[0]
            fwd_x = float(M[0][2])
            fwd_y = float(M[1][2])
            fwd_z = float(M[2][2])
            gaze_yaw   = math.degrees(math.atan2(fwd_x, fwd_z))
            gaze_pitch = math.degrees(math.atan2(fwd_y, math.sqrt(fwd_x ** 2 + fwd_z ** 2)))

        left_hand_detected = False
        left_hand_closed = False
        left_thumb_closed = False
        right_hand_detected = False
        right_hand_closed = False
        right_thumb_closed = False

        if (self.left_hand_enabled or self.right_hand_enabled) and self.hand_detector is not None:
            hand_result = self.hand_detector.detect(mp_image)
            if hand_result.hand_landmarks and hand_result.handedness:
                for hand_landmarks, hand_handedness in zip(
                    hand_result.hand_landmarks,
                    hand_result.handedness,
                ):
                    hand_label = str(hand_handedness[0].category_name).lower()
                    if self.hand_invert_handedness:
                        hand_label = "left" if hand_label == "right" else "right"

                    if hand_label == "left":
                        left_hand_detected = True
                        left_hand_closed = self._is_hand_closed(
                            hand_landmarks,
                            self.left_hand_finger_closed_margin,
                            self.left_hand_min_closed_fingers,
                        )
                        left_thumb_closed = self._is_thumb_closed(
                            hand_landmarks,
                            self.left_thumb_closed_ratio,
                        )
                    elif hand_label == "right":
                        right_hand_detected = True
                        right_hand_closed = self._is_hand_closed(
                            hand_landmarks,
                            self.right_hand_finger_closed_margin,
                            self.right_hand_min_closed_fingers,
                        )
                        right_thumb_closed = self._is_thumb_closed(
                            hand_landmarks,
                            self.right_thumb_closed_ratio,
                        )

                    if (not self.left_hand_enabled or left_hand_detected) and (
                        not self.right_hand_enabled or right_hand_detected
                    ):
                        break

        if not self.left_hand_enabled:
            left_hand_detected = False
            left_hand_closed = False
            left_thumb_closed = False

        if not self.right_hand_enabled:
            right_hand_detected = False
            right_hand_closed = False
            right_thumb_closed = False

        return {
            "blink": blink_value,
            "gaze_yaw": gaze_yaw,
            "gaze_pitch": gaze_pitch,
            "left_hand_detected": 1.0 if left_hand_detected else 0.0,
            "left_hand_closed": 1.0 if left_hand_closed else 0.0,
            "left_thumb_closed": 1.0 if left_thumb_closed else 0.0,
            "right_hand_detected": 1.0 if right_hand_detected else 0.0,
            "right_hand_closed": 1.0 if right_hand_closed else 0.0,
            "right_thumb_closed": 1.0 if right_thumb_closed else 0.0,
        }

    def stop(self):
        self.capture.release()
        if self.hand_detector is not None:
            self.hand_detector.close()
        self.detector.close()
