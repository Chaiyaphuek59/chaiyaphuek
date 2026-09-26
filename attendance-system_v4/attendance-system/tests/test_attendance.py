import unittest
from datetime import datetime, timedelta
import json
from src.attendance_service import AttendanceService, calculate_haversine_distance

class TestAttendanceVerification(unittest.TestCase):
    def setUp(self):
        # พิกัดอาจารย์ (ตึกเรียน)
        self.teacher_lat = 13.756300
        self.teacher_lon = 100.501800
        self.registered_vector = [0.10, 0.20, 0.30, 0.40]
        self.registered_json = json.dumps(self.registered_vector)
        self.expires_at = datetime.utcnow() + timedelta(minutes=15)

    def test_checkin_success(self):
        """กรณีผ่านครบ 3 เงื่อนไข (ระยะทางประมาณ 15 เมตร, ใบหน้าตรง, ในเวลา)"""
        student_lat = 13.756400
        student_lon = 100.501850
        matching_vector = [0.11, 0.19, 0.31, 0.39]

        res = AttendanceService.evaluate_checkin(
            session_is_active=True,
            session_expires_at=self.expires_at,
            teacher_lat=self.teacher_lat,
            teacher_lon=self.teacher_lon,
            registered_face_json=self.registered_json,
            student_lat=student_lat,
            student_lon=student_lon,
            face_vector=matching_vector
        )

        self.assertTrue(res["success"])
        self.assertLessEqual(res["distance_meters"], 50.0)

    def test_checkin_fail_outside_50m(self):
        """กรณีอยู่นอกระยะ 50 เมตร (ห่างประมาณ 180 เมตร)"""
        student_lat = 13.757800
        student_lon = 100.501800
        matching_vector = [0.10, 0.20, 0.30, 0.40]

        res = AttendanceService.evaluate_checkin(
            session_is_active=True,
            session_expires_at=self.expires_at,
            teacher_lat=self.teacher_lat,
            teacher_lon=self.teacher_lon,
            registered_face_json=self.registered_json,
            student_lat=student_lat,
            student_lon=student_lon,
            face_vector=matching_vector
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "LOCATION_OUT_OF_RANGE")
        self.assertGreater(res["distance_meters"], 50.0)

    def test_checkin_fail_face_mismatch(self):
        """กรณีอยู่ในระยะ 50 เมตรแต่ใบหน้าไม่ตรงกัน"""
        student_lat = 13.756320
        student_lon = 100.501810
        mismatch_vector = [0.95, -0.80, 0.65, -0.50]

        res = AttendanceService.evaluate_checkin(
            session_is_active=True,
            session_expires_at=self.expires_at,
            teacher_lat=self.teacher_lat,
            teacher_lon=self.teacher_lon,
            registered_face_json=self.registered_json,
            student_lat=student_lat,
            student_lon=student_lon,
            face_vector=mismatch_vector
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "FACE_MISMATCH")

    def test_checkin_fail_time_expired(self):
        """กรณีหมดเวลาเช็กชื่อ"""
        past_expiration = datetime.utcnow() - timedelta(minutes=1)
        student_lat = 13.756300
        student_lon = 100.501800

        res = AttendanceService.evaluate_checkin(
            session_is_active=True,
            session_expires_at=past_expiration,
            teacher_lat=self.teacher_lat,
            teacher_lon=self.teacher_lon,
            registered_face_json=self.registered_json,
            student_lat=student_lat,
            student_lon=student_lon,
            face_vector=self.registered_vector
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "TIME_EXPIRED")

if __name__ == "__main__":
    unittest.main()
