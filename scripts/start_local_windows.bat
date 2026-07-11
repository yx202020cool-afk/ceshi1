@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0\.."

if not exist ".env" copy ".env.example" ".env" > nul

echo 使用本机 Python 启动 Streamlit。若提示缺依赖，请优先使用根目录 start_windows.bat。
python -m streamlit run ashare_replay\ui\streamlit_app.py --server.address=127.0.0.1 --server.port=8501
