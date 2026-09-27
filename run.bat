@echo off
chcp 65001 >nul
echo ========================================================
echo   國高中智慧學習雲端平台 (Smart EdTech Taiwan)
echo   高安全性・極簡無干擾・遊戲化・智慧考程・AI 家教
echo ========================================================
echo.
echo 正在啟動 FastAPI 核心伺服器 (http://127.0.0.1:8000)...
start http://127.0.0.1:8000
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
