import socket
import os
import logging
from protocols.stop_and_wait import stop_and_wait_receive, stop_and_wait_send
from protocols.selective_repeat import selective_repeat_receive, selective_repeat_send

def encode_command(file_name, command):
    if command == "upload":
        return f"UPLOAD{file_name}".encode()
    elif command == "download":
        return f"DOWNLOAD{file_name}".encode()
    
def client_handle_download(sock, addr, filepath, protocol):
    validate_path(os.path.dirname(filepath))
    if protocol == "saw":
       stop_and_wait_receive(sock, addr, filepath)
    elif protocol == "sr":
        selective_repeat_receive(sock, addr, filepath)

def client_handle_upload(sock, addr, filepath, protocol):
    validate_file(filepath)
    if protocol == "saw":
       stop_and_wait_send(sock, addr, filepath)
    elif protocol == "sr":
        selective_repeat_send(sock, addr, filepath)

def run_client(args, command):
    setup_logging(args)
    addr = (args.host, args.port)
    protocol = args.protocol

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c_sock:
        c_sock.settimeout(2.0) # Setear constante para timeout

        encoded_command = encode_command(args.name, command)
        c_sock.sendto(encoded_command, addr)

        try:
            response, _ = c_sock.recvfrom(1024) # Setear cuantos bytes voy a recibir
        except socket.timeout:
            logging.error("Timeout in server response")
            return

        if command == "upload":
            if response != b"READY":
                logging.error("Server not ready")
                return
            client_handle_upload(c_sock, addr, args.src, protocol)
        
        elif command == "download":
            if response == b"NOTFOUND":
                logging.error("File not found on server")
                return
            elif response == b"FOUND":
                filepath = os.path.join(args.dst, args.name)
                client_handle_download(c_sock, addr, filepath, protocol)
            else:
                logging.error(f"Unexpected response: {response}")


def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose: level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)


def validate_file(path):
    if not os.path.isfile(path):
        raise ValueError(f"Source file not found: {path}")


def validate_path(path):
    os.makedirs(path, exist_ok=True)
