import socket
import json
import logging
import os

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HttpClient:
    def __init__(self, server_ip, server_port):
        self.server_address = (server_ip, server_port)

    def _create_socket(self):
        """Membuat dan menghubungkan socket."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.info(f"Menghubungkan ke {self.server_address}")
            sock.connect(self.server_address)
            return sock
        except Exception as e:
            logging.error(f"Error saat membuat koneksi: {e}")
            return None

    def _send_request(self, sock, request_data):
        """Mengirim request dan menerima response."""
        try:
            sock.sendall(request_data)
            
            # Menerima response dari server
            data_received = b""
            while True:
                data = sock.recv(2048)
                if not data:
                    break
                data_received += data
            
            return data_received.decode('utf-8')
        except Exception as e:
            logging.error(f"Error selama komunikasi: {e}")
            return None
        finally:
            sock.close()

    def list_files(self, directory="/"):
        """Mengirim request LIST untuk melihat daftar file."""
        sock = self._create_socket()
        if not sock: return None

        request_str = f"LIST {directory} HTTP/1.1\r\n"
        request_str += f"Host: {self.server_address[0]}\r\n"
        request_str += "Connection: close\r\n\r\n"
        
        logging.info(f"Mengirim request LIST ke direktori '{directory}'")
        return self._send_request(sock, request_str.encode('utf-8'))

    def upload_file(self, local_filepath, remote_filename):
        """Mengirim request PUT untuk mengunggah file."""
        if not os.path.exists(local_filepath):
            logging.error(f"File lokal tidak ditemukan: {local_filepath}")
            return None

        sock = self._create_socket()
        if not sock: return None

        with open(local_filepath, 'rb') as f:
            file_content = f.read()

        request_str = f"PUT /{remote_filename} HTTP/1.1\r\n"
        request_str += f"Host: {self.server_address[0]}\r\n"
        request_str += f"Content-Length: {len(file_content)}\r\n"
        request_str += "Connection: close\r\n\r\n"

        # Gabungkan header (bytes) dan body (bytes)
        request_data = request_str.encode('utf-8') + file_content
        
        logging.info(f"Mengunggah '{local_filepath}' ke server sebagai '{remote_filename}'")
        return self._send_request(sock, request_data)

    def delete_file(self, remote_filename):
        """Mengirim request DELETE untuk menghapus file."""
        sock = self._create_socket()
        if not sock: return None

        request_str = f"DELETE /{remote_filename} HTTP/1.1\r\n"
        request_str += f"Host: {self.server_address[0]}\r\n"
        request_str += "Connection: close\r\n\r\n"
        
        logging.info(f"Menghapus file '{remote_filename}' dari server")
        return self._send_request(sock, request_str.encode('utf-8'))


def main():
    # Asumsi server berjalan di mesin1 (172.16.16.101) pada port 8885 (Thread Pool) atau 8889 (Process Pool)
    # Sesuaikan port jika Anda menjalankan server yang berbeda
    SERVER_IP = "172.16.16.101"
    SERVER_PORT = 8885  # Ganti port sesuai server

    client = HttpClient(SERVER_IP, SERVER_PORT)

    # --- Skenario Pengujian ---
    print("\n\n----- 1. MELIHAT DAFTAR FILE AWAL -----")
    response = client.list_files("/")
    if response: print(response)

    print("\n\n----- 2. MENGUNGGAH FILE BARU -----")
    # Buat file dummy untuk diunggah
    upload_filename = "file_coba_upload.txt"
    with open(upload_filename, "w") as f:
        f.write("Ini adalah isi dari file yang diunggah oleh klien.")
    
    response = client.upload_file(upload_filename, upload_filename)
    if response: print(response)

    print("\n\n----- 3. MELIHAT DAFTAR FILE SETELAH UPLOAD -----")
    response = client.list_files("/")
    if response: print(response)

    print("\n\n----- 4. MENGHAPUS FILE YANG DIUNGGAH -----")
    response = client.delete_file(upload_filename)
    if response: print(response)
    
    # Hapus file dummy lokal
    os.remove(upload_filename)

    print("\n\n----- 5. MELIHAT DAFTAR FILE SETELAH HAPUS -----")
    response = client.list_files("/")
    if response: print(response)


if __name__ == "__main__":
    main()
