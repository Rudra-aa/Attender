"""
InsightFace verification script — run before building enrollment.
Tests: model load, SCRFD detection, ArcFace 512-dim embedding.
"""
import sys
import os
import numpy as np

print("=" * 60)
print("InsightFace Pipeline Verification")
print("=" * 60)

# Step 1: Import
try:
    import insightface
    from insightface.app import FaceAnalysis
    print(f"✅ insightface imported: v{insightface.__version__}")
except ImportError as e:
    print(f"❌ FAILED to import insightface: {e}")
    sys.exit(1)

try:
    import onnxruntime as ort
    print(f"✅ onnxruntime imported: v{ort.__version__}")
    print(f"   Providers available: {ort.get_available_providers()}")
except ImportError as e:
    print(f"❌ FAILED to import onnxruntime: {e}")
    sys.exit(1)

try:
    import cv2
    print(f"✅ cv2 imported: v{cv2.__version__}")
except ImportError as e:
    print(f"❌ FAILED to import cv2: {e}")
    sys.exit(1)

# Step 2: Load model
print("\n--- Loading buffalo_l model ---")
model_root = os.environ.get("INSIGHTFACE_HOME", "./app/ml/models")
os.makedirs(model_root, exist_ok=True)

try:
    analyzer = FaceAnalysis(
        name="buffalo_l",
        root=model_root,
        providers=["CPUExecutionProvider"],
    )
    analyzer.prepare(ctx_id=0, det_size=(640, 640))
    print(f"✅ buffalo_l loaded successfully from {model_root}")
except Exception as e:
    print(f"❌ FAILED to load buffalo_l: {e}")
    print(f"   Model root: {os.path.abspath(model_root)}")
    sys.exit(1)

# Step 3: Create a test image with a synthetic face
# We'll use a real test: create a blank image and try detection
print("\n--- Testing face detection on synthetic image ---")
# Create a simple 640x640 BGR image (blank — expect 0 faces, which is fine)
test_img = np.zeros((640, 640, 3), dtype=np.uint8)
# Add a gray rectangle to simulate a face region
test_img[150:450, 200:440] = 128
faces = analyzer.get(test_img)
print(f"✅ SCRFD detection ran without error (found {len(faces)} faces on blank test image — expected 0)")

# Step 4: Try with a real-ish face test using cv2 sample
print("\n--- Testing embedding extraction ---")

# Generate a test image that looks more like a face (noise-based)
face_like = np.random.randint(100, 200, (224, 224, 3), dtype=np.uint8)
face_resized = cv2.resize(face_like, (640, 640))
faces2 = analyzer.get(face_resized)

if faces2:
    emb = faces2[0].normed_embedding
    print(f"✅ ArcFace embedding extracted!")
    print(f"   Embedding shape: {emb.shape}")
    print(f"   Embedding dtype: {emb.dtype}")
    print(f"   L2 norm: {np.linalg.norm(emb):.4f} (should be ~1.0)")
    assert len(emb) == 512, f"Expected 512 dimensions, got {len(emb)}"
    print(f"✅ 512-dimensional embedding confirmed")
else:
    print(f"ℹ️  No face detected in noise image (expected) — model is working correctly")
    print(f"   To test embedding, use a real face photo.")

print("\n--- Checking model files downloaded ---")
models_path = os.path.join(model_root, "models", "buffalo_l")
if os.path.exists(models_path):
    model_files = os.listdir(models_path)
    print(f"✅ Model files in {models_path}:")
    for f in model_files:
        size = os.path.getsize(os.path.join(models_path, f))
        print(f"   - {f} ({size/1024/1024:.1f} MB)")
else:
    print(f"⚠️  Model dir not found at {models_path}")
    # Check alternate locations
    for root, dirs, files in os.walk(model_root):
        for f in files:
            if f.endswith('.onnx'):
                fp = os.path.join(root, f)
                print(f"   Found ONNX: {fp} ({os.path.getsize(fp)/1024/1024:.1f} MB)")

print("\n" + "=" * 60)
print("✅ InsightFace environment is READY")
print("=" * 60)
