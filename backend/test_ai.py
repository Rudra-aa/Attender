#!/usr/bin/env python3
"""
Attender V3 — AI Stack Diagnostic
===================================
Verifies InsightFace, ONNXRuntime, buffalo_l model, and embedding extraction.

Usage:
    cd attender/backend
    .venv/bin/python test_ai.py
    .venv/bin/python test_ai.py --image /path/to/classroom.jpg

If no --image is provided, a synthetic test image is generated automatically.
"""

import sys
import time
import argparse
import base64
import io
import os

# ── Color helpers ──────────────────────────────────────────────────────────────
def ok(msg):   print(f"  ✅  {msg}")
def fail(msg): print(f"  ❌  {msg}"); sys.exit(1)
def info(msg): print(f"  ℹ️   {msg}")
def section(title): print(f"\n{'='*55}\n  {title}\n{'='*55}")


def main():
    parser = argparse.ArgumentParser(description="Attender AI stack diagnostic")
    parser.add_argument("--image", help="Path to a classroom image (optional)", default=None)
    args = parser.parse_args()

    print("\n🔍 Attender V3 — AI Stack Diagnostic\n")

    # ── 1. numpy ──────────────────────────────────────────────────────────────
    section("1. numpy")
    try:
        import numpy as np
        ok(f"numpy {np.__version__}")
    except ImportError as e:
        fail(f"numpy not installed: {e}")

    # ── 2. OpenCV ─────────────────────────────────────────────────────────────
    section("2. OpenCV")
    try:
        import cv2
        ok(f"opencv {cv2.__version__}")
    except ImportError as e:
        fail(f"cv2 not installed: {e}")

    # ── 3. Pillow ─────────────────────────────────────────────────────────────
    section("3. Pillow")
    try:
        from PIL import Image
        import PIL
        ok(f"Pillow {PIL.__version__}")
    except ImportError as e:
        fail(f"Pillow not installed: {e}")

    # ── 4. ONNXRuntime ────────────────────────────────────────────────────────
    section("4. ONNXRuntime")
    try:
        import onnxruntime as ort
        ok(f"onnxruntime {ort.__version__}")
        providers = ort.get_available_providers()
        info(f"Providers: {providers}")
        if "CPUExecutionProvider" in providers:
            ok("CPUExecutionProvider available (will work on Mac)")
        if "CoreMLExecutionProvider" in providers:
            ok("CoreMLExecutionProvider available (Apple Silicon acceleration)")
        if "CUDAExecutionProvider" in providers:
            ok("CUDAExecutionProvider available (GPU acceleration)")
    except ImportError as e:
        fail(f"onnxruntime not installed: {e}")

    # ── 5. InsightFace ────────────────────────────────────────────────────────
    section("5. InsightFace")
    try:
        import insightface
        ok(f"insightface {insightface.__version__}")
    except ImportError as e:
        fail(f"insightface not installed: {e}")

    # ── 6. buffalo_l model load ───────────────────────────────────────────────
    section("6. Loading buffalo_l model (downloads on first run ~300MB)")
    from insightface.app import FaceAnalysis

    model_root = os.path.join(os.path.dirname(__file__), "app", "ml", "models")
    os.makedirs(model_root, exist_ok=True)
    info(f"Model root: {model_root}")

    t0 = time.time()
    try:
        analyzer = FaceAnalysis(
            name="buffalo_l",
            root=model_root,
            providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
        )
        analyzer.prepare(ctx_id=0, det_size=(640, 640))
        elapsed = time.time() - t0
        ok(f"buffalo_l loaded in {elapsed:.2f}s")
    except Exception as e:
        fail(f"buffalo_l load failed: {e}")

    # ── 7. Synthetic image test ───────────────────────────────────────────────
    section("7. Face Detection & Embedding Test")

    if args.image:
        info(f"Using image: {args.image}")
        img = cv2.imread(args.image)
        if img is None:
            fail(f"Could not read image: {args.image}")
    else:
        info("No --image provided. Creating synthetic test image (100x100 plain).")
        info("For real results, run: .venv/bin/python test_ai.py --image /path/to/photo.jpg")
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (120, 100, 90)  # Gray background
        # Note: InsightFace will return 0 faces on this synthetic image — that's expected

    t1 = time.time()
    faces = analyzer.get(img)
    elapsed2 = time.time() - t1

    info(f"Detection time: {elapsed2*1000:.1f}ms")
    info(f"Faces detected: {len(faces)}")

    if len(faces) == 0:
        if args.image:
            info("⚠️  No faces detected. Try a clearer, well-lit photo with visible faces.")
        else:
            info("Expected: 0 faces on synthetic image. Pass --image to test with a real photo.")
    else:
        for i, face in enumerate(faces):
            emb = face.normed_embedding
            det_score = float(face.det_score)
            ok(f"Face {i+1}: det_score={det_score:.3f}, embedding shape={emb.shape}, "
               f"norm={float(np.linalg.norm(emb)):.4f}")
            if emb.shape[0] == 512:
                ok("Embedding is 512-dimensional ✓ (ArcFace compatible)")
            else:
                info(f"Unexpected embedding size: {emb.shape}")

    # ── 8. Base64 round-trip ──────────────────────────────────────────────────
    section("8. Base64 Image Decode (as received from frontend)")
    try:
        from PIL import Image as PILImage
        buf = io.BytesIO()
        PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        b64_with_prefix = "data:image/jpeg;base64," + b64

        # Decode back (as our ai_engine.py does)
        raw = b64_with_prefix.split(",", 1)[1]
        decoded = base64.b64decode(raw)
        pil = PILImage.open(io.BytesIO(decoded)).convert("RGB")
        img_back = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

        ok(f"Base64 encode → decode round-trip: {img_back.shape} ✓")
    except Exception as e:
        fail(f"Base64 round-trip failed: {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    section("RESULT")
    print("  ✅  All AI components operational.\n")
    print("  Next steps:")
    print("  1. Enroll student faces via POST /api/v1/faces/enroll/multi-angle")
    print("  2. Start backend: .venv/bin/uvicorn app.main:app --reload")
    print("  3. Take classroom photo and hit POST /api/v1/sessions/{id}/analyze")
    print()


if __name__ == "__main__":
    main()
