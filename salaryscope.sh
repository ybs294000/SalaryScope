#!/bin/bash

if [ ! -d "venv" ]; then
    echo "Virtual environment not found."
    echo "Please run salaryscope_setup.sh first."
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Running SalaryScope using Python 3.13 environment..."
streamlit run app_resume.py