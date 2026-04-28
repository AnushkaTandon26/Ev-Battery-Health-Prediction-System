import argparse

def main():
    parser = argparse.ArgumentParser(description="EV Battery Health Prediction System")
    parser.add_argument("--backend", action="store_true", help="Start Flask backend")
    args = parser.parse_args()
    if args.backend:
        print("Starting backend...")

if __name__ == "__main__":
    main()
