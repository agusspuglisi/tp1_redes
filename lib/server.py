import socket
import os
import logging
import threading

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
                client_thread = threading.Thread(target=server_handle_request, args=(s_socket, data, addr, storage, protocol))
                client_thread.start()
           
        except Exception as e:
            logging.error(f"Server error: {str(e)}")

def server_handle_request(sock, data, addr, storage_dir, protocol):
    try:
        if data.startswith(b"UPLOAD"):
            filename = data[6:].decode()
            filepath = os.path.join(storage_dir, filename)
            # if protocol == 'saw':
            #     stop_and_wait_receive(sock, addr, filepath)
            # else if protocol == "sr":
            #     selective_repeat_receive(sock, addr, filepath)
            start_upload(sock, addr, filepath) # Esto no iria
            
        elif data.startswith(b"DOWNLOAD"):
            filename = data[8:].decode()
            filepath = os.path.join(storage_dir, filename)
            # if protocol == 'saw':
            #     stop_and_wait_send(sock, addr, filepath)
            # else if protocol == "sr":
            #     selective_repeat_send(sock, addr, filepath)
            start_download(sock, addr, filepath) # Esto tampoco
            
    except Exception as e:
        logging.error(f"Request handling error: {str(e)}")

def start_upload(sock, addr, filepath):
    sock.sendto(b"READY", addr)
    
    with open(filepath, 'wb') as f:
        while True:
            data, _ = sock.recvfrom(1024)
            if data == b"EOF":
                break
            f.write(data)

def start_download(sock, addr, filepath):
    if not os.path.exists(filepath):
        sock.sendto(b"NOTFOUND", addr)
        return
        
    sock.sendto(b"FOUND", addr)
    with open(filepath, 'rb') as f:
        while (chunk := f.read(1024)):
            sock.sendto(chunk, addr)
    sock.sendto(b"EOF", addr)

def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose: level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)

def validate_storage(path):
    os.makedirs(path, exist_ok=True)
    if not os.path.isdir(path):
        raise ValueError(f"Invalid storage path: {path}")