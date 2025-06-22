import socket
import threading
import logging
import json
from concurrent.futures import ThreadPoolExecutor
from file_protocol import FileProtocol

class FileServerThreadingPool:
    def __init__(self, ipaddress='0.0.0.0', port=7777, max_workers=5):
        self.ipinfo = (ipaddress, port)
        self.max_workers = max_workers
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fp = FileProtocol()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processed_requests = 0
        self.failed_requests = 0
        self.lock = threading.Lock()
        
    def handle_client(self, connection, address):
        """Handle individual client connection"""
        try:
            # Receive data
            all_data = b""
            connection.settimeout(30.0)  # 30 second timeout
            
            while True:
                try:
                    chunk = connection.recv(8192)
                    if chunk:
                        all_data += chunk
                        connection.settimeout(1.0)  # Reduce timeout after first chunk
                    else:
                        break
                except socket.timeout:
                    if all_data:
                        break
                    else:
                        continue
                except Exception as e:
                    logging.error(f"Error receiving data from {address}: {str(e)}")
                    break
            
            if all_data:
                try:
                    message = all_data.decode('utf-8').strip()
                    logging.info(f"Processing request from {address}, length: {len(message)}")
                    
                    # Process the message
                    result = self.fp.proses_string(message)
                    response = result + "\r\n\r\n"
                    
                    # Send response
                    connection.settimeout(None)
                    connection.sendall(response.encode('utf-8'))
                    
                    with self.lock:
                        self.processed_requests += 1
                    
                    logging.info(f"Successfully processed request from {address}")
                    
                except Exception as e:
                    logging.error(f"Error processing request from {address}: {str(e)}")
                    with self.lock:
                        self.failed_requests += 1
                    self.send_error(connection, "Processing error")
            else:
                logging.warning(f"No data received from {address}")
                with self.lock:
                    self.failed_requests += 1
                    
        except Exception as e:
            logging.error(f"Client handler error for {address}: {str(e)}")
            with self.lock:
                self.failed_requests += 1
        finally:
            try:
                connection.close()
            except:
                pass
    
    def send_error(self, connection, error_msg):
        """Send error response to client"""
        try:
            error_response = f'{{"status": "ERROR", "data": "{error_msg}"}}' + "\r\n\r\n"
            connection.sendall(error_response.encode('utf-8'))
        except:
            pass
    
    def get_stats(self):
        """Get server statistics"""
        with self.lock:
            return {
                'processed': self.processed_requests,
                'failed': self.failed_requests,
                'total': self.processed_requests + self.failed_requests
            }
    
    def run(self):
        """Start the server"""
        logging.info(f"Starting threading pool server at {self.ipinfo} with {self.max_workers} workers")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(100)  # Large backlog for stress testing
        
        try:
            while True:
                try:
                    connection, client_address = self.my_socket.accept()
                    logging.debug(f"New connection from {client_address}")
                    
                    # Submit task to thread pool
                    self.executor.submit(self.handle_client, connection, client_address)
                    
                except Exception as e:
                    logging.error(f"Error accepting connection: {str(e)}")
                    continue
                    
        except KeyboardInterrupt:
            logging.info("Server shutting down...")
        finally:
            self.executor.shutdown(wait=True)
            self.my_socket.close()

def main():
    import sys
    
    # Parse command line arguments
    max_workers = 5
    port = 7777
    
    if len(sys.argv) > 1:
        max_workers = int(sys.argv[1])
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    server = FileServerThreadingPool(max_workers=max_workers, port=port)
    server.run()

if __name__ == "__main__":
    main()