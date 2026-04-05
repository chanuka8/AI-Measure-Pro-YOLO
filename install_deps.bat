@echo off
REM ===========================================
REM AI MEASURE PRO - SAFE DEPENDENCY INSTALLER
REM ===========================================

echo Activating virtual environment...
call "venv\Scripts\activate.bat"

echo.
echo Installing dependencies from requirements.txt...
echo ⚠️  This will install compatible versions only!
echo.
pip install -r requirements.txt

echo.
echo ✅ Dependencies installed successfully!
echo.
echo To run the app:
echo python app.py
echo.
pause