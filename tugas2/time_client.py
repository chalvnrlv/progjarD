import socket

# IP mesin1 dan port server
SERVER_IP = "172.16.16.101"
SERVER_PORT = 45000

# koneksi ke server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))
print(f"Terhubung ke server di {SERVER_IP}:{SERVER_PORT}")

try:
    # 1. Mengirim request TIME
    print("\n=> Mengirim request 'TIME'")
    # Kirim dengan newline (CRLF)
    request1 = "TIME\r\n"
    client_socket.sendall(request1.encode('utf-8'))

    # Menerima response dari server
    response1 = client_socket.recv(1024).decode('utf-8')
    print(f"<= Menerima response: {response1.strip()}")

    # 2. Mengirim request QUIT
    print("\n=> Mengirim request 'QUIT'")
    request2 = "QUIT\r\n"
    client_socket.sendall(request2.encode('utf-8'))
    print("Koneksi akan ditutup oleh server.")

finally:
    # Menutup socket klien
    client_socket.close()
    print("\nKoneksi klien ditutup.")