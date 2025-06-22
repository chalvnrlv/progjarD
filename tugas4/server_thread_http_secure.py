from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from http import HttpServer

httpserver = HttpServer()


def ProcessTheClient(connection,address):
    try:
        headers_data = b""
        while b"\r\n\r\n" not in headers_data:
            data = connection.recv(1024)
            if not data:
                break
            headers_data += data
            
        # -pisah headers data
        header_part, _, body_part = headers_data.partition(b'\r\n\r\n')
        full_request_str = header_part.decode('utf-8')

        # panjang body
        content_length = 0
        headers_lines = full_request_str.split('\r\n')
        for line in headers_lines:
            if line.lower().startswith('content-length:'):
                try:
                    content_length = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass
                break
                
        # for body = length
        while len(body_part) < content_length:
            data = connection.recv(content_length - len(body_part))
            if not data:
                break
            body_part += data
            
        full_request = full_request_str + "\r\n\r\n" + body_part.decode('utf-8', 'ignore')
        hasil = httpserver.proses(full_request)
        connection.sendall(hasil)

    except Exception as e:
        # logging.error(f"Error pada client {address}: {e}")
        pass
    finally:
        connection.close()
    return

def Server():
	the_clients = []
	my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	my_socket.bind(('0.0.0.0', 8885))
	my_socket.listen(1)

	with ThreadPoolExecutor(20) as executor:
		while True:
				connection, client_address = my_socket.accept()
				#logging.warning("connection from {}".format(client_address))
				p = executor.submit(ProcessTheClient, connection, client_address)
				the_clients.append(p)
				#menampilkan jumlah process yang sedang aktif
				jumlah = ['x' for i in the_clients if i.running()==True]
				print(jumlah)





def main():
	Server()

if __name__=="__main__":
	main()

