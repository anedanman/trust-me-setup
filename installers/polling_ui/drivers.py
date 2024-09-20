import subprocess
import sys
import platform


def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)

    if res.returncode != 0:
        print(f"Error: {res.stderr}")
        sys.exit(res.returncode)

    else:
        print(res.stdout)


def set_drivers():
    os_type = platform.system()

    if os_type.lower() == "windows":
        try:
            run_cmd("choco install libusb hidapi -y")
        except:
            print(
                "Choco not found. Please install Choco manually from https://chocolatey.org/install"
            )
    elif os_type.lower() == "darwin":  # macOS
        run_cmd("brew install libusb hidapi")
    elif os_type.lower() == "linux":
        run_cmd("sudo apt-get install libusb-1.0.0-dev libhidapi-hidraw0")
    else:
        print(f"Unsupported OS: {os_type}")
        sys.exit(1)

    print("Driver setup complete")
