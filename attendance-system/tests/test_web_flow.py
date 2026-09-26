import unittest
from fastapi.testclient import TestClient
from src.app import app

FACE = [0.25] * 8 + [-0.25] * 8


class WebFlowTest(unittest.TestCase):
    def test_login_class_session_checkin(self):
        c = TestClient(app)
        self.assertEqual(c.get("/student", follow_redirects=False).status_code, 303)
        self.assertEqual(c.get("/login").status_code, 200)
        self.assertEqual(c.post("/api/auth/register", json={"student_id": "6500001", "full_name": "ทดสอบ", "face_vector": FACE}).status_code, 200)
        c.post("/api/auth/logout")
        bad = [-v for v in FACE]
        self.assertEqual(c.post("/api/auth/login", json={"student_id": "6500001", "face_vector": bad}).status_code, 401)
        self.assertEqual(c.post("/api/auth/login", json={"student_id": "6500001", "face_vector": FACE}).status_code, 200)
        cid = c.post("/api/classes/join", json={"code": "math101"}).json()["class_id"]
        self.assertEqual(c.get(f"/student/classes/{cid}").status_code, 200)
        self.assertEqual(c.post("/api/sessions/start", json={"classroom_id": cid, "teacher_lat": 1, "teacher_lon": 1}).status_code, 401)
        self.assertEqual(c.get("/teacher", follow_redirects=False).status_code, 303)
        self.assertEqual(c.post("/api/auth/teacher/login", json={"teacher_id": "X999"}).status_code, 401)
        self.assertEqual(c.post("/api/auth/teacher/login", json={"teacher_id": "t001"}).status_code, 200)
        s = c.post("/api/sessions/start", json={"classroom_id": cid, "teacher_lat": 13.7563, "teacher_lon": 100.5018}).json()["session"]
        far = c.post("/api/attendance/check-in", json={"session_id": s["id"], "lat": 13.76, "lon": 100.5018, "face_vector": FACE})
        self.assertEqual(far.status_code, 400)
        ok = c.post("/api/attendance/check-in", json={"session_id": s["id"], "lat": 13.7564, "lon": 100.5018, "face_vector": FACE})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(c.get(f"/teacher/classes/{cid}").status_code, 200)
        self.assertIn("มาแล้ว", c.get(f"/teacher/classes/{cid}").text)
        self.assertEqual(c.get("/teacher").status_code, 200)
        self.assertEqual(c.get("/admin", follow_redirects=False).status_code, 303)
        self.assertEqual(c.post("/api/auth/admin/login", json={"admin_code": "wrong"}).status_code, 401)
        self.assertEqual(c.post("/api/auth/admin/login", json={"admin_code": "ADMIN-2026"}).status_code, 200)
        self.assertEqual(c.get("/admin").status_code, 200)
        self.assertEqual(c.post("/api/admin/teachers", json={"teacher_id": "T002", "full_name": "อ.ใหม่"}).status_code, 200)
        self.assertIn("T002", c.get("/admin").text)


if __name__ == "__main__":
    unittest.main()
