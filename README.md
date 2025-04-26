# Personal-Projects
This repository is for all my personal projects that will be created for resume building and technical interviewers.

Projects:

<details> 
<summary>**Cybersecurity Attack Script: Opera-Triggered Credential Harvester**</summary>

This Python script appears to be designed for malicious activities, specifically targeting a system to change user passwords, log these new passwords, and then attempt to transmit them to a remote listener before restarting the computer and cleaning up the log file.

***Password Manipulation***: The script contains functions (change_user_credentials) to change the passwords of specified users on Linux, Windows, and macOS. This is a significant security risk as it can lock legitimate users out of their accounts. It attempts to change the password of the current user and the administrator/root user.
***Browser Monitoring and Termination***: The script monitors for common web browser processes (wait_for_browser_running) and has the capability to terminate them (kill_browser). This might be done to disrupt user activity or as a precursor to other malicious actions.
Credential Logging: The script generates random passwords and logs the new usernames and passwords to a local file (new_credentials.txt) using the log_all_credentials function. This creates a record of the compromised credentials.
***Data Exfiltration (Attempted)***: The script attempts to connect to a specified IP address and port (TARGET_IP_ADDRESS, TARGET_PORT) and send the logged credential file to this remote listener. This indicates an attempt to exfiltrate the compromised information to an attacker-controlled machine.
System Disruption: The script includes functionality to restart the computer (attacker_main). This could be done to finalize changes, cover tracks, or further disrupt the user's access.

***Privilege Escalation (Implicit)***: The script checks for and requires administrator/root privileges to successfully change passwords on the target system. This implies an assumption that the script will be run with elevated permissions, possibly through exploitation of vulnerabilities or social engineering.
OS-Specific Targeting: The script uses sys.platform to adapt its commands for different operating systems (Windows, Linux, macOS) for password changes, process management, and shutdown/restart, making it more versatile.

***Cleanup (Log Removal)***: After attempting to send the credentials, the script tries to delete the log file (os.remove(credentials_file)), likely to remove evidence of its actions.

***Listener Mode***: The script has a LISTENER_MODE. If enabled, it sets up a socket listener on the specified port to receive the transmitted credential file. This indicates a coordinated attack where one machine runs this script to compromise the target, and another listens to receive the stolen data.
In summary, this script exhibits behaviors consistent with a malicious tool designed to gain unauthorized access by changing user credentials, stealing them, and potentially disrupting the target system. Its multi-platform capabilities and attempts at stealth (process termination, log removal) further underscore its malicious intent.
</details>


**Weather App**:
Front-end code (HTML, CSS, and JavaScript) for a functional weather application that allows users to search for a city and see its current weather conditions, fetching the data from the OpenWeatherMap API and updating the page dynamically.

**Seacrh Bar**:
A simple search bar that allows that user to search anything via google.com




