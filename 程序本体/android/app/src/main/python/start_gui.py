"""
AI Trading System - GUI Launcher
Simple launcher to avoid Chinese filename issues
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

# Import and run the main GUI program
from AI量化交易系统GUI import main

if __name__ == "__main__":
    main()