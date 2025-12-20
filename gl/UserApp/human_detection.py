import cv2
import mediapipe as mp

mp_face_detection = mp.solutions.face_detection

def is_human(image_path: str) -> bool:
    img = cv2.imread(image_path)

    if img is None:
        return False

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    with mp_face_detection.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.5
    ) as detector:

        results = detector.process(img_rgb)

        return results.detections is not None
