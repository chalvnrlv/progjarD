import socket


def get_my_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        # Langsung gunakan IP dari getaddrinfo untuk koneksi
        koneksi = socket.getaddrinfo('www.its.ac.id', 80, proto=socket.IPPROTO_TCP)
        print(koneksi)
        
        # Ambil IP dan port dari hasil resolusi
        family, socktype, proto, canonname, sockaddr = koneksi[0]
        ip, port = sockaddr
        
        # Lakukan koneksi aktif
        s.connect((ip, port))
        print(f"Berhasil terkoneksi ke {ip}:{port}")
        
        # Kirim request HTTP sederhana (opsional)
        s.sendall(b"GET / HTTP/1.1\r\nHost: www.its.ac.id\r\n\r\n")
        response = s.recv(1024)
        print("Response:", response.decode()[:100])  # Cetak 100 karakter pertama
    except Exception as e:
        print("Error:", e)
    finally:
        s.close()


def get_my_info():
    hostname = socket.gethostname()
    print(f"hostname : {hostname}")

    ip_address = socket.gethostbyname(hostname)
    print(f"ipaddress: {ip_address}")

def get_remote_info():
    remote_host = 'www.espnfc.cosm'
    try:
        remote_host_ip = socket.gethostbyname(remote_host)
        print(f"ip address dari {remote_host} adalah {remote_host_ip}")
    except Exception as ee:
        print(f"ERROR : {str(ee)}")


if __name__=='__main__':
#    get_my_info()
#    get_remote_info()
    get_my_socket()
