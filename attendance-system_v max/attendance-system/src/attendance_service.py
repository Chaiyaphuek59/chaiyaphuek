import math
import json
from datetime import datetime
from typing import Tuple, Dict, Any, List

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """คำนวณระยะห่างระหว่างพิกัด 2 จุดเป็นเมตร"""
    R = 6371000.0  # รัศมีเฉลี่ยของโลก (เมตร)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2) + \
        (math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def verify_face_vector(registered_vector_json: str, checkin_vector: List[float], threshold: float = 0.6) -> Tuple[bool, float]:
    """เปรียบเทียบ vector ที่ลงทะเบียนไว้กับ vector ตอนเช็กชื่อ"""
    if not registered_vector_json or not checkin_vector:
        return False, 999.0

    try:
        registered = json.loads(registered_vector_json)
    except Exception:
        return False, 999.0

    if len(registered) != len(checkin_vector):
        return False, 999.0

    # หาระยะห่างของข้อมูลทั้งสองชุด
    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(registered, checkin_vector)))
    is_match = dist <= threshold
    return is_match, dist

class AttendanceService:
    MAX_DISTANCE_METERS = 50.0  # นักศึกษาต้องอยู่ไม่เกิน 50 เมตรจากจุดที่อาจารย์เปิดรอบ

    @classmethod
    def evaluate_checkin(
        cls,
        session_is_active: bool,
        session_expires_at: datetime,
        teacher_lat: float,
        teacher_lon: float,
        registered_face_json: str,
        student_lat: float,
        student_lon: float,
        face_vector: List[float],
        current_time: datetime = None
    ) -> Dict[str, Any]:
        """ตรวจสอบเวลา ตำแหน่ง และข้อมูลใบหน้าก่อนบันทึกการเข้าเรียน"""
        if current_time is None:
            current_time = datetime.utcnow()

        # เช็กเวลาก่อน เพราะถ้ารอบปิดแล้วไม่ต้องคำนวณอย่างอื่น
        if not session_is_active or current_time > session_expires_at:
            return {
                "success": False,
                "error_code": "TIME_EXPIRED",
                "message": "รอบการเช็กชื่อปิดแล้ว หรือหมดเวลาที่กำหนด"
            }

        # ตรวจว่าตำแหน่งนักศึกษาอยู่ใกล้จุดที่อาจารย์เปิดรอบหรือไม่
        distance = calculate_haversine_distance(teacher_lat, teacher_lon, student_lat, student_lon)
        if distance > cls.MAX_DISTANCE_METERS:
            return {
                "success": False,
                "error_code": "LOCATION_OUT_OF_RANGE",
                "message": f"อยู่นอกระยะที่กำหนด (อยู่ห่าง {distance:.1f} เมตร เกินเกณฑ์ 50 เมตร)",
                "distance_meters": round(distance, 2)
            }

        # ขั้นสุดท้ายคือเปรียบเทียบ vector ใบหน้า
        is_match, face_dist = verify_face_vector(registered_face_json, face_vector)
        if not is_match:
            return {
                "success": False,
                "error_code": "FACE_MISMATCH",
                "message": "การสแกนใบหน้าไม่ตรงกับข้อมูลชีวมิติที่ลงทะเบียนไว้",
                "face_distance": round(face_dist, 4)
            }

        # ผ่านทุกเงื่อนไข
        return {
            "success": True,
            "message": "เช็กชื่อเข้าเรียนสำเร็จ",
            "distance_meters": round(distance, 2),
            "face_distance": round(face_dist, 4)
        }
