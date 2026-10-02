#!/usr/bin/env bash
# ดับเบิลคลิก หรือสั่ง ./run.sh เพื่อเริ่มระบบ (Mac/Linux)
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  echo "[ERROR] ไม่พบ Python กรุณาติดตั้งจาก https://www.python.org/downloads/"
  read -r -p "กด Enter เพื่อปิด"; exit 1
fi
"$PY" run.py || read -r -p "โปรแกรมหยุดทำงานผิดปกติ กด Enter เพื่อปิด"
