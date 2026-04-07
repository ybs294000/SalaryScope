#!/bin/bash

echo "Checking for Python 3.13..."

if ! command -v python3.13 &> /dev/null
then
    echo "Python 3.13 is NOT installed."
    echo "Please install Python 3.13 and try again."
    exit 1
fi

echo "Python 3.13 found."

echo "Creating virtual environment using Python 3.13..."
python3.13 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete."