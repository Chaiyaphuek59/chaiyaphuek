# Attendance Verification System

## วิธีรัน (3 ขั้นตอน)
1. ติดตั้ง Python 3.10+ จาก https://www.python.org/downloads/ (Windows: ติ๊ก "Add Python to PATH")
2. ดับเบิลคลิก `run.bat` (Windows) / `run.command` (Mac) / `./run.sh` (Linux) — หรือสั่ง `python run.py`
3. เสร็จ! เบราว์เซอร์จะเปิดหน้าเว็บให้อัตโนมัติ (ครั้งแรกรอติดตั้ง 1-2 นาที)

## 9. ขั้นตอนการติดตั้งและรันระบบ (Setup & Execution)

1. **สร้างและเปิดใช้งาน Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # บน Windows ใช้: venv\Scripts\activate
   ```

2. **ติดตั้งไลบรารี:**
   ```bash
   pip install -r requirements.txt
   ```

3. **รัน Unit Tests เพื่อทดสอบความถูกต้องของ 3 เงื่อนไข:**
   ```bash
   python -m unittest tests/test_attendance.py
   ```

4. **เริ่มการทำงานของเซิร์ฟเวอร์:**
   ```bash
   uvicorn src.app:app --reload --port 8000
   ```
   จากนั้นเปิดหน้าเว็บที่ `http://localhost:8000` ระบบจะนำไปยังหน้านักศึกษาโดยอัตโนมัติ

## หน้าเว็บที่พร้อมใช้งาน

- **นักศึกษา:** `http://localhost:8000/student`
- **อาจารย์:** `http://localhost:8000/teacher`
- **ผู้ดูแลระบบ:** `http://localhost:8000/admin`
- **เอกสาร API:** `http://localhost:8000/docs`

หน้าเว็บใช้ Tailwind CSS และไอคอนผ่าน CDN จึงต้องเชื่อมต่ออินเทอร์เน็ตเมื่อเปิดใช้งาน
ฟังก์ชัน GPS และกล้องต้องได้รับอนุญาตจากผู้ใช้ และควรเปิดผ่าน `localhost` หรือ HTTPS


