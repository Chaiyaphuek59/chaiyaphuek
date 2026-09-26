import hmac
import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import Cookie, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from src.attendance_service import AttendanceService, verify_face_vector
from src.store import store

app = FastAPI(
    title="Smart Attendance System",
    description="ระบบเช็กชื่อเข้าเรียนด้วยพิกัด GPS ระยะ 50 เมตรและชีวมิติใบหน้า",
    version="1.1.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

FACE_THRESHOLD = 0.6
COOKIE = "sid"
TEACHER_COOKIE = "tsid"
ADMIN_COOKIE = "asid"
DEFAULT_ADMIN_CODE = "ADMIN-2026"


def admin_code() -> str:
    return os.environ.get("ADMIN_CODE", DEFAULT_ADMIN_CODE)


# ---------------- Schemas ----------------
class RegisterRequest(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=20)
    full_name: str = Field(..., min_length=1, max_length=100)
    face_vector: List[float]

class LoginRequest(BaseModel):
    student_id: str
    face_vector: List[float]

class TeacherLoginRequest(BaseModel):
    teacher_id: str

class AdminLoginRequest(BaseModel):
    admin_code: str

class AddTeacherRequest(BaseModel):
    teacher_id: str = Field(..., min_length=2, max_length=20)
    full_name: str = Field(..., min_length=1, max_length=100)

class JoinClassRequest(BaseModel):
    code: str

class CreateClassRequest(BaseModel):
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=2, max_length=20)

class StartSessionRequest(BaseModel):
    classroom_id: int
    teacher_lat: float = Field(..., description="พิกัดละติจูดของอาจารย์ ณ ตอนเปิดรอบ")
    teacher_lon: float = Field(..., description="พิกัดลองจิจูดของอาจารย์ ณ ตอนเปิดรอบ")
    duration_minutes: int = Field(default=15, ge=1, le=180)

class StudentCheckInRequest(BaseModel):
    session_id: int
    lat: float
    lon: float
    face_vector: List[float]


# ---------------- Helpers ----------------
def current_student(sid: Optional[str]) -> Optional[dict]:
    return store.student_from_token(sid)

def require_student(sid: Optional[str]) -> dict:
    student = current_student(sid)
    if not student:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    return student

def require_teacher(tsid: Optional[str]) -> dict:
    t = store.staff_from_token(tsid, "teacher")
    if not t:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบอาจารย์")
    return t

def require_admin(asid: Optional[str]) -> dict:
    a = store.staff_from_token(asid, "admin")
    if not a:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบผู้ดูแล")
    return a

def session_view(s: Optional[dict]) -> Optional[dict]:
    if not s:
        return None
    return {
        "id": s["id"], "lat": s["lat"], "lon": s["lon"],
        "started_at": s["started_at"].isoformat() + "Z",
        "expires_at": s["expires_at"].isoformat() + "Z",
    }

def render(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request=request, name=name, context=ctx)


# ---------------- Pages ----------------
@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/student")

@app.get("/login", include_in_schema=False)
def login_page(request: Request, sid: Optional[str] = Cookie(default=None)):
    if current_student(sid):
        return RedirectResponse(url="/student", status_code=303)
    return render(request, "login.html", page="login")

@app.get("/student", include_in_schema=False)
def student_page(request: Request, sid: Optional[str] = Cookie(default=None)):
    student = current_student(sid)
    if not student:
        return RedirectResponse(url="/login", status_code=303)
    sid_ = student["student_id"]
    classes = []
    for c in store.classes.values():
        if sid_ in c["members"]:
            classes.append({**c, "session": store.active_session(c["id"])})
    open_count = sum(1 for c in classes if c["session"])
    done = sum(1 for r in store.records if r["student_id"] == sid_)
    return render(request, "student.html", page="student", student=student,
                  classes=classes, open_count=open_count, done_count=done)

@app.get("/student/classes/{class_id}", include_in_schema=False)
def student_class_page(class_id: int, request: Request, sid: Optional[str] = Cookie(default=None)):
    student = current_student(sid)
    if not student:
        return RedirectResponse(url="/login", status_code=303)
    cls = store.classes.get(class_id)
    if not cls or student["student_id"] not in cls["members"]:
        return RedirectResponse(url="/student", status_code=303)
    session = store.active_session(class_id)
    my_records = [r for r in store.class_records(class_id) if r["student_id"] == student["student_id"]]
    total_sessions = sum(1 for s in store.sessions.values() if s["class_id"] == class_id)
    return render(request, "class_student.html", page="student", student=student, cls=cls,
                  session=session, session_json=json.dumps(session_view(session)),
                  checked=bool(session and store.has_checked_in(session["id"], student["student_id"])),
                  records=list(reversed(my_records)), total_sessions=total_sessions)

@app.get("/teacher/login", include_in_schema=False)
def teacher_login_page(request: Request, tsid: Optional[str] = Cookie(default=None)):
    if store.staff_from_token(tsid, "teacher"):
        return RedirectResponse(url="/teacher", status_code=303)
    return render(request, "staff_login.html", page="teacher", role="teacher")

@app.get("/admin/login", include_in_schema=False)
def admin_login_page(request: Request, asid: Optional[str] = Cookie(default=None)):
    if store.staff_from_token(asid, "admin"):
        return RedirectResponse(url="/admin", status_code=303)
    return render(request, "staff_login.html", page="admin", role="admin")

@app.get("/teacher", include_in_schema=False)
def teacher_page(request: Request, tsid: Optional[str] = Cookie(default=None)):
    teacher = store.staff_from_token(tsid, "teacher")
    if not teacher:
        return RedirectResponse(url="/teacher/login", status_code=303)
    classes = [{**c, "session": store.active_session(c["id"])} for c in store.classes.values()]
    return render(request, "teacher.html", page="teacher", teacher=teacher, classes=classes,
                  open_count=sum(1 for c in classes if c["session"]))

@app.get("/teacher/classes/{class_id}", include_in_schema=False)
def teacher_class_page(class_id: int, request: Request, tsid: Optional[str] = Cookie(default=None)):
    teacher = store.staff_from_token(tsid, "teacher")
    if not teacher:
        return RedirectResponse(url="/teacher/login", status_code=303)
    cls = store.classes.get(class_id)
    if not cls:
        return RedirectResponse(url="/teacher", status_code=303)
    session = store.active_session(class_id)
    members = [{"student_id": m, "full_name": store.students.get(m, {}).get("full_name", "-"),
                "checked": bool(session and store.has_checked_in(session["id"], m))} for m in sorted(cls["members"])]
    return render(request, "class_teacher.html", page="teacher", teacher=teacher, cls=cls, session=session,
                  session_json=json.dumps(session_view(session)), members=members,
                  records=list(reversed(store.class_records(class_id))), students=store.students)

@app.get("/admin", include_in_schema=False)
def admin_page(request: Request, asid: Optional[str] = Cookie(default=None)):
    if not store.staff_from_token(asid, "admin"):
        return RedirectResponse(url="/admin/login", status_code=303)
    return render(request, "admin.html", page="admin", admin=True,
                  teachers=store.teachers, student_count=len(store.students))


# ---------------- Auth API ----------------
@app.get("/api/health", summary="ตรวจสอบสถานะบริการ")
def health_check():
    return {"status": "ok", "service": "Smart Attendance API"}

@app.post("/api/auth/register", summary="ลงทะเบียนนักศึกษาพร้อมใบหน้า")
def register(req: RegisterRequest, response: Response):
    sid = req.student_id.strip()
    if sid in store.students:
        raise HTTPException(status_code=409, detail="รหัสนักศึกษานี้ลงทะเบียนแล้ว กรุณาเข้าสู่ระบบ")
    if len(req.face_vector) < 16:
        raise HTTPException(status_code=400, detail="ข้อมูลใบหน้าไม่ถูกต้อง")
    store.students[sid] = {"full_name": req.full_name.strip(), "face_json": json.dumps(req.face_vector)}
    response.set_cookie(COOKIE, store.new_token(sid), httponly=True, samesite="lax")
    return {"status": "success"}

@app.post("/api/auth/login", summary="เข้าสู่ระบบด้วยรหัสนักศึกษาและใบหน้า")
def login(req: LoginRequest, response: Response):
    sid = req.student_id.strip()
    student = store.students.get(sid)
    if not student:
        raise HTTPException(status_code=404, detail="ไม่พบรหัสนักศึกษา กรุณาลงทะเบียนก่อน")
    ok, dist = verify_face_vector(student["face_json"], req.face_vector, FACE_THRESHOLD)
    if not ok:
        raise HTTPException(status_code=401, detail="ใบหน้าไม่ตรงกับข้อมูลที่ลงทะเบียนไว้")
    response.set_cookie(COOKIE, store.new_token(sid), httponly=True, samesite="lax")
    return {"status": "success", "face_distance": round(dist, 4)}

@app.post("/api/auth/logout", summary="ออกจากระบบ")
def logout(response: Response, sid: Optional[str] = Cookie(default=None)):
    store.tokens.pop(sid or "", None)
    response.delete_cookie(COOKIE)
    return {"status": "success"}


@app.post("/api/auth/teacher/login", summary="อาจารย์เข้าสู่ระบบด้วยรหัสประจำตัวอาจารย์")
def teacher_login(req: TeacherLoginRequest, response: Response):
    tid = req.teacher_id.strip().upper()
    if tid not in store.teachers:
        raise HTTPException(status_code=401, detail="รหัสประจำตัวอาจารย์ไม่ถูกต้อง")
    response.set_cookie(TEACHER_COOKIE, store.new_staff_token("teacher", tid), httponly=True, samesite="lax")
    return {"status": "success"}

@app.post("/api/auth/admin/login", summary="ผู้ดูแลเข้าสู่ระบบด้วยรหัสแอดมิน")
def admin_login(req: AdminLoginRequest, response: Response):
    if not hmac.compare_digest(req.admin_code.strip().encode(), admin_code().encode()):
        raise HTTPException(status_code=401, detail="รหัสแอดมินไม่ถูกต้อง")
    response.set_cookie(ADMIN_COOKIE, store.new_staff_token("admin", "admin"), httponly=True, samesite="lax")
    return {"status": "success"}

@app.post("/api/auth/staff/logout", summary="อาจารย์/ผู้ดูแลออกจากระบบ")
def staff_logout(response: Response, tsid: Optional[str] = Cookie(default=None), asid: Optional[str] = Cookie(default=None)):
    store.staff_tokens.pop(tsid or "", None)
    store.staff_tokens.pop(asid or "", None)
    response.delete_cookie(TEACHER_COOKIE)
    response.delete_cookie(ADMIN_COOKIE)
    return {"status": "success"}


# ---------------- Admin API ----------------
@app.post("/api/admin/teachers", summary="ผู้ดูแลเพิ่มรหัสประจำตัวอาจารย์")
def add_teacher(req: AddTeacherRequest, asid: Optional[str] = Cookie(default=None)):
    require_admin(asid)
    tid = req.teacher_id.strip().upper()
    if tid in store.teachers:
        raise HTTPException(status_code=409, detail="รหัสอาจารย์นี้มีอยู่แล้ว")
    store.teachers[tid] = {"full_name": req.full_name.strip()}
    return {"status": "success", "teacher_id": tid}

@app.delete("/api/admin/teachers/{teacher_id}", summary="ผู้ดูแลถอนสิทธิ์อาจารย์")
def remove_teacher(teacher_id: str, asid: Optional[str] = Cookie(default=None)):
    require_admin(asid)
    if store.teachers.pop(teacher_id.upper(), None) is None:
        raise HTTPException(status_code=404, detail="ไม่พบรหัสอาจารย์")
    for tok, (role, ident) in list(store.staff_tokens.items()):
        if role == "teacher" and ident == teacher_id.upper():
            store.staff_tokens.pop(tok)
    return {"status": "success"}


# ---------------- Class API ----------------
@app.post("/api/classes/join", summary="นักศึกษาเข้าร่วมชั้นเรียนด้วยรหัสคลาส")
def join_class(req: JoinClassRequest, sid: Optional[str] = Cookie(default=None)):
    student = require_student(sid)
    cls = store.find_class_by_code(req.code)
    if not cls:
        raise HTTPException(status_code=404, detail="ไม่พบรหัสคลาสนี้")
    cls["members"].add(student["student_id"])
    return {"status": "success", "class_id": cls["id"]}

@app.post("/api/classes", summary="อาจารย์สร้างชั้นเรียน")
def create_class(req: CreateClassRequest, tsid: Optional[str] = Cookie(default=None)):
    teacher = require_teacher(tsid)
    try:
        cls = store.create_class(req.name, req.code, teacher["full_name"])
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "success", "class_id": cls["id"]}

@app.get("/api/classes/{class_id}/session", summary="สถานะรอบเช็กชื่อปัจจุบัน")
def class_session(class_id: int):
    return {"session": session_view(store.active_session(class_id))}


# ---------------- Session / Check-in API ----------------
@app.post("/api/sessions/start", summary="อาจารย์เปิดรอบเช็กชื่อ (ยืนยันตำแหน่ง ณ ตอนเปิด)")
def start_session(req: StartSessionRequest, tsid: Optional[str] = Cookie(default=None)):
    require_teacher(tsid)
    if req.classroom_id not in store.classes:
        raise HTTPException(status_code=404, detail="ไม่พบชั้นเรียน")
    if not (-90 <= req.teacher_lat <= 90 and -180 <= req.teacher_lon <= 180):
        raise HTTPException(status_code=400, detail="พิกัดไม่ถูกต้อง")
    s = store.start_session(req.classroom_id, req.teacher_lat, req.teacher_lon, req.duration_minutes)
    return {"status": "success", "session": session_view(s),
            "max_distance_meters": AttendanceService.MAX_DISTANCE_METERS}

@app.post("/api/sessions/{session_id}/close", summary="อาจารย์ปิดรอบเช็กชื่อ")
def close_session(session_id: int, tsid: Optional[str] = Cookie(default=None)):
    require_teacher(tsid)
    s = store.sessions.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="ไม่พบรอบเช็กชื่อ")
    s["active"] = False
    return {"status": "success"}

@app.post("/api/attendance/check-in", summary="นักศึกษาเช็กชื่อในหน้าชั้นเรียน")
def student_check_in(req: StudentCheckInRequest, sid: Optional[str] = Cookie(default=None)):
    student = require_student(sid)
    s = store.sessions.get(req.session_id)
    if not s:
        raise HTTPException(status_code=404, detail="ไม่พบรอบเช็กชื่อ")
    cls = store.classes[s["class_id"]]
    if student["student_id"] not in cls["members"]:
        raise HTTPException(status_code=403, detail="คุณไม่ได้อยู่ในชั้นเรียนนี้")
    if store.has_checked_in(s["id"], student["student_id"]):
        raise HTTPException(status_code=409, detail="คุณเช็กชื่อรอบนี้แล้ว")

    result = AttendanceService.evaluate_checkin(
        session_is_active=s["active"],
        session_expires_at=s["expires_at"],
        teacher_lat=s["lat"],
        teacher_lon=s["lon"],
        registered_face_json=student["face_json"],
        student_lat=req.lat,
        student_lon=req.lon,
        face_vector=req.face_vector,
    )
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

    store.records.append({
        "session_id": s["id"], "class_id": cls["id"], "student_id": student["student_id"],
        "time": datetime.utcnow().isoformat() + "Z", "distance": result.get("distance_meters"),
    })
    return {"status": "success", "data": result}
