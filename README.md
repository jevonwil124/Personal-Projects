# Personal-Projects
This repository is for all my personal projects that will be created for resume building and technical interviewers.

Projects:
<details> 
  <summary>Remote Server Setup: Xubuntu, XRDP, SSH, and Tailscale</summary>
  
# Comprehensive Remote Server Setup: Xubuntu, XRDP, SSH, and Tailscale

This comprehensive guide covers the entire process of setting up a remote Xubuntu server, enabling secure SSH and RDP access both locally and externally using Tailscale. It includes specific troubleshooting steps for common graphical environment issues with XRDP.

## Table of Contents

1.  [Overview & Planning](#1-overview--planning)
2.  [Server OS Installation (Xubuntu Server)](#2-server-os-installation-xubuntu-server)
    * [Initial SSH Access during Installation](#initial-ssh-access-during-installation)
3.  [Basic Server Configuration](#3-basic-server-configuration)
    * [Update & Upgrade System](#update--upgrade-system)
    * [Install Xfce Desktop Environment](#install-xfce-desktop-environment)
4.  [Tailscale VPN Setup](#4-tailscale-vpn-setup)
    * [On the Xubuntu Server](#on-the-xubuntu-server)
    * [On the Client Machine (e.g., Debian Laptop)](#on-the-client-machine-eg-debian-laptop)
5.  [SSH Server Configuration](#5-ssh-server-configuration)
    * [Verify SSH Daemon Status](#verify-ssh-daemon-status)
    * [Configure SSH for Custom Port (Optional but Recommended)](#configure-ssh-for-custom-port-optional-but-recommended)
    * [Verify SSH Daemon Listening Ports](#verify-ssh-daemon-listening-ports)
6.  [XRDP (Remote Desktop) Installation & Configuration](#6-xrdp-remote-desktop-installation--configuration)
    * [Install XRDP](#install-xrdp)
    * [Configure User Session for Xfce](#configure-user-session-for-xfce)
    * [Modify XRDP Session Start Script](#modify-xrdp-session-start-script)
    * [XRDP Certificate Permissions Fix](#xrdp-certificate-permissions-fix)
    * [**Critical Fix: Using Xvfb Backend for Display**](#critical-fix-using-xvfb-backend-for-display)
7.  [Firewall Configuration (UFW)](#7-firewall-configuration-ufw)
8.  [Client-Side Setup (Remmina for RDP)](#8-client-side-setup-remmina-for-rdp)
9.  [Testing & Access](#9-testing--access)
    * [SSH Access](#ssh-access)
    * [RDP Access](#rdp-access)
10. [Troubleshooting Common Issues](#10-troubleshooting-common-issues)

---

## 1. Overview & Planning

This guide will walk you through setting up a dedicated Xubuntu server for remote access. We will use:

* **Xubuntu Server:** A lightweight, stable Linux distribution suitable for servers.

* **Xfce Desktop Environment:** A low-resource, graphical desktop environment for remote RDP access.

* **OpenSSH Server:** For secure command-line access.

* **XRDP:** For Remote Desktop Protocol (graphical) access.

* **Tailscale:** A zero-configuration VPN that creates a secure private network between your devices, allowing seamless access whether you are on the local network or across the internet.

## 2. Server OS Installation (Xubuntu Server)

Install Xubuntu Server on your hardware. During the installation process, pay attention to the following:

* **Network Configuration:** Configure your server's network settings (DHCP is usually fine for home use).

* **User Setup:** Create a standard user (e.g., `jw`) and set a strong password. You will use this user for both SSH and RDP.

* **Install OpenSSH server:** This is **critical** for remote command-line access. Ensure you select the option to install the OpenSSH server during the installation process.

### Initial SSH Access during Installation

Once the server finishes installing and reboots, you should be able to SSH into it from your local network (e.g., from your Debian laptop).

**On your Client Machine (e.g., Debian Laptop):**

1.  **Find your server's local IP address:** You can find this on your server by running `ip a` or checking your router's connected devices list. Let's assume it's `192.168.1.153`.

2.  **SSH into the server:**

    ```bash
    ssh your_username@192.168.1.153
    # e.g., ssh jw@192.168.1.153
    ```

    You will be prompted for your user password. If this works, your basic SSH setup is good. Keep this SSH session open for subsequent steps.

## 3. Basic Server Configuration

### Update & Upgrade System

Always start by ensuring your system is up-to-date.

**On your Xubuntu Server (via SSH):**

```bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y
```

Install Xfce Desktop Environment
If you installed Xubuntu Server, Xfce is likely already present. If you installed a minimal Ubuntu Server, install Xfce now.

On your Xubuntu Server (via SSH):

```bash
sudo apt install -y xubuntu-desktop
```
This package pulls in the full Xfce desktop experience.

# 4. Tailscale VPN Setup
Tailscale simplifies secure remote access by creating a private network over the internet.

On the Xubuntu Server
On your Xubuntu Server (via SSH):

Install Tailscale:

```bash

curl -fsSL [https://tailscale.com/install.sh](https://tailscale.com/install.sh) | sh
```
Authenticate Tailscale:

```bash

sudo tailscale up
```

This will output a unique URL (e.g., https://login.tailscale.com/a/a3761a801e006).

Copy this URL.

On your client machine (e.g., Debian laptop), open a web browser and paste the URL.

Follow the prompts to log in to your Tailscale account and authorize the server to join your Tailnet.

Verify Tailscale status:

```bash

sudo tailscale status
```
Note the Tailscale IP address assigned to your Xubuntu server (it will start with 100.). This is the IP you will use for remote access.

On the Client Machine (e.g., Debian Laptop)
On your Debian Laptop (in a new terminal, not your SSH session to the server):

Install Tailscale:

```bash

curl -fsSL [https://tailscale.com/install.sh](https://tailscale.com/install.sh) | sh
```
Authenticate Tailscale:

```bash

sudo tailscale up
```
This will also output a URL. Open it in your web browser and authorize your laptop.

Verify Tailscale status:

```bash

tailscale status
```
Confirm both your laptop and the Xubuntu server are listed as active in your Tailnet.

# 5. SSH Server Configuration
While SSH is typically installed with Xubuntu Server, you might have configured a custom port. Tailscale allows connections to any port open on the server, but it's good to verify SSH is listening correctly.

Verify SSH Daemon Status
On your Xubuntu Server (via SSH):

```bash

sudo systemctl status ssh
```
Ensure it shows Active: active (running). If not, start it:

```bash

sudo systemctl start ssh
sudo systemctl enable ssh
```
Configure SSH for Custom Port (Optional but Recommended)
If you wish to use a port other than the default 22 for SSH, configure it now.

On your Xubuntu Server (via SSH):

Edit sshd_config:

```bash

sudo nano /etc/ssh/sshd_config
```
Find the line #Port 22. Uncomment it (remove #) and change 22 to your desired port (e.g., 22022). You can also add another Port line if you want to listen on multiple ports.

```ini, TOML

Port 22022 # Your custom port
#Port 22   # Keep if you want default too
```
Save and exit (Ctrl+O, Enter, Ctrl+X).

Restart SSH service:

```bash

sudo systemctl restart ssh
```
Verify SSH Daemon Listening Ports
On your Xubuntu Server (via SSH):

```bash

sudo ss -tlpn | grep sshd
```
Look for lines like 0.0.0.0:22022 or 0.0.0.0:22 to confirm sshd is listening on the correct ports.

# 6. XRDP (Remote Desktop) Installation & Configuration
Install XRDP
On your Xubuntu Server (via SSH):

```bash

sudo apt install -y xrdp
```
Configure User Session for Xfce
Tell XRDP to explicitly start your Xfce session.

On your Xubuntu Server (via SSH):

Create/Edit ~/.xsession file:

```bash

echo "xfce4-session" > ~/.xsession
```
Make ~/.xsession executable:

```bash

chmod +x ~/.xsession
```
Modify XRDP Session Start Script
Ensure XRDP prioritizes running your .xsession file.

On your Xubuntu Server (via SSH):

Backup the original startwm.sh:

```bash

sudo cp /etc/xrdp/startwm.sh /etc/xrdp/startwm.sh.bak
```
Edit startwm.sh:

```bash

sudo nano /etc/xrdp/startwm.sh
```
Find the lines at the end of the script:

```bash

test -x /etc/X11/Xsession && exec /etc/X11/Xsession
exec /bin/sh /etc/X11/Xsession
```
Replace those two lines with this block:

```bash

# Prioritize user's .xsession
if [ -x "$HOME/.xsession" ]; then
  exec "$HOME/.xsession"
fi

# Fallback to the default Xsession if ~/.xsession is not found or not executable
test -x /etc/X11/Xsession && exec /etc/X11/Xsession
exec /bin/sh /etc/X11/Xsession
```
Save the file (Ctrl+O, Enter, Ctrl+X).

XRDP Certificate Permissions Fix
Correct permissions for xrdp's private key to avoid TLS warnings.

On your Xubuntu Server (via SSH):

```bash

sudo chmod 440 /etc/xrdp/key.pem
sudo chown root:xrdp /etc/xrdp/key.pem
sudo adduser xrdp ssl-cert
```
(The adduser command might indicate the user is already a member, which is fine.)

Critical Fix: Using Xvfb Backend for Display
If you encounter black screens or immediate disconnections after XRDP login (often due to graphics driver issues like missing /dev/dri/card0), this is the solution. Xvfb creates a virtual display, bypassing your physical GPU.

On your Xubuntu Server (via SSH):

Stop the xrdp service:

```bash

sudo systemctl stop xrdp
```
Install xvfb and x11-xserver-utils:

```bash

sudo apt update
sudo apt install -y xvfb x11-xserver-utils
```
Edit /etc/xrdp/xrdp.ini:

```bash

sudo nano /etc/xrdp/xrdp.ini
```
Comment out the [Xorg] section entirely. Place a semicolon ; at the beginning of every line in the [Xorg] section, including the [Xorg] header itself.

```ini, TOML

;[Xorg]
;name=Xorg
;lib=libxup.so
;username=ask
;password=ask
;ip=127.0.0.1
;port=-1
;param=-depth 24
;#xserver=-1
;#delay_ms=2000
```
Add or modify an [Xvfb] section. Scroll to the end of the file or find an existing [Xvnc] / [Xvfb] block. Add or configure it like this:

```ini, TOML

[Xvfb]
name=Xvfb
lib=libxup.so
username=ask
password=ask
ip=127.0.0.1
port=-1
# Configure resolution and color depth for the virtual display
param=-s 1920x1080 -depth 24 -nolisten tcp +extension GLX +extension RANDR +extension RENDER
# You can adjust '1920x1080' to your preferred resolution.
#xserver=/usr/bin/Xvfb
#delay_ms=2000
```
Save the file (Ctrl+O, Enter, Ctrl+X).

Restart the xrdp service:

```bash

sudo systemctl restart xrdp
```
# 7. Firewall Configuration (UFW)
Configure your server's firewall to allow SSH and RDP connections. UFW (Uncomplicated Firewall) is recommended.

On your Xubuntu Server (via SSH):

Allow SSH:

```bash

sudo ufw allow ssh
```
# If you changed SSH port to 22022, use:
# sudo ufw allow 22022/tcp
Allow XRDP:

```bash

sudo ufw allow 3389/tcp
```
Enable the firewall (if not already enabled):

```bash

sudo ufw enable
```
Confirm with y if prompted.

Check firewall status:

```bash

sudo ufw status
```
You should see rules for your configured SSH port and 3389/tcp listed as ALLOW.

# 8. Client-Side Setup (Remmina for RDP)
Remmina is a popular RDP client for Linux.

On your Debian Laptop:

Install Remmina (if not already installed):

```bash

sudo apt install -y remmina remmina-plugin-rdp
```
Open Remmina: Find it in your applications menu or run remmina from the terminal.

Create a New Connection Profile:

Click the + icon or File > New Connection Profile.

Name: Give it a descriptive name (e.g., "Xubuntu Server Tailscale RDP").

Protocol: Select RDP - Remote Desktop Protocol.

Server: Enter the Tailscale IP address of your Xubuntu server (e.g., 100.70.160.6).

Port: This should automatically populate to 3389. If not, manually set it to 3389.

Username: Your Xubuntu username (e.g., jw).

Password: Your Xubuntu user's password.

Resolution Tab: You can set a custom resolution here if desired.

SSH Tunnel Tab: Ensure "Enable SSH tunnel" is UNCHECKED. Tailscale handles the secure connection; Remmina's SSH tunnel is not needed.

Save and Connect: Click "Save and Connect".

Accept Certificate: The first time, you might be prompted to accept a self-signed certificate. Click "Accept" or "Always accept".

XRDP Login Screen: You will then see the xrdp login screen (typically a grey background with "Xorg" or "Xvfb" and username/password fields). Enter your Xubuntu username and password again here.

You should now see your Xfce desktop environment!

# 9. Testing & Access
SSH Access
On your Client Machine (e.g., Debian Laptop):

```bash

# If using default SSH port 22:
ssh your_username@<Xubuntu_Tailscale_IP_Address>

# If using custom SSH port (e.g., 22022):
ssh -p 22022 your_username@<Xubuntu_Tailscale_IP_Address>

# Example for user 'jw' and IP '100.70.160.6' with custom port 22022:
ssh -p 22022 jw@100.70.160.6
You will be prompted for your user password. This connection is now secured and routed via Tailscale, working from anywhere with internet access.
```
**RDP Access**
On your Client Machine (e.g., Debian Laptop):

Launch Remmina and connect using the profile you configured. This RDP connection is also secured and routed via Tailscale, working from anywhere with internet access.

# 10. Troubleshooting Common Issues
Tailscale command not found on client/server:

This happens if the snapd path isn't updated. Try logging out and back in to your terminal session.

Alternatively, use the full path to the Tailscale executable, e.g., sudo /snap/bin/tailscale up or sudo /snap/tailscale/current/bin/tailscale up.

"Connection refused" when SSHing or RDPing:

Ensure the Xubuntu server is powered on and fully booted.

Verify sshd (for SSH) and xrdp (for RDP) services are active (running) on the server:

```bash

sudo systemctl status ssh
sudo systemctl status xrdp
```
Verify sshd is listening on the correct port: sudo ss -tlpn | grep sshd.

Check ufw status on the server to ensure ports are open.

Confirm Tailscale is active on both client and server: sudo tailscale status.

Black screen or immediate disconnect after RDP login:

This is typically a desktop environment startup issue within XRDP.

Recheck ~/.xsession content: It should ONLY be xfce4-session. (echo "xfce4-session" > ~/.xsession followed by chmod +x ~/.xsession)

Verify /etc/xrdp/startwm.sh correctly executes ~/.xsession (see section 5.2).

Crucially, ensure Xvfb is configured correctly in /etc/xrdp/xrdp.ini (Section 6.4) and that the [Xorg] section is commented out.

Check ~/.xsession-errors on the server for any messages logged during the failed session attempt.

Check xrdp logs: sudo journalctl -u xrdp.service -f (while trying to connect).

Permission denied for /etc/xrdp/key.pem:

Run:

```bash

sudo chmod 440 /etc/xrdp/key.pem
sudo chown root:xrdp /etc/xrdp/key.pem
sudo adduser xrdp ssl-cert
sudo systemctl restart xrdp
```
Slow RDP performance:

Expected when using Xvfb as it lacks hardware acceleration.

Consider lowering the resolution in the [Xvfb] section's param line in /etc/xrdp/xrdp.ini (e.g., -s 1280x720).


</details>

<details>

<summary>Cybersecurity Attack Script: Opera-Triggered Credential Harvester</summary>

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
In summary, this script exhibits behaviors consistent with a malicious tool designed to gain unauthorized access by changing user credentials, stealing them, and potentially disrupting the target system. Its multi-platform capabilities and attempts at stealth (process termination, log removal) further underscore its malicious intent.More actions
</details>


**Weather App**:
Front-end code (HTML, CSS, and JavaScript) for a functional weather application that allows users to search for a city and see its current weather conditions, fetching the data from the OpenWeatherMap API and updating the page dynamically.

**Seacrh Bar**:
A simple search bar that allows that user to search anything via google.com




