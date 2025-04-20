import cv2
import numpy as np

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

if not face_cascade.load(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"):
    raise IOError("Error loading Haar Cascade XML file. Check OpenCV installation.")

def detect_faces(image: np.ndarray, scale_factor: float = 1.05, min_neighbors: int = 5, min_size: tuple = (30, 30), return_bounding_boxes: bool = True):
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Invalid image input. Ensure it's a non-empty NumPy array.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=scale_factor, minNeighbors=min_neighbors, minSize=min_size)

    if return_bounding_boxes:
        return faces.tolist() if len(faces) > 0 else []
    else:
        return len(faces) > 0
