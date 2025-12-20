import cv2
import numpy as np


def validate_avatar_image(image_file):
    """
    Simple & stable human face detection using OpenCV Haar Cascade.
    Returns: (is_valid, message, detected_object, confidence)
    """

    try:
        # Read image from UploadedFile
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return False, "Image invalide.", "unknown", 0.0

        # Load Haar Cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        faces = face_cascade.detectMultiScale(
            img,
            scaleFactor=1.3,
            minNeighbors=5,
            minSize=(60, 60)
        )

        if len(faces) > 0:
            confidence = min(0.95, 0.6 + 0.1 * len(faces))
            return True, "Visage humain détecté.", "human", confidence

        return False, "Aucun visage humain détecté.", "non-human", 0.0

    except Exception as e:
        return False, f"Erreur validation image: {e}", "error", 0.0
