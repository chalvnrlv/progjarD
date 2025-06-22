import sys
import socket
import logging
import hashlib

logging.basicConfig(level=logging.INFO)

try:
    # Create TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect to server
    server_address = ('172.18.0.3', 32444)
    logging.info(f"Connecting to {server_address}")
    sock.connect(server_address)
    
    # Read file to send
    with open('file_to_send.txt', 'rb') as f:
        file_data = f.read()
    
    # Calculate file hash
    file_hash = hashlib.sha256(file_data).hexdigest()
    logging.info(f"Sending file with SHA-256 Hash: {file_hash}")
    
    # Send file
    sock.sendall(file_data)
    sock.shutdown(socket.SHUT_WR)  # Signal end of sending
    
    # Receive verification hash from server
    verification_hash = sock.recv(64).decode()
    logging.info(f"Server verification hash: {verification_hash}")
    
    # Verify hash
    if verification_hash == file_hash:
        logging.info("File transfer successful! Hashes match.")
    else:
        logging.error("File transfer failed! Hashes don't match.")
        
except Exception as e:
    logging.error(f"Error: {str(e)}")
finally:
    sock.close()
    logging.info("Connection closed")