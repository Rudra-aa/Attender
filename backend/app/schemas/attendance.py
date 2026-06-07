"""Pydantic schemas for attendance endpoints"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MarkAttendanceRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded JPEG from browser webcam")
    lat: float = Field(..., ge=-90, le=90, description="Student GPS latitude")
    lon: float = Field(..., ge=-180, le=180, description="Student GPS longitude")
    liveness_token: str = Field(..., description="HMAC-signed liveness token from client challenge")
    liveness_challenge: str = Field(..., description="The challenge that was issued (BLINK/TURN_LEFT/etc)")
    device_fingerprint: Optional[str] = None


class AttendanceResult(BaseModel):
    status: str
    session_id: str
    subject_name: str
    marked_at: datetime
    face_confidence: float
    distance_m: int

    class Config:
        from_attributes = True
