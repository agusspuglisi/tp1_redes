import socket
import threading

def handle_client(message, client_address, s_socket):
    print(f"Received message from {client_address}: {message.decode()}")
    s_socket.sendto(b"Message received", client_address)

def run_server(args):
    host, port = args.host, args.port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_socket:
        s_socket.bind((host, port))
        print(f"Server listening on {host}:{port}")

        while True:
            message, client_address = s_socket.recvfrom(2048)
            client_thread = threading.Thread(target=handle_client, args=(message, client_address, s_socket))
            client_thread.start()