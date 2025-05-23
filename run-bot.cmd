@echo off
REM Kích hoạt môi trường ảo nếu có
REM call venv\Scripts\activate

REM Cài đặt các thư viện cần thiết
pip install -r requirements.txt

REM Chạy bot
python main.py
pause