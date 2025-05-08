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
                client_thread = threading.Thread(
                    target=server_handle_request,
                    args=(s_socket, data, addr, storage, protocol),
                    daemon=True,
                )
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
    client_ip, client_port = addr
    transfer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    transfer_sock.settimeout(2.0)
    transfer_sock.bind(("", 0))
    transfer_port = transfer_sock.getsockname()[1]

    logging.info(f"New connection from {client_ip}:{client_port}")

    if three_way_handshake(transfer_sock, addr, data):
        logging.info(
            f"Handshake successful with {client_ip}:{client_port}, transfer port: {transfer_port}"
        )

        try:
            msg, _ = transfer_sock.recvfrom(1024)

            if msg.startswith(b"UPLOAD"):
                filename = msg[6:].decode()
                filepath = os.path.join(storage_dir, filename)

                logging.info(
                    f"Upload request for '{filename}' from {client_ip}:{client_port}"
                )
                sock.sendto(f"READY:{transfer_port}".encode(), addr)

                if protocol == "saw":
                    total_bytes, duration, duplicates = stop_and_wait_receive(
                        transfer_sock, addr, filepath
                    )
                elif protocol == "sr":
                    total_bytes, duration, duplicates = selective_repeat_receive(
                        transfer_sock, addr, filepath
                    )

                filesize_kb = total_bytes / 1024
                transfer_rate = filesize_kb / duration if duration > 0 else 0

                logging.info(
                    f"Upload complete: '{filename}', {filesize_kb:.2f} KB, {transfer_rate:.2f} KB/s"
                )

            elif msg.startswith(b"DOWNLOAD"):
                filename = msg[8:].decode()
                filepath = os.path.join(storage_dir, filename)

                if not os.path.exists(filepath):
                    logging.warning(
                        f"Download request failed: File '{filename}' not found"
                    )
                    sock.sendto(b"NOTFOUND", addr)
                    return

                filesize = os.path.getsize(filepath) / 1024  # KB
                logging.info(
                    f"Download request for '{filename}' ({filesize:.2f} KB) from {client_ip}:{client_port}"
                )
                sock.sendto(f"FOUND:{transfer_port}".encode(), addr)

                if protocol == "saw":
                    total_bytes, duration, retransmissions = stop_and_wait_send(
                        transfer_sock, addr, filepath
                    )
                elif protocol == "sr":
                    total_bytes, duration, retransmissions = selective_repeat_send(
                        transfer_sock, addr, filepath
                    )

                transfer_rate = (total_bytes / 1024) / duration if duration > 0 else 0

                logging.info(
                    f"Download complete: '{filename}', {total_bytes/1024:.2f} KB, {transfer_rate:.2f} KB/s"
                )

        except Exception as e:
            logging.error(
                f"Error handling request from {client_ip}:{client_port}: {str(e)}"
            )
    else:
        logging.warning(f"Handshake failed with {client_ip}:{client_port}")


def setup_logging(args):
    level = logging.INFO if not args.quiet else logging.WARNING
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)


def validate_storage(path):
    os.makedirs(path, exist_ok=True)
    if not os.path.isdir(path):
        raise ValueError(f"Invalid storage path: {path}")
