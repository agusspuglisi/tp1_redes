import socket
import os
import logging

def encode_command(file_name, command):
    if command == "upload":
        return f"UPLOAD{file_name}".encode()
    elif command == "download":
        return f"DOWNLOAD{file_name}".encode()

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
            upload_file(args, c_sock) # Esto no va, se llamaria al handle_upload, se validarian los parametros y se llamaria al protocolo que corresponda
            # client_handle_upload(c_sock, addr, args.src, protocol)
        
        elif command == "download":
            if response == b"NOTFOUND":
                logging.error("File not found on server")
                return
            # filepath = os.path.join(args.dst, args.name)
            # client_handle_download(c_sock, addr, filepath, protocol)



def upload_file(args, sock):
    validate_file(args.src)

    with open(args.src, 'rb') as f:
        while (chunk := f.read(1024)):
            sock.sendto(chunk, (args.host, args.port))
        sock.sendto(b"EOF", (args.host, args.port))

def download_file(args):
    setup_logging(args)
    validate_path(args.dst)
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(f"DOWNLOAD{args.name}".encode(), (args.host, args.port))
        response = sock.recv(1024)
        
        if response == b"NOTFOUND":
            logging.error("File not found on server")
            return
            
        filepath = os.path.join(args.dst, args.name)
        with open(filepath, 'wb') as f:
            while True:
                data = sock.recv(1024)
                if data == b"EOF":
                    break
                f.write(data)



def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose: level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)

def validate_file(path):
    if not os.path.isfile(path):
        raise ValueError(f"Source file not found: {path}")

def validate_path(path):
    os.makedirs(path, exist_ok=True)