#!/usr/bin/env python3
"""
EV Battery Health Prediction System Launcher
"""
from pathlib import Path
import os
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = ROOT_DIR / ".venv311" / "Scripts" / "python.exe"


def get_project_python():
    """Prefer the TensorFlow-compatible project venv when present."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def install_requirements():
    """Install project dependencies."""
    python_exe = get_project_python()
    print(f"Installing requirements with: {python_exe}")
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT_DIR)


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

    parser = argparse.ArgumentParser(description="EV Battery Health System")
    parser.add_argument("--install", action="store_true", help="Install dependencies")
    parser.add_argument("--backend", action="store_true", help="Run backend only")
    parser.add_argument("--train", action="store_true", help="Train model")

    args = parser.parse_args()

    if args.install:
        install_requirements()
    elif args.train:
        train_model()
    elif args.backend:
        run_backend()
    else:
        print("Run: python run.py --install")
        print("     python run.py --backend")
        print("     python run.py --train")
        print("Backend uses .venv311 automatically when available.")
        print("Frontend: Open http://127.0.0.1:5000/ after backend starts")
