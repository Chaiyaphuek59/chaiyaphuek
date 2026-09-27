# -*- coding: utf-8 -*-
"""
ไฟล์สำหรับรันระบบเช็กชื่อ — ใช้คำสั่ง:  python run.py
- ตรวจสอบและติดตั้งแพ็กเกจที่จำเป็นให้อัตโนมัติ
- ตั้งค่าเส้นทางโปรเจกต์ให้ถูกต้อง (ไม่มีปัญหา No module named 'src')
- เปิดเว็บเซิร์ฟเวอร์ที่ http://127.0.0.1:8000
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED = {
    "fastapi": "fastapi>=0.100.0",
    "uvicorn": "uvicorn[standard]>=0.23.0",
    "pydantic": "pydantic>=2.0.0",
    "sqlalchemy": "sqlalchemy>=2.0.0",
    "jinja2": "jinja2>=3.1.0",
}


def ensure_packages() -> None:
    """ติดตั้งแพ็กเกจที่ยังไม่มี โดยอ่านจาก requirements.txt"""
    missing = []
    for module in REQUIRED:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if not missing:
        print("[OK] แพ็กเกจครบแล้ว")
        return

    print(f"[SETUP] กำลังติดตั้งแพ็กเกจที่ขาด: {', '.join(missing)}")
    req_file = PROJECT_ROOT / "requirements.txt"
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[ERROR] ติดตั้งแพ็กเกจไม่สำเร็จ กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต")
        sys.exit(1)
    print("[OK] ติดตั้งแพ็กเกจเรียบร้อย")


def main() -> None:
    ensure_packages()

    import uvicorn

    host = "127.0.0.1"
    port = 8000
    print()
    print("=" * 55)
    print("  ระบบเช็กชื่อกำลังทำงาน")
    print(f"  เปิดเบราว์เซอร์ที่:  http://{host}:{port}")
    print("  กด Ctrl+C เพื่อหยุดโปรแกรม")
    print("=" * 55)
    print()

    uvicorn.run("src.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
