\
@echo off
REM Staybnb - démarrage facile (Windows)
setlocal
echo === Staybnb (Windows) ===
where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
  echo Erreur : Python n'est pas installe ou non detecte.
  echo Installe Python 3.10+ depuis https://www.python.org/downloads/ (coche "Add Python to PATH").
  pause
  exit /b 1
)
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python app.py
pause
