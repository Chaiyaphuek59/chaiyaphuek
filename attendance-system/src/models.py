from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class UserRole(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    role = Column(String(20), default=UserRole.STUDENT, nullable=False)
    student_id = Column(String(20), unique=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    face_embedding = Column(Text, nullable=True) # เก็บ JSON array ของเวกเตอร์ 128 มิติ
    created_at = Column(DateTime, default=datetime.utcnow)

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(100), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceSession(Base):
    """รอบการเช็กชื่อที่อาจารย์เปิดใช้งาน"""
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    teacher_lat = Column(Float, nullable=False)
    teacher_lon = Column(Float, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Integer, default=1) # 1 = เปิด, 0 = ปิด

class AttendanceRecord(Base):
    """ประวัติการเช็กชื่อของนักศึกษาแต่ละคน"""
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checked_in_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="PRESENT") # PRESENT, REJECTED, MANUAL_OVERRIDE
    distance_meters = Column(Float, nullable=True)
    face_distance = Column(Float, nullable=True)
    rejection_reason = Column(String(255), nullable=True)
    override_reason = Column(String(255), nullable=True)
    override_by = Column(Integer, ForeignKey("users.id"), nullable=True)
