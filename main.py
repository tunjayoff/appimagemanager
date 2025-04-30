#!/usr/bin/env python3
"""
Entry point for the appimagemanager application.
Run this script with `python3 main.py` from the project root to start the GUI.
"""
import os, sys
# Ensure project root is in sys.path for package imports
sys.path.insert(0, os.path.dirname(__file__))
from appimagemanager.main import main

if __name__ == "__main__":
    main() 