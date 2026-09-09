@echo off
chcp 65001 > nul
echo 사주 프로그램을 시작합니다...
cd /d "%~dp0"
streamlit run dabdab_saju_app.py
pause
