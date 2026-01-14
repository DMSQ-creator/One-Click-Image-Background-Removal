@echo off
:: 这里的 %~dp0 会自动获取当前这个文件所在的文件夹路径
cd /d "%~dp0"

echo Starting Streamlit...
streamlit run app_ultra_final.py

pause