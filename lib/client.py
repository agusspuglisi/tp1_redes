import socket
import os
import logging
from protocols.stop_and_wait import stop_and_wait_receive, stop_and_wait_send
from protocols.selective_repeat import selective_repeat_receive, selective_repeat_send

TIMEOUT = 0.5 

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

def three_way_handshake(socket, addr):
    socket.sendto(b"HI", addr)
    try:
        received, transfer_address = socket.recvfrom(6)
        if received.startswith(b"HI_ACK"):
            socket.sendto(b"ACK", transfer_address)
            return True, transfer_address
        else:
            logging.error("Invalid HI ACK message")
            return False, (0,0)
    except Exception as e:
        logging.error(f"Handshake error: {str(e)}")
    return False, (0,0)

def run_client(args, command):
    setup_logging(args)
    addr = (args.host, args.port)
    protocol = args.protocol

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c_sock:
        c_sock.settimeout(2.0)

        handshake_ok, transfer_address = three_way_handshake(c_sock, addr)
        if handshake_ok:
            logging.info("Handshake successful | Proceeding with transfer")
            encoded_command = encode_command(args.name, command)
            c_sock.sendto(encoded_command, transfer_address)        
            try:
                response, _ = c_sock.recvfrom(1024)
                
                if command == "upload":
                    logging.info(f"Uploading file: {args.src} -> {args.name}")
                    if not response.startswith(b"READY"):
                        logging.error("Server not ready")
                        return
                    client_handle_upload(c_sock, transfer_address, args.src, protocol)
                    logging.info("Upload completed successfully")
                
                elif command == "download":
                    logging.info(f"Downloading file: {args.name} -> {args.dst}")
                    if response == b"NOTFOUND":
                        logging.error("File not found on server")
                        return
                    elif response.startswith(b"FOUND"):
                        filepath = os.path.join(args.dst, args.name)
                        client_handle_download(c_sock, transfer_address, filepath, protocol)
                        logging.info("Download completed successfully")
            except socket.timeout:
                logging.error("Timeout in server response")
        else:
            logging.error("Handshake with server failed")



def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose: level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)


def validate_file(path):
    if not os.path.isfile(path):
        raise ValueError(f"Source file not found: {path}")


def validate_path(path):
    os.makedirs(path, exist_ok=True)
