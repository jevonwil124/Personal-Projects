# background_listener_multiple_files.py (on Windows)
import socket
import threading
import datetime

HOST = ''  # Listen on all interfaces
PORT = 12345
OUTPUT_DIR = r''  # Directory to save files

def handle_connection(conn, addr):
    print(f"Connected by {addr}")
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"received_credentials_{timestamp}.txt"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        with open(output_path, 'wb') as f:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                f.write(data)
        print(f"Data received and saved to {output_path}")
    except Exception as e:
        print(f"Error handling connection: {e}")
    finally:
        conn.close()

def start_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on port {PORT} in the background...")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_connection, args=(conn, addr))
            thread.daemon = True  # Allow the main program to exit even if this thread is running
            thread.start()

if __name__ == "__main__":
    # You'll need to run this script in a way that keeps it running in the background.
    # On Windows, you can use the following methods:
    # 1. Run it in a separate Command Prompt or PowerShell window and minimize it.
    # 2. Use a tool to run it as a background service (more advanced).
    start_listener()