from socket import *
import socket
import threading
import logging
import time
import sys
from file_protocol import FileProtocol

fp = FileProtocol()

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)
    
    def run(self):
        try:
            # Baca semua data yang tersedia
            all_data = b""
            
            # Set initial timeout yang cukup untuk menerima header
            self.connection.settimeout(5.0)
            
            while True:
                try:
                    chunk = self.connection.recv(8192)  # Buffer besar
                    if chunk:
                        all_data += chunk
                        # Set timeout pendek
                        self.connection.settimeout(0.5)
                    else:
                        # Client menutup koneksi
                        break
                except socket.timeout:
                    # Tidak ada data lagi dalam timeout, anggap selesai
                    if all_data:
                        break
                    else:
                        # Tidak ada data sama sekali, continue menunggu
                        continue
                except Exception as e:
                    logging.error(f"Error receiving data: {str(e)}")
                    break
            
            if all_data:
                try:
                    # Decode data
                    message = all_data.decode('utf-8').strip()
                    logging.warning(f"Message received, length: {len(message)} chars")
                    
                    # Process message
                    hasil = fp.proses_string(message)
                    response = hasil + "\r\n\r\n"
                    
                    # Send response
                    self.connection.settimeout(None)
                    self.connection.sendall(response.encode('utf-8'))
                    logging.warning(f"Response sent to {self.address}")
                    
                except UnicodeDecodeError as e:
                    logging.error(f"Unicode decode error: {str(e)}")
                    self.send_error("Invalid character encoding")
                except Exception as e:
                    logging.error(f"Processing error: {str(e)}")
                    self.send_error("Processing error")
            else:
                logging.warning(f"No data received from {self.address}")
                
        except Exception as e:
            logging.error(f"Client handler error {self.address}: {str(e)}")
            self.send_error("Server error")
        finally:
            try:
                self.connection.close()
            except:
                pass
            logging.warning(f"Connection closed for {self.address}")
    
    def send_error(self, error_msg):
        try:
            error_response = f'{{"status": "ERROR", "data": "{error_msg}"}}' + "\r\n\r\n"
            self.connection.sendall(error_response.encode('utf-8'))
        except:
            pass

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=8889):
        self.ipinfo = (ipaddress, port)
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)
    
    def run(self):
        logging.warning(f"server berjalan di ip address {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(10)  # Increase backlog
        while True:
            try:
                self.connection, self.client_address = self.my_socket.accept()
                logging.warning(f"connection from {self.client_address}")
                clt = ProcessTheClient(self.connection, self.client_address)
                clt.start()
                self.the_clients.append(clt)
            except Exception as e:
                logging.error(f"Error accepting connection: {str(e)}")

def main():
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s:%(message)s')
    svr = Server(ipaddress='0.0.0.0', port=7777)
    svr.start()

if __name__ == "__main__":
    main()
