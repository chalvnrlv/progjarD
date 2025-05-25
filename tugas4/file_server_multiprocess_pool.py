import socket
import multiprocessing
import logging
import json
import time
from concurrent.futures import ProcessPoolExecutor
from file_protocol import FileProtocol

def handle_client_process(connection_data, address):
    """Handle client in separate process"""
    try:
        # Create new FileProtocol instance for this process
        fp = FileProtocol()
        
        # Recreate socket from connection data
        connection = socket.fromfd(connection_data, socket.AF_INET, socket.SOCK_STREAM)
        
        # Receive data
        all_data = b""
        connection.settimeout(30.0)
        
        while True:
            try:
                chunk = connection.recv(8192)
                if chunk:
                    all_data += chunk
                    connection.settimeout(1.0)
                else:
                    break
            except socket.timeout:
                if all_data:
                    break
                else:
                    continue
            except Exception as e:
                logging.error(f"Error receiving data from {address}: {str(e)}")
                return {'status': 'failed', 'error': str(e)}
        
        if all_data:
            try:
                message = all_data.decode('utf-8').strip()
                logging.info(f"Processing request from {address}, length: {len(message)}")
                
                # Process the message
                result = fp.proses_string(message)
                response = result + "\r\n\r\n"
                
                # Send response
                connection.settimeout(None)
                connection.sendall(response.encode('utf-8'))
                
                logging.info(f"Successfully processed request from {address}")
                return {'status': 'success'}
                
            except Exception as e:
                logging.error(f"Error processing request from {address}: {str(e)}")
                error_response = f'{{"status": "ERROR", "data": "Processing error"}}' + "\r\n\r\n"
                try:
                    connection.sendall(error_response.encode('utf-8'))
                except:
                    pass
                return {'status': 'failed', 'error': str(e)}
        else:
            logging.warning(f"No data received from {address}")
            return {'status': 'failed', 'error': 'No data received'}
            
    except Exception as e:
        logging.error(f"Process handler error for {address}: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
    finally:
        try:
            connection.close()
        except:
            pass

class FileServerMultiprocessPool:
    def __init__(self, ipaddress='0.0.0.0', port=7777, max_workers=5):
        self.ipinfo = (ipaddress, port)
        self.max_workers = max_workers
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.processed_requests = multiprocessing.Value('i', 0)
        self.failed_requests = multiprocessing.Value('i', 0)
        
    def get_stats(self):
        """Get server statistics"""
        return {
            'processed': self.processed_requests.value,
            'failed': self.failed_requests.value,
            'total': self.processed_requests.value + self.failed_requests.value
        }
    
    def run(self):
        """Start the server"""
        logging.info(f"Starting multiprocess pool server at {self.ipinfo} with {self.max_workers} workers")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(100)
        
        # Use a simpler approach - handle connections in main process
        # and only delegate processing to worker processes
        try:
            while True:
                try:
                    connection, client_address = self.my_socket.accept()
                    logging.debug(f"New connection from {client_address}")
                    
                    # Handle client directly in main process for multiprocessing
                    self.handle_client_direct(connection, client_address)
                    
                except Exception as e:
                    logging.error(f"Error accepting connection: {str(e)}")
                    continue
                    
        except KeyboardInterrupt:
            logging.info("Server shutting down...")
        finally:
            self.my_socket.close()
    
    def handle_client_direct(self, connection, address):
        """Handle client connection directly (simplified for multiprocessing)"""
        try:
            # Receive data
            all_data = b""
            connection.settimeout(30.0)
            
            while True:
                try:
                    chunk = connection.recv(8192)
                    if chunk:
                        all_data += chunk
                        connection.settimeout(1.0)
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
                    # Create new FileProtocol instance
                    fp = FileProtocol()
                    message = all_data.decode('utf-8').strip()
                    logging.info(f"Processing request from {address}, length: {len(message)}")
                    
                    # Process the message
                    result = fp.proses_string(message)
                    response = result + "\r\n\r\n"
                    
                    # Send response
                    connection.settimeout(None)
                    connection.sendall(response.encode('utf-8'))
                    
                    with self.processed_requests.get_lock():
                        self.processed_requests.value += 1
                    
                    logging.info(f"Successfully processed request from {address}")
                    
                except Exception as e:
                    logging.error(f"Error processing request from {address}: {str(e)}")
                    with self.failed_requests.get_lock():
                        self.failed_requests.value += 1
                    
                    error_response = f'{{"status": "ERROR", "data": "Processing error"}}' + "\r\n\r\n"
                    try:
                        connection.sendall(error_response.encode('utf-8'))
                    except:
                        pass
            else:
                logging.warning(f"No data received from {address}")
                with self.failed_requests.get_lock():
                    self.failed_requests.value += 1
                    
        except Exception as e:
            logging.error(f"Client handler error for {address}: {str(e)}")
            with self.failed_requests.get_lock():
                self.failed_requests.value += 1
        finally:
            try:
                connection.close()
            except:
                pass

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
    
    server = FileServerMultiprocessPool(max_workers=max_workers, port=port)
    server.run()

if __name__ == "__main__":
    main()