import socket
import os
import logging
import threading
from protocols.stop_and_wait import stop_and_wait_receive, stop_and_wait_send
from protocols.selective_repeat import selective_repeat_receive, selective_repeat_send

TIMEOUT = 0.5

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

def three_way_handshake(socket, addr, data):
    if data.startswith(b"HI"):
        socket.sendto(b"HI_ACK", addr)
        try:
            received, _ = socket.recvfrom(3)
            if received.startswith(b"ACK"):
                return True
            else:
                logging.error("Invalid ACK message")
                return False
        except Exception as e:
            logging.error(e)
    else:
        logging.error("Invalid HI message")
        return False


def server_handle_request(sock, data, addr, storage_dir, protocol):
    transfer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    transfer_sock.settimeout(2.0)
    transfer_sock.bind(('', 0))
    transfer_port = transfer_sock.getsockname()[1]
    if three_way_handshake(transfer_sock, addr, data):
        msg, _ = transfer_sock.recvfrom(1024)
        try:
            if msg.startswith(b"UPLOAD"):
                filename = msg[6:].decode()
                filepath = os.path.join(storage_dir, filename)
                sock.sendto(f"READY:{transfer_port}".encode(), addr)
                if protocol == 'saw':
                    stop_and_wait_receive(transfer_sock, addr, filepath)
                elif protocol == "sr":
                    selective_repeat_receive(transfer_sock, addr, filepath)
            elif msg.startswith(b"DOWNLOAD"):
                filename = msg[8:].decode()
                filepath = os.path.join(storage_dir, filename)
                if not os.path.exists(filepath):
                    sock.sendto(b"NOTFOUND", addr)
                    return
                sock.sendto(f"FOUND:{transfer_port}".encode(), addr)
                if protocol == 'saw':
                    stop_and_wait_send(transfer_sock, addr, filepath)
                elif protocol == "sr":
                    selective_repeat_send(transfer_sock, addr, filepath)
        except Exception as e:
            logging.error(f"Request handling error: {str(e)}")
    else:
        logging.error("Handshake with client failed")

def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose: 
        level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)


def validate_storage(path):
    os.makedirs(path, exist_ok=True)
    if not os.path.isdir(path):
        raise ValueError(f"Invalid storage path: {path}")
