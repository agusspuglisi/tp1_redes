import socket
import threading
from protocols.package import Package

WINDOW_SIZE = 5       
TIMEOUT = 1.0         
CHUNK_SIZE = 1024     


def selective_repeat_send(sock: socket.socket, addr, filepath: str):
    sock.settimeout(TIMEOUT)
    packets = []
    seq = 0
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(CHUNK_SIZE)
            # Sequence numbers are absolute indices 
            pkt = Package(seq_num=seq, ack=False, data=data)
            packets.append(pkt)
            seq += 1
            if not data:
                break

    base = 0            
    next_seq = 0        
    acked = set()       
    timers = {}         # seq_num -> Timer
    lock = threading.Lock()

    def start_timer(index):
        def timeout_handler():
            with lock:
                seq_num = packets[index].seq_num
                if seq_num not in acked:
                    sock.sendto(packets[index].to_bytes(), addr)
                    start_timer(index)
        timer = threading.Timer(TIMEOUT, timeout_handler)
        timer.daemon = True
        timer.start()
        timers[packets[index].seq_num] = timer

    total = len(packets)
    while base < total:
        while next_seq < base + WINDOW_SIZE and next_seq < total:
            pkt = packets[next_seq]
            sock.sendto(pkt.to_bytes(), addr)
            start_timer(next_seq)
            next_seq += 1

        # Wait for ACK
        try:
            raw, _ = sock.recvfrom(8 + 4)  # header + no payload
            ack_pkt = Package.from_bytes(raw)
            if ack_pkt.ack:
                seq_num = ack_pkt.seq_num
                with lock:
                    if seq_num not in acked:
                        acked.add(seq_num)
                        if seq_num in timers:
                            timers[seq_num].cancel()
                while base < total and packets[base].seq_num in acked:
                    base += 1
        except socket.timeout:
            # ignore and allow timers to trigger retransmissions
            pass


def selective_repeat_receive(sock: socket.socket, addr, filepath: str):
    sock.settimeout(None)
    with open(filepath, 'wb') as f:
        while True:
            raw, peer = sock.recvfrom(CHUNK_SIZE + 1024)
            pkt = Package.from_bytes(raw)
            ack_pkt = Package(seq_num=pkt.seq_num, ack=True, data=b'')
            sock.sendto(ack_pkt.to_bytes(), peer)

            if pkt.data == b'':
                break
            f.write(pkt.data)
