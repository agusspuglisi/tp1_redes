import socket
import os
import logging

def upload_file(args):
    setup_logging(args)
    validate_file(args.src)
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(f"UPLOAD{args.name}".encode(), (args.host, args.port))
        response = sock.recv(1024)
        
        if response != b"READY":
            logging.error("Server not ready")
            return
            
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