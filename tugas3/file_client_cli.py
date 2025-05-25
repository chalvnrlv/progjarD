import socket
import json
import base64
import logging

server_address = ('172.16.16.101', 7777)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(server_address)
        logging.warning(f"connecting to {server_address}")
        
        # Send command
        logging.warning(f"sending message (length: {len(command_str)})")
        message = command_str.encode('utf-8')
        sock.sendall(message)
        
        # Tutup sisi pengirim untuk memberi tahu server bahwa data sudah selesai
        sock.shutdown(socket.SHUT_WR)
        
        # Receive response
        data_received = ""
        sock.settimeout(10.0)  # 10 second timeout for response
        
        while True:
            try:
                data = sock.recv(4096)
                if data:
                    data_received += data.decode('utf-8')
                    # Check for end marker
                    if "\r\n\r\n" in data_received:
                        # Remove the end marker
                        data_received = data_received.replace("\r\n\r\n", "")
                        break
                else:
                    break
            except socket.timeout:
                logging.warning("Timeout waiting for response")
                break
        
        if data_received:
            # Parse JSON response
            try:
                hasil = json.loads(data_received)
                logging.warning("data received from server:")
                return hasil
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error: {str(e)}")
                logging.error(f"Raw response: {data_received}")
                return {"status": "ERROR", "data": "Invalid JSON response"}
        else:
            return {"status": "ERROR", "data": "No response from server"}
            
    except Exception as e:
        logging.warning(f"error during communication: {str(e)}")
        return {"status": "ERROR", "data": str(e)}
    finally:
        try:
            sock.close()
        except:
            pass

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print(f"Gagal: {hasil.get('data', 'Unknown error')}")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        # Process base64 file to bytes
        namafile = hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        with open(namafile, 'wb+') as fp:
            fp.write(isifile)
        print(f"File {namafile} berhasil didownload")
        return True
    else:
        print(f"Gagal: {hasil.get('data', 'Unknown error')}")
        return False

def remote_upload(filename=""):
    try:
        with open(filename, "rb") as f:
            data = f.read()
        
        print(f"Uploading {filename} ({len(data)} bytes)...")
        
        # Encode to base64
        b64_encoded = base64.b64encode(data).decode('utf-8')
        
        # Create JSON command
        command_data = {
            "command": "UPLOAD",
            "filename": filename,
            "filedata": b64_encoded
        }
        command_str = json.dumps(command_data)
        
        print(f"Sending JSON command ({len(command_str)} chars)...")
        hasil = send_command(command_str)
        
        if hasil['status'] == 'OK':
            print(f"Upload berhasil: {hasil['data']}")
        else:
            print(f"Upload gagal: {hasil['data']}")
            
    except FileNotFoundError:
        print("File tidak ditemukan di client")
    except Exception as e:
        print(f"Error saat upload: {str(e)}")

def remote_delete(filename):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print(f"Delete berhasil: {hasil.get('data', 'File deleted')}")
    else:
        print(f"Delete gagal: {hasil.get('data', 'Unknown error')}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    server_address = ('172.16.16.101', 7777)
    
    print("=== Testing File Server ===")
    
    print("\n1. Listing files:")
    remote_list()
    
    print("\n2. Uploading file:")
    remote_upload('donalbebek.jpg')
    
    print("\n3. Listing files again:")
    remote_list()
