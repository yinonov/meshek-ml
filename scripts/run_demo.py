"""Launch the demo dashboard."""


def main():
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "src/meshek_ml/demo/dashboard.py"],
        check=True,
    )


if __name__ == "__main__":
    main()
