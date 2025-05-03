import socket
import threading
import time
from protocols.package import Package

WINDOW_SIZE = 4
CHUNK_SIZE = 1024
TIMEOUT = 1.0  # segundos

def selective_repeat_send(sock, addr, filepath):
    sock.settimeout(0.1)
    seq_base = 0
    next_seq = 0
    buffer = []
    timers = {}
    acks_received = {}
    eof_sent = False

    with open(filepath, 'rb') as f:
        while not eof_sent or seq_base < next_seq:
            # solo envia si nuevos paquetes si hay lugar en la ventana / envia hasta llenar ventana
            while next_seq < seq_base + WINDOW_SIZE:
                data = f.read(CHUNK_SIZE)
                if not data:
                    eof_sent = True
                    break
                packet = Package(next_seq, False, data)
                sock.sendto(packet.to_bytes(), addr)
                buffer.append((next_seq, packet))
                timers[next_seq] = time.time() # incia timer
                acks_received[next_seq] = False
                next_seq=(next_seq+1)%256

            # escuchar ack´s
            try:
                raw_ack, _ = sock.recvfrom(2)
                ack_packet = Package.from_bytes(raw_ack)
                if ack_packet.ack and ack_packet.seq_num in acks_received:
                    acks_received[ack_packet.seq_num] = True
            except socket.timeout:
                pass

            # retrasmision por timeout
            for seq, pkt in buffer:
                if not acks_received[seq] and time.time() - timers[seq] > TIMEOUT:
                    sock.sendto(pkt.to_bytes(), addr)
                    timers[seq] = time.time() # si se retrasmite, reinicia el timer

            # desliza la ventana
            while seq_base in acks_received and acks_received[seq_base]:
                del acks_received[seq_base]
                buffer = [(s, p) for s, p in buffer if s != seq_base]
                del timers[seq_base]
                seq_base += 1

        # mandar un eof
        eof_packet = Package(next_seq, False, b'')
        while True:
            sock.sendto(eof_packet.to_bytes(), addr)
            try:
                raw_ack, _ = sock.recvfrom(2)
                ack_packet = Package.from_bytes(raw_ack)
                if ack_packet.ack and ack_packet.seq_num == next_seq:
                    break
            except socket.timeout:
                continue

def selective_repeat_receive(sock, addr, filepath):
    print("[SR RECV] Recibiendo archivo usando Selective Repeat...")
    expected_base = 0
    received = {}
    received_flags = set()

    with open(filepath, 'wb') as f:
        while True:
            raw_data, sender = sock.recvfrom(1026)
            packet = Package.from_bytes(raw_data)

            seq = packet.seq_num

            # envia ack siempre
            ack = Package(seq, True, b'')
            sock.sendto(ack.to_bytes(), addr)

            if seq in received_flags:
                continue # duplicado

            if not packet.data:
                break # eof

            if expected_base <= seq < expected_base + WINDOW_SIZE:
                received[seq] = packet.data
                received_flags.add(seq)

                # escribe en orden
                while expected_base in received:
                    f.write(received[expected_base])
                    del received[expected_base]
                    expected_base += 1