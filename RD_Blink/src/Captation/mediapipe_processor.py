import math
from pathlib import Path
from urllib.request import urlretrieve

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class MediaPipeFaceProcessor:
    def __init__(self, config: dict):
        mp_cfg = config.get("mediapipe_info", {})
        project_root = Path(config.get("project_root", Path.cwd()))

        camera_index = int(mp_cfg.get("camera_index", 0))
        camera_fallback_indexes = mp_cfg.get("camera_fallback_indexes", [1, 2, 3])
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
        candidate_indexes = [camera_index] + [int(i) for i in camera_fallback_indexes if int(i) != camera_index]
        backend_candidates = [cv2.CAP_DSHOW, cv2.CAP_MSMF, None]

        for index in candidate_indexes:
            for backend in backend_candidates:
                cap = cv2.VideoCapture(index) if backend is None else cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    self.capture = cap
                    backend_name = "AUTO" if backend is None else str(backend)
                    print(f"[MediaPipe] Caméra utilisée: index={index}, backend={backend_name}")
                    break
                cap.release()

            if self.capture is not None:
                break

        if self.capture is None:
            raise RuntimeError(
                f"[MediaPipe] Impossible d'ouvrir une caméra (indexes testés: {candidate_indexes})"
            )

        if frame_width:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(frame_width))
        if frame_height:
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(frame_height))

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

        return {"blink": blink_value, "gaze_yaw": gaze_yaw, "gaze_pitch": gaze_pitch}

    def stop(self):
        self.capture.release()
        self.detector.close()
