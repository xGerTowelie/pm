#!/bin/bash

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Compile the Python project with PyInstaller
pyinstaller --onefile fm.py

# Deactivate the virtual environment
deactivate

