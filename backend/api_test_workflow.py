import httpx
import base64
import json
import asyncio
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_tests():
    print("==========================================")
    print("Testing Phase 7: Enrollment Workflow Test")
    print("==========================================")

    # 1. Login Student
    print("1. Logging in as student...")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/auth/login", json={"email": "student@test.com", "password": "password123"})
        if r.status_code != 200:
            print(f"Student login failed: {r.text}")
            return
        student_token = r.json()["access_token"]
        headers_student = {"Authorization": f"Bearer {student_token}"}
        print("✅ Student login successful")

        # 2. Get Subjects
        r = await client.get(f"{BASE_URL}/faces/enrollment-status/subjects", headers=headers_student)
        subjects = r.json()
        if not subjects:
            print("❌ No subjects found for student!")
            return
        subject_id = subjects[0]["subject_id"]
        print(f"✅ Found subject: {subjects[0]['subject_name']}")

        # 3. Read image and encode
        image_path = "/Users/rudrapratapsinghparmar/.gemini/antigravity-ide/brain/db08a9a9-73ca-4e01-92fe-d062a2b0f6eb/test_student_face_1780585872284.png"
        if not os.path.exists(image_path):
            print(f"❌ Image not found at {image_path}")
            return
        
        with open(image_path, "rb") as f:
            b64_image = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        # 4. Submit Guided Enrollment
        print("2. Submitting 5-angle face enrollment (this triggers InsightFace validation)...")
        payload = {
            "subject_id": subject_id,
            "images": [
                {"angle": "front", "image_data": b64_image},
                {"angle": "left", "image_data": b64_image},
                {"angle": "right", "image_data": b64_image},
                {"angle": "up", "image_data": b64_image},
                {"angle": "down", "image_data": b64_image}
            ]
        }
        r = await client.post(f"{BASE_URL}/faces/enroll/guided", json=payload, headers=headers_student, timeout=30.0)
        if r.status_code != 200:
            print(f"❌ Enrollment failed: {r.text}")
            return
        
        request_id = r.json()["request_id"]
        print("✅ Face enrollment request created successfully!")

        # 5. Login Professor
        print("\n3. Logging in as professor to approve...")
        r = await client.post(f"{BASE_URL}/auth/login", json={"email": "professor@test.com", "password": "password123"})
        prof_token = r.json()["access_token"]
        headers_prof = {"Authorization": f"Bearer {prof_token}"}
        print("✅ Professor login successful")

        # 6. Approve Enrollment
        r = await client.post(f"{BASE_URL}/enrollment/{request_id}/approve", headers=headers_prof)
        if r.status_code != 200:
            print(f"❌ Approval failed: {r.text}")
            return
        print("✅ Enrollment approved successfully! Face embeddings are now active.")
        print("==========================================")
        print("Phase 7 Verification Complete!")

if __name__ == "__main__":
    asyncio.run(run_tests())
