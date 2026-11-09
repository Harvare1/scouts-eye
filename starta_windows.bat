@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (echo Kunde inte installera beroenden. Kontrollera Python. & pause & exit /b 1)
echo.
echo Andrablicken startar lokalt pa http://127.0.0.1:8000
echo Tryck CTRL+C for att stoppa.
py -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
