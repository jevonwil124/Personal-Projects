import subprocess
import sys
import time
import os

def kill_opera_processes_background():
    """
    Continuously kills any running Opera processes using a PowerShell command.
    The script runs in the background (without a visible console window).
    """
    try:
        # Construct the PowerShell command.
        powershell_command = "Get-Process | Where-Object {$_.Name -eq 'opera'} | Stop-Process -Force"

        # Execute the PowerShell command.
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW  # Add this for background execution
        )

        # Log the output from PowerShell (for informational purposes).
        if process.stdout:
            with open("background_log.txt", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - PowerShell output:\n{process.stdout}\n")
        if process.stderr:
            with open("background_log.txt", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - PowerShell error output:\n{process.stderr}\n")

        with open("background_log.txt", "a") as f:
             f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Checked for and killed Opera processes (if any).\n")

    except subprocess.CalledProcessError as e:
        # Handle errors that occur during the execution of the PowerShell command.
        error_message = f"Error killing Opera processes: {e}\nPowerShell error output:\n{e.stderr}\n"
        print(error_message)  # Print to standard output (which may be captured if redirected)
        # Log the error
        with open("error_log.txt", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error: {error_message}\n")

    except Exception as e:
        # Handle other exceptions.
        error_message = f"An unexpected error occurred: {e}\n"
        print(error_message)
        with open("error_log.txt", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Unexpected error: {error_message}\n")
        time.sleep(5)

    # Wait for a short period before checking again.
    time.sleep(5)

def main():
    """
    Main function to run the background task.
    """
    # Create a log file at the start
    with open("background_log.txt", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Script started.\n")

    while True:
        kill_opera_processes_background()

if __name__ == "__main__":
    main()




