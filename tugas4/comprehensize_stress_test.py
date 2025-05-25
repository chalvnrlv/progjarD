#!/usr/bin/env python3

import time
import logging
import csv
import os
import subprocess
import signal
import psutil
from stress_test_client import run_stress_test
import pandas as pd

class ComprehensiveStressTest:
    def __init__(self, server_address=('172.16.16.101', 7777)):
        self.server_address = server_address
        self.results = []
        self.server_processes = {}
        
        # Test parameters
        self.operations = ['download', 'upload']
        self.file_sizes = [10, 50, 100]  # MB
        self.client_workers = [1, 5, 50]
        self.server_workers = [1, 5, 50]
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('stress_test.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_server(self, server_type, workers, port=7777):
        """Start server with specified configuration"""
        try:
            # Kill any existing server process
            self.stop_server()
            
            if server_type == 'threading':
                cmd = ['python3', 'file_server_threading_pool.py', str(workers), str(port)]
            else:  # multiprocessing
                cmd = ['python3', 'file_server_multiprocess_pool.py', str(workers), str(port)]
            
            self.logger.info(f"Starting {server_type} server with {workers} workers on port {port}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            self.server_processes[server_type] = process
            
            # Wait for server to start
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                self.logger.info(f"Server started successfully (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                self.logger.error(f"Server failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting server: {str(e)}")
            return False
    
    def stop_server(self):
        """Stop all running server processes"""
        for server_type, process in list(self.server_processes.items()):
            try:
                if process and process.poll() is None:
                    self.logger.info(f"Stopping {server_type} server (PID: {process.pid})")
                    
                    # Kill process group to ensure all child processes are terminated
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
                    # Wait for process to terminate
                    process.wait(timeout=10)
                    
                del self.server_processes[server_type]
            except Exception as e:
                self.logger.warning(f"Error stopping {server_type} server: {str(e)}")
        
        # Additional cleanup - kill any lingering python processes on our ports
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python3' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'file_server' in cmdline and ('7777' in cmdline or '7778' in cmdline):
                            self.logger.info(f"Killing lingering server process {proc.info['pid']}")
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.warning(f"Error during additional cleanup: {str(e)}")
    
    def wait_for_server(self, timeout=30):
        """Wait for server to be ready"""
        from stress_test_client import StressTestClient
        
        client = StressTestClient(self.server_address)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = client.list_files()
                if result['success']:
                    self.logger.info("Server is ready")
                    return True
            except Exception:
                pass
            time.sleep(1)
        
        self.logger.error("Server failed to become ready within timeout")
        return False
    
    def run_single_test(self, test_num, operation, file_size, client_workers, server_workers, server_type):
        """Run a single stress test combination"""
        self.logger.info(f"Test {test_num}: {operation}, {file_size}MB, {client_workers} clients, {server_workers} server workers ({server_type})")
        
        # Start server
        port = 7777 if server_type == 'threading' else 7778
        server_address = (self.server_address[0], port)
        
        if not self.start_server(server_type, server_workers, port):
            return {
                'test_num': test_num,
                'operation': operation,
                'file_size_mb': file_size,
                'client_workers': client_workers,
                'server_workers': server_workers,
                'server_type': server_type,
                'avg_client_duration': 0,
                'avg_client_throughput': 0,
                'successful_clients': 0,
                'failed_clients': client_workers,
                'server_successful': 0,
                'server_failed': 1,
                'error': 'Failed to start server'
            }
        
        # Wait for server to be ready
        if not self.wait_for_server():
            self.stop_server()
            return {
                'test_num': test_num,
                'operation': operation,
                'file_size_mb': file_size,
                'client_workers': client_workers,
                'server_workers': server_workers,
                'server_type': server_type,
                'avg_client_duration': 0,
                'avg_client_throughput': 0,
                'successful_clients': 0,
                'failed_clients': client_workers,
                'server_successful': 0,
                'server_failed': 1,
                'error': 'Server not ready'
            }
        
        try:
            # Run stress test with threading pool
            result_threading = run_stress_test(
                operation=operation,
                file_size_mb=file_size,
                num_clients=client_workers,
                use_multiprocessing=False,
                server_address=server_address
            )
            
            # Run stress test with multiprocessing pool  
            result_multiprocessing = run_stress_test(
                operation=operation,
                file_size_mb=file_size,
                num_clients=client_workers,
                use_multiprocessing=True,
                server_address=server_address
            )
            
            # Get server stats if possible
            server_successful = 1
            server_failed = 0
            
            results = []
            
            # Add threading result
            results.append({
                'test_num': test_num,
                'operation': operation,
                'file_size_mb': file_size,
                'client_workers': client_workers,
                'server_workers': server_workers,
                'server_type': server_type,
                'client_concurrency': 'threading',
                'avg_client_duration': result_threading['avg_client_duration'],
                'avg_client_throughput': result_threading['avg_client_throughput'],
                'successful_clients': result_threading['successful_clients'],
                'failed_clients': result_threading['failed_clients'],
                'server_successful': server_successful,
                'server_failed': server_failed,
                'total_duration': result_threading['total_duration'],
                'total_bytes': result_threading['total_bytes_processed'],
                'error': None
            })
            
            # Add multiprocessing result  
            results.append({
                'test_num': test_num + 0.5,  # Distinguish from threading test
                'operation': operation,
                'file_size_mb': file_size,
                'client_workers': client_workers,
                'server_workers': server_workers,
                'server_type': server_type,
                'client_concurrency': 'multiprocessing',
                'avg_client_duration': result_multiprocessing['avg_client_duration'],
                'avg_client_throughput': result_multiprocessing['avg_client_throughput'],
                'successful_clients': result_multiprocessing['successful_clients'],
                'failed_clients': result_multiprocessing['failed_clients'],
                'server_successful': server_successful,
                'server_failed': server_failed,
                'total_duration': result_multiprocessing['total_duration'],
                'total_bytes': result_multiprocessing['total_bytes_processed'],
                'error': None
            })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error during test execution: {str(e)}")
            return [{
                'test_num': test_num,
                'operation': operation,
                'file_size_mb': file_size,
                'client_workers': client_workers,
                'server_workers': server_workers,
                'server_type': server_type,
                'client_concurrency': 'threading',
                'avg_client_duration': 0,
                'avg_client_throughput': 0,
                'successful_clients': 0,
                'failed_clients': client_workers,
                'server_successful': 0,
                'server_failed': 1,
                'error': str(e)
            }]
        finally:
            self.stop_server()
            time.sleep(2)  # Brief pause between tests
    
    def run_all_tests(self):
        """Run all test combinations"""
        self.logger.info("Starting comprehensive stress test")
        self.logger.info(f"Total combinations: {len(self.operations)} operations × {len(self.file_sizes)} sizes × {len(self.client_workers)} client workers × {len(self.server_workers)} server workers × 2 server types = {len(self.operations) * len(self.file_sizes) * len(self.client_workers) * len(self.server_workers) * 2} tests")
        
        test_num = 1
        all_results = []
        
        for operation in self.operations:
            for file_size in self.file_sizes:
                for client_workers in self.client_workers:
                    for server_workers in self.server_workers:
                        for server_type in ['threading', 'multiprocessing']:
                            try:
                                results = self.run_single_test(
                                    test_num, operation, file_size, 
                                    client_workers, server_workers, server_type
                                )
                                
                                if isinstance(results, list):
                                    all_results.extend(results)
                                else:
                                    all_results.append(results)
                                
                                # Log progress
                                total_tests = len(self.operations) * len(self.file_sizes) * len(self.client_workers) * len(self.server_workers) * 2
                                progress = (test_num / total_tests) * 100
                                self.logger.info(f"Progress: {progress:.1f}% ({test_num}/{total_tests})")
                                
                            except Exception as e:
                                self.logger.error(f"Test {test_num} failed with error: {str(e)}")
                                all_results.append({
                                    'test_num': test_num,
                                    'operation': operation,
                                    'file_size_mb': file_size,
                                    'client_workers': client_workers,
                                    'server_workers': server_workers,
                                    'server_type': server_type,
                                    'client_concurrency': 'unknown',
                                    'avg_client_duration': 0,
                                    'avg_client_throughput': 0,
                                    'successful_clients': 0,
                                    'failed_clients': client_workers,
                                    'server_successful': 0,
                                    'server_failed': 1,
                                    'error': str(e)
                                })
                            
                            test_num += 1
        
        self.results = all_results
        return all_results
    
    def save_results(self, filename='stress_test_results.csv'):
        """Save results to CSV file"""
        if not self.results:
            self.logger.warning("No results to save")
            return
        
        # Create DataFrame
        df = pd.DataFrame(self.results)
        
        # Reorder columns for better readability
        column_order = [
            'test_num', 'operation', 'file_size_mb', 'client_workers', 
            'server_workers', 'server_type', 'client_concurrency',
            'avg_client_duration', 'avg_client_throughput', 
            'successful_clients', 'failed_clients',
            'server_successful', 'server_failed',
            'total_duration', 'total_bytes', 'error'
        ]
        
        # Reorder columns (keep only existing ones)
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Save to CSV
        df.to_csv(filename, index=False)
        self.logger.info(f"Results saved to {filename}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        if not self.results:
            return
        
        df = pd.DataFrame(self.results)
        
        print("\n" + "="*80)
        print("STRESS TEST SUMMARY")
        print("="*80)
        
        print(f"Total tests conducted: {len(df)}")
        print(f"Successful tests: {len(df[df['error'].isna()])}")
        print(f"Failed tests: {len(df[df['error'].notna()])}")
        
        if len(df[df['error'].isna()]) > 0:
            successful_df = df[df['error'].isna()]
            
            print(f"\nAverage client duration: {successful_df['avg_client_duration'].mean():.2f} seconds")
            print(f"Average client throughput: {successful_df['avg_client_throughput'].mean():.2f} bytes/sec")
            print(f"Maximum throughput achieved: {successful_df['avg_client_throughput'].max():.2f} bytes/sec")
            
            print(f"\nTotal successful client operations: {successful_df['successful_clients'].sum()}")
            print(f"Total failed client operations: {successful_df['failed_clients'].sum()}")
            
            # Best performing configurations
            print(f"\nBest throughput configuration:")
            best_throughput = successful_df.loc[successful_df['avg_client_throughput'].idxmax()]
            print(f"  Operation: {best_throughput['operation']}")
            print(f"  File size: {best_throughput['file_size_mb']}MB")
            print(f"  Client workers: {best_throughput['client_workers']}")
            print(f"  Server workers: {best_throughput['server_workers']}")
            print(f"  Server type: {best_throughput['server_type']}")
            print(f"  Client concurrency: {best_throughput['client_concurrency']}")
            print(f"  Throughput: {best_throughput['avg_client_throughput']:.2f} bytes/sec")
        
        print("="*80)

def main():
    """Main function to run comprehensive stress test"""
    
    # Configuration
    server_address = ('172.16.16.101', 7777)
    
    print("Comprehensive File Server Stress Test")
    print("=====================================")
    print(f"Server address: {server_address}")
    print("Test parameters:")
    print("  Operations: download, upload")
    print("  File sizes: 10MB, 50MB, 100MB")  
    print("  Client workers: 1, 5, 50")
    print("  Server workers: 1, 5, 50")
    print("  Server types: threading, multiprocessing")
    print("  Client concurrency: threading, multiprocessing")
    print()
    
    # Create and run test
    test_runner = ComprehensiveStressTest(server_address)
    
    try:
        results = test_runner.run_all_tests()
        test_runner.save_results('comprehensive_stress_test_results.csv')
        
        print(f"\nTest completed successfully!")
        print(f"Results saved to: comprehensive_stress_test_results.csv")
        print(f"Log file: stress_test.log")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        test_runner.stop_server()
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        test_runner.stop_server()
    finally:
        # Ensure cleanup
        test_runner.stop_server()

if __name__ == '__main__':
    main()