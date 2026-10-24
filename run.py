#!/usr/bin/env python3
"""
EV Battery Health Prediction System Launcher
"""
from pathlib import Path
import os
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent
VENV_CANDIDATES = [
    ROOT_DIR / ".venv" / "Scripts" / "python.exe",
    ROOT_DIR / ".venv311" / "Scripts" / "python.exe",
]


def get_project_python():
    """Use the first usable project virtualenv, falling back to the active Python."""
    for venv_python in VENV_CANDIDATES:
        if venv_python.exists():
            try:
                res = subprocess.run([str(venv_python), "--version"], capture_output=True, text=True)
                if res.returncode == 0:
                    return str(venv_python)
            except Exception:
                pass
    return sys.executable


def install_requirements():
    """Install project dependencies."""
    python_exe = get_project_python()
    print(f"Installing requirements with: {python_exe}")
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT_DIR)


def run_tests():
    """Run full test suite (39 tests: 29 NLG unit tests + 10 API tests)."""
    python_exe = get_project_python()
    print(f"Running test suite with: {python_exe}")
    subprocess.call([python_exe, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT_DIR)


def run_evaluation():
    """Run NLG synthetic corpus evaluation."""
    python_exe = get_project_python()
    print(f"Running evaluation with: {python_exe}")
    subprocess.call([python_exe, "evaluation/evaluate.py"], cwd=ROOT_DIR)


def run_backend():
    """Run Flask backend."""
    python_exe = get_project_python()
    print(f"Starting backend with: {python_exe}")
    subprocess.call([python_exe, "backend/app.py"], cwd=ROOT_DIR)


def run_frontend():
    """Open frontend in browser."""
    print("Opening frontend...")
    os.system("start http://127.0.0.1:5000/")


def train_model():
    """Train model with the active project interpreter."""
    python_exe = get_project_python()
    print(f"Training model with: {python_exe}")
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", "model/requirements.txt"], cwd=ROOT_DIR)
    subprocess.check_call([python_exe, "model/train.py"], cwd=ROOT_DIR)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EV Battery Health System with NLG Reporting")
    parser.add_argument("--install", action="store_true", help="Install dependencies")
    parser.add_argument("--backend", action="store_true", help="Run backend only")
    parser.add_argument("--train", action="store_true", help="Train model")
    parser.add_argument("--test", action="store_true", help="Run test suite (39 unit/API tests)")
    parser.add_argument("--eval", action="store_true", help="Run synthetic evaluation script")

    args = parser.parse_args()

    if args.install:
        install_requirements()
    elif args.train:
        train_model()
    elif args.test:
        run_tests()
    elif args.eval:
        run_evaluation()
    elif args.backend:
        run_backend()
    else:
        print("Run:")
        print("  python run.py --backend  : Start Flask server & dashboard")
        print("  python run.py --test     : Run 39 automated unit & API tests")
        print("  python run.py --eval     : Run 10-scenario synthetic evaluation")
        print("  python run.py --install  : Install dependencies")
        print("  python run.py --train    : Train model")
        print("\nDashboard URL: http://127.0.0.1:5000/")
