if (!(Test-Path "venv")) {
    Write-Host "Virtual environment not found."
    Write-Host "Please run setup_salaryscope.bat first."
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "Activating virtual environment..."
& "venv\Scripts\Activate.ps1"

Write-Host "Running SalaryScope using Python 3.13 environment..."
streamlit run app_resume.py

Read-Host "Press Enter to continue"