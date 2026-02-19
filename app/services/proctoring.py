"""Proctoring analysis and exam management."""
import cv2
import numpy as np
import face_recognition
from app import celery
from app.models import ProctoringLog, ExamSession, db
import logging

logger = logging.getLogger(__name__)


@celery.task
def analyze_proctoring_frame(exam_session_id: int, image_data: bytes, event_type: str = 'frame'):
    """Background task to analyze a frame for faces."""
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    face_locations = face_recognition.face_locations(img)
    num_faces = len(face_locations)

    if num_faces == 0:
        log = ProctoringLog(
            exam_id=exam_session_id,
            user_id=None,
            event_type='no_face',
            metadata={'num_faces': num_faces}
        )
        db.session.add(log)
        db.session.commit()
    elif num_faces > 1:
        log = ProctoringLog(
            exam_id=exam_session_id,
            user_id=None,
            event_type='multiple_faces',
            metadata={'num_faces': num_faces}
        )
        db.session.add(log)
        db.session.commit()
