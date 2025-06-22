import sys
import os
import os.path
import uuid
from glob import glob
from datetime import datetime
import json # Digunakan untuk format daftar file

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.types['.json'] = 'application/json' # Tambahkan tipe untuk JSON

    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append(f"HTTP/1.0 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        for kk in headers:
            resp.append(f"{kk}:{headers[kk]}\r\n")
        resp.append("\r\n")

        response_headers = ''.join(resp)

        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()

        response = response_headers.encode() + messagebody
        return response

    def proses(self, data):
        # Pisahkan header dan body
        # Ini penting untuk metode seperti PUT dan POST yang membawa data di body
        request_parts = data.split("\r\n\r\n", 1)
        requests = request_parts[0].split("\r\n")
        body = request_parts[1] if len(request_parts) > 1 else ""
        
        baris = requests[0]
        all_headers = {h.split(": ")[0]: h.split(": ")[1] for h in requests[1:] if ': ' in h}

        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()

            if method == 'GET':
                return self.http_get(object_address, all_headers)
            elif method == 'POST':
                # Body dari request POST perlu diparsing jika ada
                return self.http_post(object_address, all_headers, body)
            # --- Fungsionalitas Baru ---
            elif method == 'LIST':
                return self.http_list(object_address, all_headers)
            elif method == 'PUT':
                return self.http_put(object_address, all_headers, body)
            elif method == 'DELETE':
                return self.http_delete(object_address, all_headers)
            else:
                return self.response(400, 'Bad Request', 'Metode tidak dikenali', {})
        except IndexError:
            return self.response(400, 'Bad Request', '', {})
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e), {})

    def http_get(self, object_address, headers):
        thedir = './'
        if object_address == '/':
            return self.response(200, 'OK', 'Ini adalah web server percobaan', {})

        object_address = object_address.lstrip('/')
        file_path = os.path.join(thedir, object_address)

        if not os.path.exists(file_path):
            return self.response(404, 'Not Found', '', {})
        
        # Jangan izinkan akses ke direktori di atasnya
        if not os.path.abspath(file_path).startswith(os.path.abspath(thedir)):
            return self.response(403, 'Forbidden', '', {})

        with open(file_path, 'rb') as fp:
            isi = fp.read()

        fext = os.path.splitext(file_path)[1]
        content_type = self.types.get(fext, 'application/octet-stream')

        headers = {'Content-type': content_type}
        return self.response(200, 'OK', isi, headers)

    def http_post(self, object_address, headers, body):
        # Fungsionalitas POST bisa dikembangkan di sini
        # Contoh: memproses data dari form
        return self.response(200, 'OK', f"Data POST diterima: {body}", {})

    # ----- METODE-METODE BARU -----

    def http_list(self, object_address, headers):
        """
        Menangani metode LIST untuk melihat daftar file dalam direktori.
        """
        thedir = './'
        dir_path_str = object_address.lstrip('/')
        dir_path = os.path.join(thedir, dir_path_str)

        # Validasi keamanan dasar
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            return self.response(404, 'Not Found', 'Direktori tidak ditemukan', {})
        if not os.path.abspath(dir_path).startswith(os.path.abspath(thedir)):
            return self.response(403, 'Forbidden', '', {})

        try:
            files = os.listdir(dir_path)
            # Menggunakan JSON untuk output yang terstruktur
            file_list_json = json.dumps({"directory": dir_path_str, "files": files})
            return self.response(200, 'OK', file_list_json, {'Content-Type': 'application/json'})
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e), {})

    def http_put(self, object_address, headers, body):
        """
        Menangani metode PUT untuk mengunggah (upload) file.
        """
        thedir = './'
        file_path_str = object_address.lstrip('/')
        file_path = os.path.join(thedir, file_path_str)

        # Validasi keamanan dasar: jangan menimpa file di luar direktori kerja
        if not os.path.abspath(file_path).startswith(os.path.abspath(thedir)):
            return self.response(403, 'Forbidden', '', {})
        
        # Pastikan direktori client ada jika targetnya di sana
        if 'client/' in file_path_str:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            # Body sudah dalam bentuk string, perlu di-encode kembali ke bytes untuk ditulis
            with open(file_path, 'wb') as f:
                f.write(body.encode('utf-8')) # Asumsi body adalah utf-8 string
            return self.response(201, 'Created', f'File {file_path_str} berhasil dibuat', {})
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e), {})

    def http_delete(self, object_address, headers):
        """
        Menangani metode DELETE untuk menghapus file.
        """
        thedir = './'
        file_path_str = object_address.lstrip('/')
        file_path = os.path.join(thedir, file_path_str)

        if not os.path.exists(file_path):
            return self.response(404, 'Not Found', 'File tidak ditemukan', {})
        
        # Validasi keamanan
        if not os.path.abspath(file_path).startswith(os.path.abspath(thedir)):
            return self.response(403, 'Forbidden', '', {})
        if os.path.isdir(file_path):
            return self.response(400, 'Bad Request', 'Tidak dapat menghapus direktori', {})

        try:
            os.remove(file_path)
            return self.response(200, 'OK', f'File {file_path_str} berhasil dihapus', {})
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e), {})


if __name__ == "__main__":
    httpserver = HttpServer()
    # Contoh penggunaan dasar, tidak akan berfungsi penuh tanpa server nyata
    d = httpserver.proses('GET /testing.txt HTTP/1.0\r\n\r\n')
    print(d.decode())
