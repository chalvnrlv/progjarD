import socket
import json
import base64
import logging
import time
import os
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import random
import string

class StressTestClient:
    def __init__(self, server_address=('172.16.16.101', 7777)):
        self.server_address = server_address
        self.results = []
        self.lock = threading.Lock()
        
    def generate_test_file(self, size_mb, filename):
        """Generate test file of specified size"""
        size_bytes = size_mb * 1024 * 1024
        
        # Create random content
        content = ''.join(random.choices(string.ascii_letters + string.digits, k=min(1024, size_bytes)))
        
        # Repeat content to reach desired size
        full_content = (content * ((size_bytes // len(content)) + 1))[:size_bytes]
        
        with open(filename, 'w') as f:
            f.write(full_content)
        
        return filename
    
    def send_command(self, command_str="", timeout=60):
        """Send command to server with timeout"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            sock.connect(self.server_address)
            
            # Send command
            message = command_str.encode('utf-8')
            sock.sendall(message)
            sock.shutdown(socket.SHUT_WR)
            
            # Receive response
            data_received = ""
            sock.settimeout(timeout)
            
            while True:
                try:
                    data = sock.recv(4096)
                    if data:
                        data_received += data.decode('utf-8')
                        if "\r\n\r\n" in data_received:
                            data_received = data_received.replace("\r\n\r\n", "")
                            break
                    else:
                        break
                except socket.timeout:
                    break
            
            if data_received:
                try:
                    hasil = json.loads(data_received)
                    return hasil
                except json.JSONDecodeError as e:
                    return {"status": "ERROR", "data": f"Invalid JSON response: {str(e)}"}
            else:
                return {"status": "ERROR", "data": "No response from server"}
                
        except Exception as e:
            return {"status": "ERROR", "data": str(e)}
        finally:
            try:
                sock.close()
            except:
                pass
    
    def upload_file(self, filename):
        """Upload file to server"""
        start_time = time.time()
        
        try:
            with open(filename, "rb") as f:
                data = f.read()
            
            b64_encoded = base64.b64encode(data).decode('utf-8')
            
            command_data = {
                "command": "UPLOAD",
                "filename": os.path.basename(filename),
                "filedata": b64_encoded
            }
            command_str = json.dumps(command_data)
            
            result = self.send_command(command_str, timeout=120)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.get('status') == 'OK'
            throughput = len(data) / duration if duration > 0 and success else 0
            
            return {
                'operation': 'upload',
                'filename': filename,
                'file_size': len(data),
                'duration': duration,
                'throughput': throughput,
                'success': success,
                'error': result.get('data', '') if not success else None
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            return {
                'operation': 'upload',
                'filename': filename,
                'file_size': 0,
                'duration': duration,
                'throughput': 0,
                'success': False,
                'error': str(e)
            }
    
    def download_file(self, filename):
        """Download file from server"""
        start_time = time.time()
        
        try:
            command_str = f"GET {filename}"
            result = self.send_command(command_str, timeout=120)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.get('status') == 'OK':
                file_data = base64.b64decode(result['data_file'])
                
                # Save downloaded file
                download_filename = f"downloaded_{filename}"
                with open(download_filename, 'wb') as f:
                    f.write(file_data)
                
                throughput = len(file_data) / duration if duration > 0 else 0
                
                return {
                    'operation': 'download',
                    'filename': filename,
                    'file_size': len(file_data),
                    'duration': duration,
                    'throughput': throughput,
                    'success': True,
                    'error': None
                }
            else:
                return {
                    'operation': 'download',
                    'filename': filename,
                    'file_size': 0,
                    'duration': duration,
                    'throughput': 0,
                    'success': False,
                    'error': result.get('data', 'Unknown error')
                }
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            return {
                'operation': 'download',
                'filename': filename,
                'file_size': 0,
                'duration': duration,
                'throughput': 0,
                'success': False,
                'error': str(e)
            }
    
    def list_files(self):
        """List files on server"""
        start_time = time.time()
        
        try:
            command_str = "LIST"
            result = self.send_command(command_str)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.get('status') == 'OK'
            
            return {
                'operation': 'list',
                'filename': None,
                'file_size': 0,
                'duration': duration,
                'throughput': 0,
                'success': success,
                'error': result.get('data', '') if not success else None,
                'file_list': result.get('data', []) if success else []
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            return {
                'operation': 'list',
                'filename': None,
                'file_size': 0,
                'duration': duration,
                'throughput': 0,
                'success': False,
                'error': str(e),
                'file_list': []
            }

def worker_thread_task(args):
    """Worker task for threading pool"""
    client_id, operation, filename, server_address = args
    
    client = StressTestClient(server_address)
    
    if operation == 'upload':
        return client.upload_file(filename)
    elif operation == 'download':
        return client.download_file(filename)
    elif operation == 'list':
        return client.list_files()

def worker_process_task(args):
    """Worker task for multiprocessing pool"""
    return worker_thread_task(args)

def run_stress_test(operation, file_size_mb, num_clients, use_multiprocessing=False, server_address=('172.16.16.101', 7777)):
    """Run stress test with specified parameters"""
    
    print(f"Running stress test: {operation}, {file_size_mb}MB, {num_clients} clients, {'multiprocessing' if use_multiprocessing else 'threading'}")
    
    # Prepare test files
    test_files = []
    if operation in ['upload', 'download']:
        for i in range(min(num_clients, 10)):  # Limit number of unique files
            filename = f"test_file_{file_size_mb}mb_{i}.txt"
            client = StressTestClient(server_address)
            client.generate_test_file(file_size_mb, filename)
            test_files.append(filename)
    
    # Prepare tasks
    tasks = []
    for i in range(num_clients):
        if operation == 'list':
            filename = None
        else:
            filename = test_files[i % len(test_files)]
        
        tasks.append((i, operation, filename, server_address))
    
    # Execute tasks
    start_time = time.time()
    results = []
    
    if use_multiprocessing:
        with ProcessPoolExecutor(max_workers=min(num_clients, 50)) as executor:
            future_to_task = {executor.submit(worker_process_task, task): task for task in tasks}
            
            for future in as_completed(future_to_task):
                try:
                    result = future.result(timeout=180)
                    results.append(result)
                except Exception as e:
                    task = future_to_task[future]
                    results.append({
                        'operation': operation,
                        'filename': task[2],
                        'file_size': 0,
                        'duration': 0,
                        'throughput': 0,
                        'success': False,
                        'error': str(e)
                    })
    else:
        with ThreadPoolExecutor(max_workers=min(num_clients, 50)) as executor:
            future_to_task = {executor.submit(worker_thread_task, task): task for task in tasks}
            
            for future in as_completed(future_to_task):
                try:
                    result = future.result(timeout=180)
                    results.append(result)
                except Exception as e:
                    task = future_to_task[future]
                    results.append({
                        'operation': operation,
                        'filename': task[2],
                        'file_size': 0,
                        'duration': 0,
                        'throughput': 0,
                        'success': False,
                        'error': str(e)
                    })
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Calculate statistics
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]
    
    total_bytes = sum(r['file_size'] for r in successful_results)
    avg_duration = sum(r['duration'] for r in successful_results) / len(successful_results) if successful_results else 0
    total_throughput = sum(r['throughput'] for r in successful_results)
    avg_throughput = total_throughput / len(successful_results) if successful_results else 0
    
    # Clean up test files
    for filename in test_files:
        try:
            os.remove(filename)
        except:
            pass
    
    return {
        'operation': operation,
        'file_size_mb': file_size_mb,
        'num_clients': num_clients,
        'concurrency_type': 'multiprocessing' if use_multiprocessing else 'threading',
        'total_duration': total_duration,
        'avg_client_duration': avg_duration,
        'total_throughput': total_throughput,
        'avg_client_throughput': avg_throughput,
        'successful_clients': len(successful_results),
        'failed_clients': len(failed_results),
        'total_bytes_processed': total_bytes,
        'results': results
    }

if __name__ == '__main__':
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    # Test parameters
    server_address = ('172.16.16.101', 7777)
    
    # Run a simple test
    result = run_stress_test('upload', 1, 2, False, server_address)
    print(f"Test completed: {result['successful_clients']} successful, {result['failed_clients']} failed")
    print(f"Average throughput: {result['avg_client_throughput']:.2f} bytes/sec")