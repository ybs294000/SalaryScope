@echo off

IF NOT EXIST venv (
    echo Virtual environment not found.
    echo Please run setup_salaryscope.bat first.
    pause
    exit /b
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Running SalaryScope using Python 3.13 environment...
streamlit run app_resume.py

pause
