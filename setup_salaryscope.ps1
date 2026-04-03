Write-Host "Checking for Python 3.13..."

py -3.13 --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.13 is NOT installed."
    Write-Host "Please install Python 3.13 and try again."
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "Python 3.13 found."

Write-Host "Creating virtual environment using Python 3.13..."
py -3.13 -m venv venv

Write-Host "Activating virtual environment..."
& "venv\Scripts\Activate.ps1"

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host "Setup complete."
Read-Host "Press Enter to continue"