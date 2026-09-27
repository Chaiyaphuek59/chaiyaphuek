"""
คลังข้อมูลในหน่วยความจำ (In-memory) สำหรับเดโม
ในระบบจริงให้แทนที่ด้วยฐานข้อมูลผ่าน SQLAlchemy (ดู src/models.py)
"""
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class Store:
    def __init__(self) -> None:
        self.students: Dict[str, dict] = {}          # student_id -> {full_name, face_json}
        self.tokens: Dict[str, str] = {}             # token -> student_id
        self.classes: Dict[int, dict] = {}           # id -> {id, name, code, teacher, members:set}
        self.sessions: Dict[int, dict] = {}          # id -> {id, class_id, lat, lon, started_at, expires_at, active}
        self.records: List[dict] = []                # {session_id, class_id, student_id, time, distance}
        self.teachers: Dict[str, dict] = {"T001": {"full_name": "อ.สมชาย ใจดี"}}  # teacher_id -> {full_name}
        self.staff_tokens: Dict[str, tuple] = {}     # token -> (role, id)
        self._class_seq = 0
        self._session_seq = 0
        self.create_class("คณิตศาสตร์พื้นฐาน", "MATH101", "อ.สมชาย ใจดี")

    # ---------- นักศึกษา / ล็อกอิน ----------
    def new_token(self, student_id: str) -> str:
        token = secrets.token_urlsafe(24)
        self.tokens[token] = student_id
        return token

    def student_from_token(self, token: Optional[str]) -> Optional[dict]:
        sid = self.tokens.get(token or "")
        if not sid or sid not in self.students:
            return None
        return {"student_id": sid, **self.students[sid]}

    # ---------- อาจารย์ / ผู้ดูแล ----------
    def new_staff_token(self, role: str, ident: str) -> str:
        token = secrets.token_urlsafe(24)
        self.staff_tokens[token] = (role, ident)
        return token

    def staff_from_token(self, token: Optional[str], role: str) -> Optional[dict]:
        entry = self.staff_tokens.get(token or "")
        if not entry or entry[0] != role:
            return None
        if role == "teacher":
            t = self.teachers.get(entry[1])
            return {"teacher_id": entry[1], **t} if t else None
        return {"admin": True}

    # ---------- ชั้นเรียน ----------
    def create_class(self, name: str, code: str, teacher: str = "อาจารย์ผู้สอน") -> dict:
        code = code.strip().upper()
        if any(c["code"] == code for c in self.classes.values()):
            raise ValueError("รหัสคลาสนี้ถูกใช้แล้ว")
        self._class_seq += 1
        cls = {"id": self._class_seq, "name": name.strip(), "code": code, "teacher": teacher, "members": set()}
        self.classes[cls["id"]] = cls
        return cls

    def find_class_by_code(self, code: str) -> Optional[dict]:
        code = code.strip().upper()
        return next((c for c in self.classes.values() if c["code"] == code), None)

    # ---------- รอบเช็กชื่อ ----------
    def active_session(self, class_id: int) -> Optional[dict]:
        now = datetime.utcnow()
        for s in self.sessions.values():
            if s["class_id"] == class_id and s["active"]:
                if now > s["expires_at"]:
                    s["active"] = False
                else:
                    return s
        return None

    def start_session(self, class_id: int, lat: float, lon: float, minutes: int) -> dict:
        old = self.active_session(class_id)
        if old:
            old["active"] = False
        self._session_seq += 1
        now = datetime.utcnow()
        s = {"id": self._session_seq, "class_id": class_id, "lat": lat, "lon": lon,
             "started_at": now, "expires_at": now + timedelta(minutes=minutes), "active": True}
        self.sessions[s["id"]] = s
        return s

    def class_records(self, class_id: int) -> List[dict]:
        return [r for r in self.records if r["class_id"] == class_id]

    def has_checked_in(self, session_id: int, student_id: str) -> bool:
        return any(r["session_id"] == session_id and r["student_id"] == student_id for r in self.records)


store = Store()
