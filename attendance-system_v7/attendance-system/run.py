# -*- coding: utf-8 -*-
"""
รันระบบเช็กชื่อ:  python run.py   (หรือดับเบิลคลิก run.bat / run.sh)
- สร้าง .venv และติดตั้งแพ็กเกจให้อัตโนมัติ (ครั้งแรกครั้งเดียว)
- หาพอร์ตว่างให้เอง และเปิดเบราว์เซอร์อัตโนมัติ
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MARKER = VENV / ".installed"

if sys.version_info < (3, 10):
    print("[ERROR] ต้องใช้ Python 3.10 ขึ้นไป (เครื่องนี้คือ %d.%d)" % sys.version_info[:2])
    print("ดาวน์โหลดได้ที่ https://www.python.org/downloads/")
    sys.exit(1)


def bootstrap() -> None:
    """สร้าง .venv + ติดตั้งแพ็กเกจ แล้วรันตัวเองใหม่ภายใน .venv"""
    if Path(sys.prefix).resolve() == VENV.resolve():
        return
    if not VENV_PY.exists():
        print("[SETUP] กำลังเตรียมระบบครั้งแรก (อาจใช้เวลา 1-2 นาที)...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    if not MARKER.exists():
        print("[SETUP] กำลังติดตั้งแพ็กเกจ...")
        if subprocess.call([str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")]) != 0:
            print("[ERROR] ติดตั้งแพ็กเกจไม่สำเร็จ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่")
            sys.exit(1)
        MARKER.write_text("ok")
    sys.exit(subprocess.call([str(VENV_PY), str(ROOT / "run.py")]))


def free_port(start: int = 8000) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("[ERROR] ไม่พบพอร์ตว่าง")


def open_browser_when_ready(url: str, port: int) -> None:
    for _ in range(60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.5)


def main() -> None:
    bootstrap()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import uvicorn

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 55)
    print("  ระบบเช็กชื่อกำลังทำงาน")
    print(f"  เปิดเบราว์เซอร์ที่:  {url}")
    print("  กด Ctrl+C เพื่อหยุดโปรแกรม")
    print("=" * 55 + "\n")
    if not os.environ.get("NO_BROWSER"):
        threading.Thread(target=open_browser_when_ready, args=(url, port), daemon=True).start()
    uvicorn.run("src.app:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
