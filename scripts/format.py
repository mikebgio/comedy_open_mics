#!/usr/bin/env python3
"""
Simple formatting script using Black
"""
import os
import subprocess
import sys


def run_black():
    """Run Black formatter on Python files"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", "--line-length=88", "."],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ Black formatting completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Black formatting failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def run_isort():
    """Run isort import sorting"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "isort", "--profile=black", "."],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ Import sorting completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Import sorting failed: {e}")
        return False


if __name__ == "__main__":
    print("Running code formatting...")
    success = True

    if not run_isort():
        success = False

    if not run_black():
        success = False

    if success:
        print("All formatting completed successfully!")
    else:
        print("Some formatting tasks failed")
        sys.exit(1)
