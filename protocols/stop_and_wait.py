# Send -> Leo de a chunks
# -> Mando cada chunk y espero ACK
# -> Si no llega ack retransmito
# -> Al terminar archivo mando paquete vacio

# Receive -> Leo, escribo y mando ACK por c/chunk recibido
# -> Cuando el paquete viene vacio significa EOF

# Si ack=True y el seq_num coincide el fragmento llego bien

import socket
from protocols.package import Package
import logging
import time

TIMEOUT = 0.1
CHUCK_SIZE = 4096


def stop_and_wait_send(sock, addr, filepath):
    sock.settimeout(TIMEOUT)
    seq_num = 0
    retransmissions = 0
    total_bytes = 0
    start_time = time.time()

    logging.info(f"Starting file transfer using Stop & Wait protocol: {filepath}")

    with open(filepath, "rb") as f:
        while True:
            data = f.read(CHUCK_SIZE)
            packet = Package(seq_num, False, data)

            if data:
                total_bytes += len(data)
                logging.debug(f"Sending packet seq={seq_num}, size={len(data)} bytes")
            else:
                logging.info("Sending EOF packet")

            attempts = 0
            while True:
                sock.sendto(packet.to_bytes(), addr)
                attempts += 1

                try:
                    raw_ack, _ = sock.recvfrom(2)
                    ack_packet = Package.from_bytes(raw_ack)
                    if ack_packet.ack and ack_packet.seq_num == seq_num:
                        if attempts > 1:
                            logging.debug(
                                f"ACK received for packet {seq_num} after {attempts} attempts"
                            )
                        seq_num = 1 - seq_num
                        break
                except socket.timeout:
                    retransmissions += 1
                    if attempts <= 3:
                        logging.warning(
                            f"Timeout occurred, retransmitting packet {seq_num} (attempt {attempts})"
                        )
                    continue

            if not data:
                break

    duration = time.time() - start_time
    transfer_rate = total_bytes / (1024 * duration) if duration > 0 else 0

    logging.info(f"Transfer complete: {total_bytes} bytes sent in {duration:.2f}s")
    logging.info(
        f"Retransmissions: {retransmissions}, Transfer rate: {transfer_rate:.2f} KB/s"
    )
    return total_bytes, duration, retransmissions


def stop_and_wait_receive(sock, addr, filepath):
    sock.settimeout(None)
    expected_seq = 0
    total_bytes = 0
    duplicate_packets = 0
    start_time = time.time()

    logging.info(f"Receiving file using Stop & Wait protocol: {filepath}")

    with open(filepath, "wb") as f:
        while True:
            # try:
            raw_data, sender = sock.recvfrom(CHUCK_SIZE + 2)
            packet = Package.from_bytes(raw_data)
            data_len = len(packet.data) if packet.data else 0
            logging.debug(f"Received packet seq={expected_seq}, size={data_len} bytes")

            if packet.seq_num == expected_seq:
                if not packet.data:
                    logging.info("EOF packet received")
                    ack = Package(expected_seq, True, b"")
                    sock.sendto(ack.to_bytes(), addr)
                    break

                total_bytes += data_len

                f.write(packet.data)
                ack = Package(expected_seq, True, b"")
                sock.sendto(ack.to_bytes(), addr)
                expected_seq = 1 - expected_seq
            else:
                duplicate_packets += 1
                logging.debug(
                    f"Received duplicate packet seq={packet.seq_num}, expecting {expected_seq}"
                )
                expected_seq_alt = 1 - expected_seq
                ack = Package(expected_seq_alt, True, b"")
                sock.sendto(ack.to_bytes(), addr)
        # except socket.timeout:
        #    continue

    duration = time.time() - start_time
    transfer_rate = total_bytes / (1024 * duration) if duration > 0 else 0

    logging.info(f"Reception complete: {total_bytes} bytes received in {duration:.2f}s")
    logging.info(
        f"Duplicate packets: {duplicate_packets}, Transfer rate: {transfer_rate:.2f} KB/s"
    )
    return total_bytes, duration, duplicate_packets
