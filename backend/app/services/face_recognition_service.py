"""
Face Recognition Service — InsightFace (ArcFace / buffalo_l)
Handles: face detection, embedding extraction, ANN search via pgvector
"""
import os
import io
import base64
import logging
from typing import Optional, Tuple, List
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

# Lazy-loaded model (avoids import cost at startup in tests)
_face_analyzer = None


def _get_analyzer():
    global _face_analyzer
    if _face_analyzer is None:
        try:
            import insightface
            from insightface.app import FaceAnalysis
            model_dir = os.environ.get("INSIGHTFACE_HOME", os.path.join(os.path.dirname(__file__), "models"))
            _face_analyzer = FaceAnalysis(
                name="buffalo_l",
                root=model_dir,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            _face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✅ InsightFace buffalo_l loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load InsightFace: {e}")
            _face_analyzer = None
    return _face_analyzer


def decode_base64_image(image_b64: str) -> np.ndarray:
    """Decode base64 image (from browser webcam) to numpy BGR array."""
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(image_b64)
    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def extract_embedding(image_b64: str) -> Tuple[Optional[np.ndarray], float]:
    """
    Extract 512-dim ArcFace embedding from a base64 image.
    Returns: (embedding_array, quality_score) or (None, 0.0) if no face.
    """
    analyzer = _get_analyzer()
    if analyzer is None:
        raise RuntimeError("Face recognition model not available")

    img = decode_base64_image(image_b64)
    faces = analyzer.get(img)

    if not faces:
        return None, 0.0

    # Pick best face (largest bounding box = closest to camera)
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    embedding = face.normed_embedding  # Already L2-normalized 512-dim vector
    quality_score = float(face.det_score)  # Detection confidence 0.0-1.0

    return embedding, quality_score


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalized vectors."""
    return float(np.dot(a, b))


def verify_face(
    embedding: np.ndarray,
    known_embedding: np.ndarray,
    threshold: float = 0.85,
) -> Tuple[bool, float]:
    """Check if two embeddings belong to the same person."""
    sim = cosine_similarity(embedding, known_embedding)
    return sim >= threshold, sim


# ============================================================
# pgvector ANN Search query (raw SQL helper)
# ============================================================

FACE_SEARCH_SQL = """
SELECT
    fe.student_id,
    1 - (fe.embedding <=> :query_vec::vector) AS similarity
FROM face_embeddings fe
ORDER BY fe.embedding <=> :query_vec::vector
LIMIT 1;
"""
# Usage: execute with {"query_vec": str(embedding.tolist())}
# Returns the closest student_id and similarity score.
# Threshold check: if similarity < settings.FACE_SIMILARITY_THRESHOLD → reject
