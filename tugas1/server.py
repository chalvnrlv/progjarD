import sys
import socket
import logging
import hashlib

logging.basicConfig(level=logging.INFO)

try:
    # Create TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to port 32444
    server_address = ('0.0.0.0', 32444)
    logging.info(f"Starting server on {server_address}")
    sock.bind(server_address)
    sock.listen(1)
    
    while True:
        logging.info("Waiting for connection...")
        connection, client_address = sock.accept()
        logging.info(f"Connection from {client_address}")
        
        # Receive file
        file_data = b''
        while True:
            data = connection.recv(4096)  # Increased buffer size for file transfer
            if not data:
                break
            file_data += data
            
        # Save received file
        with open('received_file.txt', 'wb') as f:
            f.write(file_data)
            
        # Calculate hash
        file_hash = hashlib.sha256(file_data).hexdigest()
        logging.info(f"File received. SHA-256 Hash: {file_hash}")
        
        # Send hash back to client
        connection.sendall(file_hash.encode())
        connection.close()
        
except Exception as e:
    logging.error(f"Error: {str(e)}")
finally:
    sock.close()
    logging.info("Server closed")