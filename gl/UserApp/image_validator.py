"""
Service de validation d'image pour vérifier si une image contient un être humain.
Utilise MediaPipe Face Detection.
"""

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Initialisation MediaPipe
try:
    mp_face_detection = mp.solutions.face_detection
    MEDIAPIPE_AVAILABLE = True
except Exception as e:
    MEDIAPIPE_AVAILABLE = False
    logger.error(f"MediaPipe non disponible: {e}")


def validate_avatar_image(image_file, min_confidence=0.6):
    """
    Vérifie si une image contient au moins un visage humain valide.

    Retourne :
    (is_valid, message, detected_object, confidence)
    """

    if not MEDIAPIPE_AVAILABLE:
        return True, "Validation ignorée (MediaPipe indisponible).", "unknown", 0.0

    try:
        # 🔁 Revenir au début du fichier
        try:
            image_file.seek(0)
        except Exception:
            pass

        # Charger l'image
        img_pil = Image.open(image_file).convert("RGB")
        img_rgb = np.array(img_pil)

        with mp_face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=min_confidence
        ) as detector:

            results = detector.process(img_rgb)

            # ❌ Aucun visage détecté
            if not results.detections:
                return (
                    False,
                    "Aucun visage humain détecté sur cette image.",
                    "no_face",
                    0.0
                )

            # ✅ Vérifier la confiance
            for detection in results.detections:
                score = detection.score[0]
                if score >= min_confidence:
                    return (
                        True,
                        "Visage humain détecté avec succès.",
                        "human_face",
                        score
                    )

            return (
                False,
                "Visage détecté mais confiance insuffisante.",
                "low_confidence_face",
                max(d.score[0] for d in results.detections)
            )

    except Exception as e:
        logger.error(f"Erreur validation image: {e}", exc_info=True)
        return False, "Erreur lors de l'analyse de l'image.", "error", 0.0
