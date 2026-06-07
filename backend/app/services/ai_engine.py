"""
Attender V3 — AI Attendance Engine
===================================
Professor-driven bulk classroom recognition.

Pipeline:
  1. Decode base64 images → numpy arrays
  2. SCRFD face detection (InsightFace)
  3. ArcFace embedding extraction per face
  4. Cross-image deduplication (cosine similarity grouping)
  5. pgvector ANN search against enrolled students
  6. Second-pass re-verification for low-confidence (0.75–0.90) matches
  7. Confidence classification → draft generation

Output: AttendanceDraftResult
"""

import io
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

# ── Confidence thresholds ──────────────────────────────────────────────────────
THRESHOLD_AUTO     = 0.90   # → auto_present
THRESHOLD_REVIEW   = 0.75   # below → unknown / not marked
# Between THRESHOLD_REVIEW and THRESHOLD_AUTO → second-pass re-verify

# ── Model singleton ────────────────────────────────────────────────────────────
_analyzer = None

def _get_analyzer():
    global _analyzer
    if _analyzer is not None:
        return _analyzer
    try:
        import insightface
        from insightface.app import FaceAnalysis
        import os
        model_root = os.environ.get("INSIGHTFACE_HOME", "./app/ml/models")
        _analyzer = FaceAnalysis(
            name="buffalo_l",
            root=model_root,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        _analyzer.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("✅ InsightFace buffalo_l loaded (SCRFD + ArcFace)")
    except Exception as e:
        logger.error(f"❌ InsightFace load failed: {e}")
        _analyzer = None
    return _analyzer


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class DetectedFace:
    """A single detected face from one image."""
    embedding: np.ndarray          # 512-dim ArcFace embedding (normalized)
    quality:   float               # detection confidence score
    bbox:      list                # [x1, y1, x2, y2]
    face_crop_b64: str             # base64 JPEG crop for professor review UI
    source_image_idx: int          # which of the 2-5 images this came from


@dataclass
class DraftEntry:
    """One entry in the AI-generated attendance draft."""
    student_id:    Optional[str]   # None = unknown face
    confidence:    float
    status:        str             # 'auto_present' | 'needs_review' | 'unknown'
    face_crop_b64: str
    source_image_idx: int
    bbox:          list
    candidates:    list[dict] = field(default_factory=list)


@dataclass
class AttendanceDraftResult:
    """Full output of the AI engine for one session."""
    auto_present:  list[dict]   # [{student_id, name, roll, confidence}]
    needs_review:  list[dict]   # [{student_id, name, roll, confidence, face_crop, candidates}]
    unknown_faces: list[dict]   # [{face_crop, bbox, candidates}]
    not_detected:  list[dict]   # enrolled students not seen in any image


# ── Helpers ────────────────────────────────────────────────────────────────────

def _decode_image(b64_string: str) -> np.ndarray:
    """Decode base64 image string → BGR numpy array."""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_string)
    pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def _crop_face_b64(img: np.ndarray, bbox: list, padding: float = 0.20) -> str:
    """Crop and return a face region as base64 JPEG with padding."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    pw = int((x2 - x1) * padding)
    ph = int((y2 - y1) * padding)
    x1 = max(0, x1 - pw)
    y1 = max(0, y1 - ph)
    x2 = min(w, x2 + pw)
    y2 = min(h, y2 + ph)
    crop = img[y1:y2, x1:x2]
    _, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def _tighter_crop_and_reembed(img: np.ndarray, bbox: list) -> Optional[np.ndarray]:
    """
    Second-pass re-verification:
    Crop face with zero padding, upscale to 112x112, re-run ArcFace.
    Used for 0.75–0.90 confidence band before asking professor to review.
    """
    analyzer = _get_analyzer()
    if analyzer is None:
        return None
    x1, y1, x2, y2 = [int(v) for v in bbox]
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    crop_resized = cv2.resize(crop, (160, 160))
    faces = analyzer.get(crop_resized)
    if not faces:
        return None
    return faces[0].normed_embedding


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a / np.linalg.norm(a), b / np.linalg.norm(b)))


def _deduplicate_faces(faces: list[DetectedFace]) -> list[DetectedFace]:
    """
    Group faces across multiple images by cosine similarity.
    If two faces from different images match (sim > 0.85), keep the higher-quality one.
    Returns deduplicated list.
    """
    if not faces:
        return []

    groups: list[list[DetectedFace]] = []
    used = [False] * len(faces)

    for i, face_i in enumerate(faces):
        if used[i]:
            continue
        group = [face_i]
        used[i] = True
        for j, face_j in enumerate(faces):
            if used[j] or i == j:
                continue
            sim = _cosine_sim(face_i.embedding, face_j.embedding)
            if sim > 0.85:
                group.append(face_j)
                used[j] = True
        groups.append(group)

    # Keep best quality face per group
    return [max(g, key=lambda f: f.quality) for g in groups]


# ── pgvector Search SQL ────────────────────────────────────────────────────────

ANN_SEARCH_SQL = """
SELECT
    fe.student_id::text AS student_id,
    u.full_name AS name,
    s.student_id AS roll,
    fe.face_photo_b64 AS face_photo_b64,
    1 - (fe.embedding <=> :qvec::vector) AS similarity
FROM face_embeddings fe
JOIN students s ON s.user_id = fe.student_id
JOIN users u ON u.id = fe.student_id
WHERE s.is_face_approved = TRUE
ORDER BY fe.embedding <=> :qvec::vector
LIMIT 3;
"""

# ── Main Engine ────────────────────────────────────────────────────────────────

async def run_ai_engine(
    session_id: str,
    image_b64_list: list[str],
    enrolled_students: list[dict],   # [{student_id, name, roll}]
    db,                              # AsyncSession
) -> AttendanceDraftResult:
    """
    Full AI attendance pipeline.

    Args:
        session_id: UUID of the active session
        image_b64_list: 2-5 base64 classroom images
        enrolled_students: all students enrolled in the subject
        db: SQLAlchemy async session

    Returns:
        AttendanceDraftResult with classified attendance
    """
    from sqlalchemy import text

    analyzer = _get_analyzer()
    if analyzer is None:
        raise RuntimeError("InsightFace model unavailable. Check model installation.")

    # ── Step 1: Detect faces in all images ────────────────────────────────────
    all_faces: list[DetectedFace] = []
    decoded_images: list[np.ndarray] = []

    for idx, b64 in enumerate(image_b64_list):
        try:
            img = _decode_image(b64)
            decoded_images.append(img)
        except Exception as e:
            logger.warning(f"Failed to decode image {idx}: {e}")
            continue

        faces_detected = analyzer.get(img)
        for face in faces_detected:
            crop_b64 = _crop_face_b64(img, face.bbox.tolist())
            all_faces.append(DetectedFace(
                embedding=face.normed_embedding,
                quality=float(face.det_score),
                bbox=face.bbox.tolist(),
                face_crop_b64=crop_b64,
                source_image_idx=idx,
            ))

    logger.info(f"Detected {len(all_faces)} faces across {len(image_b64_list)} images")

    # ── Step 2: Cross-image deduplication ─────────────────────────────────────
    unique_faces = _deduplicate_faces(all_faces)
    logger.info(f"After deduplication: {len(unique_faces)} unique faces")

    # ── Step 3: ANN search against enrolled students ───────────────────────────
    matched_student_ids: set[str] = set()
    draft_entries: list[DraftEntry] = []

    for face in unique_faces:
        query_vec = str(face.embedding.tolist())
        rows = []
        try:
            result = await db.execute(
                text(ANN_SEARCH_SQL),
                {"qvec": query_vec},
            )
            rows = result.fetchall()
        except Exception as e:
            logger.error(f"pgvector search error: {e}")

        # Map to candidates
        candidate_list = []
        for r in rows:
            candidate_list.append({
                "student_id": r.student_id,
                "name": r.name,
                "roll": r.roll,
                "confidence": round(float(r.similarity), 4),
                "face_photo": r.face_photo_b64,
            })

        if not rows:
            # Below minimum threshold / no match -> unknown face
            draft_entries.append(DraftEntry(
                student_id=None,
                confidence=0.0,
                status="unknown",
                face_crop_b64=face.face_crop_b64,
                source_image_idx=face.source_image_idx,
                bbox=face.bbox,
                candidates=[],
            ))
            continue

        top_row = rows[0]
        student_id = top_row.student_id
        confidence = float(top_row.similarity)

        # ── Step 4: Second-pass re-verification for 0.75–0.90 band ───────────
        if THRESHOLD_REVIEW <= confidence < THRESHOLD_AUTO:
            orig_img = decoded_images[face.source_image_idx]
            better_embedding = _tighter_crop_and_reembed(orig_img, face.bbox)

            if better_embedding is not None:
                query_vec2 = str(better_embedding.tolist())
                try:
                    result2 = await db.execute(
                        text(ANN_SEARCH_SQL),
                        {"qvec": query_vec2},
                    )
                    rows2 = result2.fetchall()
                    if rows2:
                        # Re-build candidates with new similarity scores
                        candidate_list = []
                        for r in rows2:
                            candidate_list.append({
                                "student_id": r.student_id,
                                "name": r.name,
                                "roll": r.roll,
                                "confidence": round(float(r.similarity), 4),
                                "face_photo": r.face_photo_b64,
                            })
                        top_row2 = rows2[0]
                        if top_row2.student_id == student_id:
                            confidence = max(confidence, float(top_row2.similarity))
                            candidate_list[0]["confidence"] = round(confidence, 4)
                            logger.info(f"Re-verification boosted confidence: {confidence:.3f}")
                except Exception as e:
                    logger.warning(f"Re-verification search failed: {e}")

        # Classify final confidence
        if confidence >= THRESHOLD_AUTO:
            status = "auto_present"
        elif confidence >= THRESHOLD_REVIEW:
            status = "needs_review"
        else:
            status = "unknown"
            student_id = None

        if student_id and student_id not in matched_student_ids:
            matched_student_ids.add(student_id)
            draft_entries.append(DraftEntry(
                student_id=student_id,
                confidence=confidence,
                status=status,
                face_crop_b64=face.face_crop_b64,
                source_image_idx=face.source_image_idx,
                bbox=face.bbox,
                candidates=candidate_list,
            ))
        elif student_id and student_id in matched_student_ids:
            # Duplicate match — upgrade confidence if better
            for entry in draft_entries:
                if entry.student_id == student_id:
                    if confidence > entry.confidence:
                        entry.confidence = confidence
                        entry.candidates = candidate_list
                        if confidence >= THRESHOLD_AUTO:
                            entry.status = "auto_present"
                        elif confidence >= THRESHOLD_REVIEW:
                            entry.status = "needs_review"
                    break
        else:
            # Unknown face
            draft_entries.append(DraftEntry(
                student_id=None,
                confidence=confidence,
                status="unknown",
                face_crop_b64=face.face_crop_b64,
                source_image_idx=face.source_image_idx,
                bbox=face.bbox,
                candidates=candidate_list,
            ))

    # ── Step 5: Determine not_detected ─────────────────────────────────────────
    not_detected = [
        s for s in enrolled_students
        if s["student_id"] not in matched_student_ids
    ]

    # ── Step 6: Build result ────────────────────────────────────────────────────
    student_lookup = {s["student_id"]: s for s in enrolled_students}

    auto_present  = []
    needs_review  = []
    unknown_faces = []

    for entry in draft_entries:
        if entry.status == "unknown":
            unknown_faces.append({
                "face_crop": entry.face_crop_b64,
                "bbox": entry.bbox,
                "source_image": entry.source_image_idx,
                "candidates": entry.candidates,
            })
        else:
            student = student_lookup.get(entry.student_id, {})
            record = {
                "student_id":  entry.student_id,
                "name":        student.get("name", "Unknown"),
                "roll":        student.get("roll", ""),
                "confidence":  round(entry.confidence, 4),
                "face_crop":   entry.face_crop_b64,
                "source_image": entry.source_image_idx,
                "status":      entry.status,
                "candidates":  entry.candidates,
            }
            if entry.status == "auto_present":
                auto_present.append(record)
            else:
                needs_review.append(record)

    return AttendanceDraftResult(
        auto_present=auto_present,
        needs_review=needs_review,
        unknown_faces=unknown_faces,
        not_detected=not_detected,
    )
