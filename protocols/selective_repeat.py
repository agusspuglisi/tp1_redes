import socket
import time
from protocols.package import Package

WINDOW_SIZE = 4
CHUNK_SIZE = 256
TIMEOUT = 5.0  # segundos
HEADER_SIZE = 2
SEQ_MODULO = 2 * WINDOW_SIZE

# Al usar SEQ_MODULO = 2 * WINDOW_SIZE, Selective Repeat asegura que no habrá ambigüedad 
# ni solapamiento en los números de secuencia entre paquetes nuevos y viejos.

def selective_repeat_send(sock, addr, filepath):
    sock.settimeout(0.1)
    seq_base = 0
    next_seq = 0
    buffer = {}  # Contiene los paquetes enviados pero pendientes de confirmacion
    timers = {}
    acks_received = set()
    eof_sent = False
    eof_seq = None  # Me guardo el numero del EOF para enviarlo al final

    with open(filepath, 'rb') as f:
        while not eof_sent or len(buffer) > 0:  # seq_base < next_seq
            # solo envia si nuevos paquetes si hay lugar en la ventana / envia hasta llenar ventana
            while len(buffer) < WINDOW_SIZE and not eof_sent:
                data = f.read(CHUNK_SIZE)
                if not data: 
                    eof_sent = True
                    eof_seq = next_seq
                    packet = Package(next_seq, False, b'')
                else:
                    packet = Package(next_seq, False, data)
                    
                sock.sendto(packet.to_bytes(), addr)
                buffer[next_seq] = packet
                timers[next_seq] = time.time() # incia timer
                next_seq=(next_seq+1) % SEQ_MODULO

            # escuchar ack´s
            try:
                raw_ack, _ = sock.recvfrom(HEADER_SIZE)
                ack_packet = Package.from_bytes(raw_ack)
                if ack_packet.ack and ack_packet.seq_num in buffer:
                    acks_received.add(ack_packet.seq_num)
            except socket.timeout:
                pass

            # retrasmision por timeout
            for seq in list(buffer):
                if seq not in acks_received and (time.time() - timers[seq] > TIMEOUT):
                    sock.sendto(buffer[seq].to_bytes(), addr)
                    timers[seq] = time.time() # si se retrasmite, reinicia el timer

            # desliza la ventana
            while seq_base in acks_received: # and acks_received[seq_base]:
                del buffer[seq_base]
                del timers[seq_base]
                acks_received.remove(seq_base)
                seq_base = (seq_base + 1) % SEQ_MODULO

        # mandar un eof
        # eof_packet = Package(next_seq, False, b'')
        while True:
            try:
                raw_ack, _ = sock.recvfrom(HEADER_SIZE)
                ack_packet = Package.from_bytes(raw_ack)
                if ack_packet.ack and ack_packet.seq_num == eof_seq:
                    break
            except socket.timeout:
                sock.sendto(Package(eof_seq, False, b'').to_bytes(), addr) # Ver

def selective_repeat_receive(sock, addr, filepath):
    print("[SR RECV] Recibiendo archivo usando Selective Repeat...")
    expected_base = 0
    received = {}
    eof_received = False
    eof_seq = None

    with open(filepath, 'wb') as f:
        while True:
            try:
                raw_data, sender = sock.recvfrom(CHUNK_SIZE + HEADER_SIZE)
                packet = Package.from_bytes(raw_data)

                seq = packet.seq_num

                # envia ack siempre
                ack = Package(seq, True, b'')
                sock.sendto(ack.to_bytes(), addr)

                if packet.data == b'':  # EOF detectado
                    eof_received = True
                    eof_seq = seq
                    if seq == expected_base:
                        break  # Ya se recibio todolo anterior en orden
                    else:
                        continue

                # Guardo cualquierpaquete valido en recived
                if (seq - expected_base + SEQ_MODULO) % SEQ_MODULO < WINDOW_SIZE:
                    received[seq] = packet.data


                # escribe en orden
                while expected_base in received:
                    f.write(received[expected_base])
                    del received[expected_base]
                    expected_base = (expected_base + 1) % SEQ_MODULO

                    if eof_received and expected_base == eof_seq:
                        return  # EOF recibido y procesado
            except socket.timeout:
                continue