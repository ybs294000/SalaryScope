#!/bin/bash

echo "Checking Python 3.13..."

if ! command -v python3.13 &> /dev/null
then
    echo "Python 3.13 not found. Please install it."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.13 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running SalaryScope..."
streamlit run app.py
