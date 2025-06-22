from socket import *
import socket
import threading
import logging
from datetime import datetime
import sys

# konfigurasi logging untuk menampilkan informasi koneksi
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):

        while True:
            try:
                # Menerima data dari klien, buffer 32 byte cukup untuk request
                data = self.connection.recv(32)
                if data:
                    # Decode byte string ke UTF-8 dan hapus spasi/karakter newline
                    # Karakter 13 (CR) dan 10 (LF) akan dihapus oleh strip()
                    request = data.decode('utf-8').strip()
                    logging.info(f"Menerima request '{request}' dari {self.address}")

                    # proses request "TIME"
                    if request == "TIME":
                        now = datetime.now()
                        # Format waktu menjadi hh:mm:ss
                        waktu_sekarang = now.strftime("%H:%M:%S")
                        
                        # Siapkan response sesuai format "JAM <jam>\r\n"
                        response_str = f"JAM {waktu_sekarang}\r\n"
                        
                        # Kirim response setelah di-encode kembali ke byte
                        self.connection.sendall(response_str.encode('utf-8'))
                        logging.info(f"Mengirim response '{response_str.strip()}' ke {self.address}")
                    
                    # proses request "QUIT"
                    elif request == "QUIT":
                        logging.info(f"Klien {self.address} meminta untuk keluar. Koneksi ditutup.")
                        break # Keluar dari loop untuk menutup koneksi
                    
                    else:
                        # request tidak dikenali
                        error_msg = "ERROR: Perintah tidak dikenali\r\n"
                        self.connection.sendall(error_msg.encode('utf-8'))
                        logging.warning(f"Perintah tidak dikenali dari {self.address}: '{request}'")

                else:
                    # recv() mengembalikan data kosong, klien telah menutup koneksi
                    logging.info(f"Koneksi ditutup oleh {self.address} (data kosong).")
                    break
            except Exception as e:
                logging.error(f"Terjadi error pada koneksi dengan {self.address}: {e}")
                break
        
        # koneksi ditutup setelah keluar dari loop
        self.connection.close()

class Server(threading.Thread):
    def __init__(self, port):
        self.the_clients = []
        self.port = port
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        # Bind socket ke semua interface ('0.0.0.0') pada port yang ditentukan
        self.my_socket.bind(('0.0.0.0', self.port))
        self.my_socket.listen(5) # Mengizinkan hingga 5 koneksi dalam antrian
        logging.info(f"Server berjalan dan mendengarkan di port {self.port}")
        
        while True:
            try:
                # Menerima koneksi baru
                self.connection, self.client_address = self.my_socket.accept()
                logging.info(f"Koneksi baru dari {self.client_address}")
                
                # Membuat thread baru untuk menangani klien yang baru terhubung
                clt = ProcessTheClient(self.connection, self.client_address)
                clt.start()
                self.the_clients.append(clt)
            except Exception as e:
                logging.error(f"Error saat menerima koneksi: {e}")
                break

def main():
    # server pada port 45000 sesuai ketentuan
    svr = Server(45000)
    svr.start()

if __name__=="__main__":
    main()