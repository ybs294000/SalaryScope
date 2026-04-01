@echo off

echo Checking for Python 3.13...
py -3.13 --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python 3.13 is NOT installed.
    echo Please install Python 3.13 and try again.
    pause
    exit /b
)

echo Python 3.13 found.

echo Creating virtual environment using Python 3.13...
py -3.13 -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo Setup complete.
pause
