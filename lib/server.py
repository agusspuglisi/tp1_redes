import socket
import os
import logging
import threading
from protocols.stop_and_wait import stop_and_wait_receive, stop_and_wait_send
from protocols.selective_repeat import selective_repeat_receive, selective_repeat_send


def run_server(args):
    host, port = args.host, args.port
    storage, protocol = args.storage, args.protocol
    
    setup_logging(args)
    validate_storage(storage)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_socket:
        try:
            s_socket.bind((host, port))
            print("Server started on {}:{}".format(host, port))
            
            while True:
                data, addr = s_socket.recvfrom(1024)
                client_thread = threading.Thread(target=server_handle_request, 
                                                 args=(s_socket, data, addr, storage, protocol), 
                                                 daemon=True)
                client_thread.start()
           
        except Exception as e:
            logging.error(f"Server error: {str(e)}")


def server_handle_request(sock, data, addr, storage_dir, protocol):
    try:
        if data.startswith(b"UPLOAD"):
            filename = data[6:].decode()
            filepath = os.path.join(storage_dir, filename)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tmp_sock:
                tmp_sock.bind(('', 0)) 
                tmp_port = tmp_sock.getsockname()[1]
                sock.sendto(f"READY:{tmp_port}".encode(), addr)
                if protocol == 'saw':
                    stop_and_wait_receive(tmp_sock, addr, filepath)
                elif protocol == "sr":
                    selective_repeat_receive(tmp_sock, addr, filepath)
            
        elif data.startswith(b"DOWNLOAD"):
            filename = data[8:].decode()
            filepath = os.path.join(storage_dir, filename)
            if not os.path.exists(filepath):
                sock.sendto(b"NOTFOUND", addr)
                return
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tmp_sock:
                tmp_sock.bind(('', 0))
                tmp_port = tmp_sock.getsockname()[1]
                sock.sendto(f"FOUND:{tmp_port}".encode(), addr)

                if protocol == 'saw':
                    stop_and_wait_send(tmp_sock, addr, filepath)
                elif protocol == "sr":
                    selective_repeat_send(sock, addr, filepath)
            
    except Exception as e:
        logging.error(f"Request handling error: {str(e)}")

def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose: 
        level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)


def validate_storage(path):
    os.makedirs(path, exist_ok=True)
    if not os.path.isdir(path):
        raise ValueError(f"Invalid storage path: {path}")
