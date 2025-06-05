# Personal-Projects
This repository is for all my personal projects that will be created for resume building and technical interviewers.

Projects:
<details> 
  <summary>Personal VPN</summary>
  
# OpenVPN Server & Client Setup Guide
This guide details the steps taken to set up a personal OpenVPN server on Debian 12 and configure a client on a Debian 12 KDE Plasma desktop. This setup allows for secure, encrypted internet traffic routing through your home network, effectively creating your own private VPN.
# 1. Introduction
   A Virtual Private Network (VPN) creates a secure tunnel over an insecure network (like the internet), allowing you to access resources as if you were directly connected to the private network. This guide focuses on OpenVPN, a robust and flexible open-source VPN solution, providing you with full control over your privacy and network access. Goal: To establish a working OpenVPN server on a dedicated Debian 12 machine (your_server_internal_ip - e.g., 186.65.2.788) and connect to it from another Debian 12 KDE Plasma client, routing all client internet traffic through the server.
# 2. Prerequisites
  Before you begin, ensure you have:
    Two Debian 12 Machines: 
      Server: A dedicated machine (e.g., a Raspberry Pi, old PC, or VM) with a static internal IP address (e.g., your_server_internal_ip). This machine should be connected to your home network.
      Client: Your Debian 12 KDE Plasma desktop.
      Root/Sudo Access: For both machines.
      Internet Access: For both machines during setup.
      Router Access: You will need access to your home router's administration interface to configure port forwarding.Basic Linux Command Line Knowledge.
# 3. OpenVPN Server Setup (Debian 12 - your_server_internal_ip)
This section covers setting up the OpenVPN server, including its Public Key Infrastructure (PKI), configuration, and firewall rules.

**3.1 Initial System SetupUpdate your system:**

        `sudo apt update
         sudo apt upgrade -y`

Install necessary packages:
`sudo apt install -y openvpn easy-rsa ufw net-tools`

**3.2 Public Key Infrastructure (PKI) with Easy-RSA**
OpenVPN uses certificates to authenticate the server and clients. Easy-RSA is a tool to manage this PKI.Copy Easy-RSA to a working directory:
      `make-cadir ~/easy-rsa`
      `cd ~/easy-rsa`

Initialize the PKI: `./easyrsa init-pki`

Build the Certificate Authority (CA): `./easyrsa build-ca nopass`

You'll be prompted for a Common Name (CN) for your CA. This can be anything (e.g., MyOpenVPN-CA).Generate the Server Certificate and Key: `./easyrsa gen-req server nopass`

You'll be prompted for a Common Name (CN) for the server. It's recommended to use server for clarity.Sign the Server Certificate Request: `./easyrsa sign-req server server`

Confirm the signing by typing yes.Generate Diffie-Hellman Parameters:
This generates strong cryptographic parameters for key exchange. This step can take a significant amount of time (10-20 minutes or more). `./easyrsa gen-dh`

Generate a TLS Authentication Key (HMAC signature):
This adds an extra layer of security against DoS attacks and UDP port flooding. `openvpn --genkey --secret pki/ta.key`

**3.3 Copy PKI Files to OpenVPN Directory**
Move the generated keys and certificates to the OpenVPN configuration directory.
    `sudo cp pki/ca.crt /etc/openvpn/server/
    sudo cp pki/issued/server.crt /etc/openvpn/server/
    sudo cp pki/private/server.key /etc/openvpn/server/
    sudo cp pki/dh.pem /etc/openvpn/server/
    sudo cp pki/ta.key /etc/openvpn/server/`

**3.4 OpenVPN Server Configuration (server.conf)**
Create the server configuration file.Create the configuration file:

`sudo nano /etc/openvpn/server/server.conf`

Paste the following content into the file:
    `#OpenVPN Server Configuration
     #Running on Debian 12
    
    #Protocol & Port: Using TCP on port 8443 for better firewall traversal.
    #This was changed from UDP 1194 due to Verizon Fios router issues.
    port 8443
    proto tcp
    dev tun
    
    #PKI Configuration
    #Certificate Authority (CA) certificate
    ca /etc/openvpn/server/ca.crt
    #Server certificate
    cert /etc/openvpn/server/server.crt
    #Server private key
    key /etc/openvpn/server/server.key
    #Diffie-Hellman parameters for key exchange
    dh /etc/openvpn/server/dh.pem
    #TLS-Auth key for HMAC signature (extra layer of security)
    tls-auth /etc/openvpn/server/ta.key 0
    
    #Tunnel Network Configuration
    #VPN tunnel IP address range
    server 10.8.0.0 255.255.255.0
    #Push DNS servers to clients (Google DNS in this case)
    push "dhcp-option DNS 8.8.8.8"
    push "dhcp-option DNS 8.8.4.4"
    #Redirect all client traffic through the VPN
    push "redirect-gateway def1 bypass-dhcp"
    
    #Client-related settings
    #Allow clients to talk to each other (optional)
    client-to-client
    #Persist tunnel device and key, avoid some reinstalls
    persist-tun
    persist-key
    
    #Security & User
    #Run as a non-privileged user after initialization
    user nobody
    group nogroup
    
    #Logging & Verbosity
    status /var/log/openvpn/openvpn-status.log
    log /var/log/openvpn/openvpn.log
    verb 3 # Verbosity level (3 is good for production, 4 for debug)
    #Silence repeated messages
    mute 20
    
    #Compression (older method, optional, modern OpenVPN often uses --compress)
    #comp-lzo
    
    #Keepalive ensures connection stays alive
    keepalive 10 120
    
    #Cipher Configuration: IMPORTANT for client compatibility.
    #This was a crucial fix for client connection issues.
    #Specifies data ciphers the server will use.
    #Client must also support these or auto-negotiate compatible.
    data-cciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305`

Create the log directory:
`sudo mkdir -p /var/log/openvpn/`

Save and exit (Ctrl+X, then Y, then Enter).

**3.5 Firewall Configuration (UFW) on ServerConfigure the server's firewall to allow OpenVPN traffic and forward client traffic.**
Allow SSH and OpenVPN incoming traffic:
  `sudo ufw allow 22/tcp comment 'Allow SSH traffic'
  sudo ufw allow 8443/tcp comment 'Allow OpenVPN traffic'`

Enable IP Forwarding in the kernel:
Open the sysctl configuration file:
`sudo nano /etc/sysctl.conf`

Find the line #net.ipv4.ip_forward=1 and uncomment it (remove the #).
Save and exit (Ctrl+X, then Y, then Enter).
Apply the change immediately:
`sudo sysctl -p`

Configure NAT (Network Address Translation) for outgoing traffic:
Open UFW's before.rules file:
`sudo nano /etc/ufw/before.rules`

Add the following lines at the very top of the file, before the *filter line. Adjust your_server_network_interface if your server's public-facing network interface is different (e.g., eth0 or enp0s3).
`# START OPENVPN RULES
# NAT table rules
*nat
:POSTROUTING ACCEPT [0:0]
# Allow VPN clients to access the Internet
-A POSTROUTING -s 10.8.0.0/24 -o your_server_network_interface -j MASQUERADE
COMMIT
# END OPENVPN RULES
`

Save and exit.Configure UFW to allow forwarded packets:
Open the UFW default configuration:
`sudo nano /etc/default/ufw`

Find the line DEFAULT_FORWARD_POLICY="DROP" and change it to DEFAULT_FORWARD_POLICY="ACCEPT".
Save and exit.
Enable and reload UFW:
`sudo ufw enable
sudo ufw reload`

You might be warned about SSH connections. Confirm by typing y.

**3.6 Start and Enable OpenVPN Service**

Start the OpenVPN service: `sudo systemctl start openvpn-server@server`

The @server part tells it to use server.conf.

Enable OpenVPN to start on boot: `sudo systemctl enable openvpn-server@server`

Check OpenVPN status: `sudo systemctl status openvpn-server@server`

It should show active (running).

# 4. Client Configuration Generation (on Server)

Now, generate the client certificate and a ready-to-use .ovpn configuration file.

**4.1 Generate Client Certificate and KeyReturn to the easy-rsa directory on the server:**
`cd ~/easy-rsa`

Generate a new client request and key (replace client1 with a descriptive name like your_client_name):
`./easyrsa gen-req client1 nopass`

Sign the client certificate request:
`./easyrsa sign-req client client1`

Confirm by typing yes.

**4.2 Create Client Configuration File (client1.ovpn)**
This file contains all the necessary information for the client to connect.Create a directory for client configs:
`mkdir -p ~/client-configs/files
chmod 700 ~/client-configs/files`

Create a base client configuration file:
`nano ~/client-configs/base.conf`

Paste the following content:

`# OpenVPN Client Base Configuration

# Client-side configuration
client
dev tun
proto tcp

# Public IP and Port of your OpenVPN server
# Replace your_server_public_ip_or_ddns_hostname with your actual public IP or Dynamic DNS hostname
remote your_server_public_ip_or_ddns_hostname 8443
# Connect randomly to one of the remote addresses (if multiple are listed)
remote-random

# General configuration
resolv-retry infinite
nobind
persist-key
persist-tun

# Security configuration
# Server CA certificate (will be embedded)
# ca ca.crt
# Client certificate (will be embedded)
# cert client1.crt
# Client private key (will be embedded)
# key client1.key
# TLS-Auth key (will be embedded)
# tls-auth ta.key 1

# Cipher Configuration: Must match or be compatible with server's data-ciphers.
# This was a crucial fix for client connection issues.
data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305

# Compression (if used on server)
# comp-lzo no

# Verbosity level
verb 3
mute 20
`

IMPORTANT: Replace your_server_public_ip_or_ddns_hostname with your actual public IP address (the one you get from whatismyip.com when not on VPN) or your Dynamic DNS hostname if you set one up. This is the address your clients will use to reach your router.Save and exit.Create a script to generate client .ovpn files:
`nano ~/client-configs/make_config.sh`

Paste the following content:
`#!/bin/bash

# OpenVPN Client Configuration Generator
# This script collects the necessary certificates and keys
# and embeds them into a single .ovpn file for easy client distribution.

# Check if a client name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <client_name>"
    exit 1
fi

CLIENT_NAME="$1"
# EASY_RSA_DIR is located in the user's home directory
EASY_RSA_DIR="$HOME/easy-rsa"
# CLIENT_CONFIGS_DIR is located in the user's home directory
CLIENT_CONFIGS_DIR="$HOME/client-configs"

echo "Generating client configuration for $CLIENT_NAME..."

# Verify all necessary files and directories exist before proceeding
# The script should be run from a user account with read access to these files.
# If run as root (sudo -i), ~ will refer to /root, so paths need to be adjusted or files copied.
# For simplicity, ensure EASY_RSA_DIR and CLIENT_CONFIGS_DIR are accessible from where this script is run.

if [ ! -f "${CLIENT_CONFIGS_DIR}/base.conf" ]; then
    echo "Error: base.conf not found at ${CLIENT_CONFIGS_DIR}/base.conf"
    exit 1
fi
if [ ! -f "${EASY_RSA_DIR}/pki/ca.crt" ]; then
    echo "Error: ca.crt not found at ${EASY_RSA_DIR}/pki/ca.crt"
    exit 1
fi
if [ ! -f "${EASY_RSA_DIR}/pki/issued/${CLIENT_NAME}.crt" ]; then
    echo "Error: Client certificate not found at ${EASY_RSA_DIR}/pki/issued/${CLIENT_NAME}.crt"
    exit 1
fi
if [ ! -f "${EASY_RSA_DIR}/pki/private/${CLIENT_NAME}.key" ]; then
    echo "Error: Client key not found at ${EASY_RSA_DIR}/pki/private/${CLIENT_NAME}.key"
    exit 1
fi
# ta.key is copied to /etc/openvpn/server/
if [ ! -f "/etc/openvpn/server/ta.key" ]; then
    echo "Error: ta.key not found at /etc/openvpn/server/ta.key"
    exit 1
fi
if [ ! -d "${CLIENT_CONFIGS_DIR}/files" ]; then
    echo "Error: Output directory not found at ${CLIENT_CONFIGS_DIR}/files"
    exit 1
fi


cat "${CLIENT_CONFIGS_DIR}/base.conf" \
    <(echo -e '<ca>') \
    "${EASY_RSA_DIR}/pki/ca.crt" \
    <(echo -e '</ca>\n<cert>') \
    "${EASY_RSA_DIR}/pki/issued/${CLIENT_NAME}.crt" \
    <(echo -e '</cert>\n<key>') \
    "${EASY_RSA_DIR}/pki/private/${CLIENT_NAME}.key" \
    <(echo -e '</key>\n<tls-auth>') \
    "/etc/openvpn/server/ta.key" \
    <(echo -e '</tls-auth>') \
    > "${CLIENT_CONFIGS_DIR}/files/${CLIENT_NAME}.ovpn"

echo "Client configuration for $CLIENT_NAME generated at: ${CLIENT_CONFIGS_DIR}/files/${CLIENT_NAME}.ovpn"
echo "Remember to secure this file as it contains your client's credentials."
`
Save and exit.Make the script executable: `chmod +x ~/client-configs/make_config.sh`

**4.3 Generate the First Client FileRun the script:cd ~/client-configs**
./make_config.sh client1

This will create ~/client-configs/files/client1.ovpn.Copy the .ovpn file to your user's home directory (for easier scp): `cp ~/client-configs/files/client1.ovpn ~/`

# 5. Client Setup (Debian 12 KDE Plasma Desktop)

This section details how to set up the OpenVPN client on your KDE Plasma desktop.

**5.1 Transfer the Client Configuration File**

On your KDE Plasma desktop, open a terminal.Use scp to copy the .ovpn file from the server to your desktop:

`scp your_username@your_server_internal_ip:~/client-configs/files/client1.ovpn ~/Downloads/`

You will be prompted for your server user (your_username) password.

**5.2 Install NetworkManager OpenVPN Plugin**

KDE Plasma uses NetworkManager for network connections.Install the NetworkManager OpenVPN plugin:

`sudo apt install -y network-manager-openvpn-gnome`

Even though it says -gnome, it works perfectly with KDE Plasma's NetworkManager.

Restart NetworkManager (or reboot): `sudo systemctl restart NetworkManager`

A full reboot is often simpler and ensures everything is refreshed.

**5.3 Import OpenVPN Connection in KDE Plasma**

Click on the Network icon in your KDE Plasma system tray.

Go to "Configure Network Connections..."
In the Network Connections window, click the "+" button to add a new connection.
Choose "Import VPN connection..."
Navigate to ~/Downloads/ and select the client1.ovpn file you copied.
Click "Open".
Review the settings:
The Connection name will default to client1. You can change this.The Gateway (your server's public IP), Authentication Type (Certificates (TLS)), CA Certificate, User Certificate, and Private Key should all be automatically populated from the .ovpn file.
Crucial: 
  Data Ciphers: Go to the "Advanced..." settings button. In the "Advanced VPN Options" window, go to the "Security" tab. Ensure the Cipher dropdown is set to a compatible cipher, or that data-       ciphers from server.conf are implicitly handled.
Important Fix: For specific client compatibility (as encountered during troubleshooting), you might need to manually ensure data-ciphers are explicitly set on the client. In KDE's NetworkManager, this might involve checking a "Ciphers" or "Advanced" section. The client1.ovpn file created above includes the data-ciphers line, and NetworkManager should pick it up. If issues arise, double-check that AES-256-GCM or AES-128-GCM is selected/enabled.
Click "OK" to save the advanced settings, then "Apply" to save the new VPN connection.

**5.4 Connect to the VPN**
Click on the Network icon in your KDE Plasma system tray again.You should now see client1 (or whatever you named it) under your VPN connections.Click on it to connect.The icon should change, and you should see a connection notification.

**5.5 Verify ConnectionOpen a web browser (on your KDE Plasma desktop).**
Go to whatismyip.com or ipchicken.com.The IP address displayed should now be your_server_public_ip_or_ddns_hostname (your server's public IP). This confirms your internet traffic is being routed through your VPN server.

# 6. Troubleshooting Notes (Key Fixes Encountered)
Verizon Fios Router Issues (UDP 1194 to TCP 8443):Initial attempts with UDP 1194 often fail with Verizon Fios routers due to strict NAT or firewall behavior.
Solution: Change proto tcp and port 8443 in server.conf and base.conf.
Crucial Router Step: After configuring port forwarding on the Fios router (from external TCP 8443 to internal your_server_internal_ip TCP 8443), ensure you click "Apply Changes" AND confirm the settings persist after a router reboot if possible. 
Verizon Fios routers can be notoriously finicky about saving firewall/port forwarding rules.
Cipher Mismatch / Client Handshake Issues:Clients might fail to connect or show "TLS handshake failed" errors even with correct certificates.Solution: Explicitly define data-ciphers in both server.conf and the client's .ovpn file. Using modern, widely supported ciphers like AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305 resolves this.

UFW on Host (for Whonix VM setup): When routing VM traffic (e.g., from virbr0 for KVM/Whonix) through the VPN, the host's UFW can implicitly block this traffic even with default allow outgoing.

Solution (for Whonix/KVM): If encountering issues, temporarily sudo ufw disable for diagnosis. If it works, then re-enable and add a very broad, high-priority rule: 
`sudo ufw insert 1 allow out`  on your_server_network_interface comment 'VERY BROAD VM OUTGOING ALLOW'. (However, in our case, the core issue persisted, pointing to VPN/ISP filtering).

# 7. Important Notes & Security Considerations

Security Hardening (SSH): For improved security, disable password authentication for SSH on your server and use SSH key-based authentication instead.
Dynamic DNS (DDNS): If your public IP address (e.g., your_server_public_ip_or_ddns_hostname) changes (common with residential ISPs), your VPN will stop working. Consider setting up a free DDNS service (e.g., DuckDNS, No-IP) and update your base.conf to use the DDNS hostname instead of the IP. 
Ongoing Maintenance: Regularly update your server (sudo apt update && sudo apt upgrade -y).
Client Security: Keep your .ovpn files secure. They contain sensitive authentication information.
Bandwidth: The speed of your VPN will be limited by your home internet's upload and download speeds.

# 8. Disclaimer
This guide provides steps for setting up a personal OpenVPN server. While OpenVPN is a secure technology, ensuring complete anonymity and protection requires understanding your threat model, network environment, and additional security measures (e.g., using Tor for specific activities). Misconfiguration or misuse can compromise your security.

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
In summary, this script exhibits behaviors consistent with a malicious tool designed to gain unauthorized access by changing user credentials, stealing them, and potentially disrupting the target system. Its multi-platform capabilities and attempts at stealth (process termination, log removal) further underscore its malicious intent.
</details>


**Weather App**:
Front-end code (HTML, CSS, and JavaScript) for a functional weather application that allows users to search for a city and see its current weather conditions, fetching the data from the OpenWeatherMap API and updating the page dynamically.

**Seacrh Bar**:
A simple search bar that allows that user to search anything via google.com




