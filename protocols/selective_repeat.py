import socket
import logging
import time
from protocols.package import Package


WINDOW_SIZE = 8
CHUNK_SIZE = 4096
TIMEOUT = 0.5  # segundos
HEADER_SIZE = 2
SEQ_MODULO = 2 * WINDOW_SIZE

# Al usar SEQ_MODULO = 2 * WINDOW_SIZE, Selective Repeat asegura que no habrá ambigüedad 
# ni solapamiento en los números de secuencia entre paquetes nuevos y viejos.

def selective_repeat_send(sock, addr, filepath):
    sock.settimeout(TIMEOUT)
    seq_base = 0#primer elemento
    next_seq = 0
    buffer = {}  # Contiene los paquetes enviados pero pendientes de confirmacion
    timers = {}
    acks_received = set()
    eof_sent = False
    eof_seq = None # Me guardo el numero del EOF para enviarlo al final
    
    
    total_bytes = 0
    retransmissions = 0
    start_time = time.time()
    last_log_time = start_time
    condicion_corte=False
    logging.info(f"Starting file transfer using Selective Repeat protocol: {filepath}")

    with open(filepath, 'rb') as f:
        #while not eof_sent or len(buffer) > 0:  # seq_base < next_seq
        while not (condicion_corte):
            
            # solo envia si nuevos paquetes si hay lugar en la ventana / envia hasta llenar ventana
            while len(buffer) < WINDOW_SIZE and not eof_sent:
                data = f.read(CHUNK_SIZE)
                if not data:
                    logging.info(f"EOF reached, sending EOF packet with seq={next_seq}")
                    eof_sent = True
                    eof_seq = next_seq
                    packet = Package(next_seq, True, b'')
                else:
                    total_bytes += len(data)
                    packet = Package(next_seq, False, data)
        
                    current_time = time.time()
                    if current_time - last_log_time > 2.0: 
                        logging.info(f"Window: {len(buffer)}/{WINDOW_SIZE}, Base: {seq_base}, Next: {next_seq}, Bytes: {total_bytes}")
                        last_log_time = current_time
                    
                sock.sendto(packet.to_bytes(), addr)
                buffer[next_seq] = packet
                timers[next_seq] = time.time() # inicia timer
                next_seq = (next_seq + 1) % SEQ_MODULO

            # escuchar ack´s
            if not condicion_corte:

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
                        retransmissions += 1
                        logging.debug(f"Timeout for packet {seq}, retransmitting")
                        sock.sendto(buffer[seq].to_bytes(), addr)
                        timers[seq] = time.time() # si se retrasmite, reinicia el timer

                # desliza la ventana
                while seq_base in acks_received: # and acks_received[seq_base]:
                    del buffer[seq_base]
                    del timers[seq_base]
                    acks_received.remove(seq_base)
                    seq_base = (seq_base + 1) % SEQ_MODULO
                    condicion_corte=not buffer and eof_sent
                    logging.debug(f"Window base advanced to {seq_base}")
            else:
                break

        # mandar un eof
        eof_ack_recv_tries = 0
        logging.info("Waiting for EOF acknowledgment")
        while eof_ack_recv_tries < 3:
            try:
                raw_ack, _ = sock.recvfrom(HEADER_SIZE)
                ack_packet = Package.from_bytes(raw_ack)
                if ack_packet.ack and ack_packet.seq_num == eof_seq:
                    logging.info("EOF acknowledged")
                    break
            except socket.timeout:
                logging.warning(f"EOF ACK timeout, retrying ({eof_ack_recv_tries+1}/3)")
                sock.sendto(Package(eof_seq, True, b'').to_bytes(), addr)
                eof_ack_recv_tries += 1
        
        duration = time.time() - start_time
        transfer_rate = total_bytes / (1024 * duration) if duration > 0 else 0
        
        logging.info(f"Transfer complete: {total_bytes} bytes sent in {duration:.2f}s")
        logging.info(f"Retransmissions: {retransmissions}, Transfer rate: {transfer_rate:.2f} KB/s")
        return total_bytes, duration, retransmissions
    
def selective_repeat_receive(sock, addr, filepath):
    
    sock.settimeout(None)

    expected_base = 0
    received = {}
    eof_received = False
    eof_seq = None
    
    
    total_bytes = 0
    duplicate_packets = 0
    start_time = time.time()
    last_log_time = start_time
    
    logging.info(f"Receiving file using Selective Repeat protocol: {filepath}")

    with open(filepath, 'wb') as f:
        while True:
            try:
                raw_data, sender = sock.recvfrom(CHUNK_SIZE + HEADER_SIZE)
                packet = Package.from_bytes(raw_data)
                
                seq = packet.seq_num
                
                # envia ack siempre
                ack = Package(seq, True, b'')
                sock.sendto(ack.to_bytes(), addr)
                logging.debug(f"Sent ACK for packet {seq}")

                
                if packet.data == b'': # EOF detectado
                    logging.info(f"EOF packet received with seq={seq}")
                    eof_received = True
                    eof_seq = seq
                    if seq == expected_base:
                        sock.sendto(Package(eof_seq, True, b'').to_bytes(), addr)
                        logging.info("All data received before EOF, transfer complete")
                        break   # Ya se recibio todo lo anterior en orden
                    else:
                        logging.info("Waiting for remaining packets before EOF")
                        continue

                # Guardo cualquier paquete valido en received
                if (seq - expected_base + SEQ_MODULO) % SEQ_MODULO < WINDOW_SIZE:
                    received[seq] = packet.data

                
                
                current_time = time.time()
                if current_time - last_log_time > 2.0:
                    logging.info(f"Received: {len(received)} packets, Base: {expected_base}, Bytes: {total_bytes}")
                    last_log_time = current_time

                # escribe en orden
                while expected_base in received:
                    f.write(received[expected_base])
                    del received[expected_base]
                    expected_base = (expected_base + 1) % SEQ_MODULO
                    logging.debug(f"Base advanced to {expected_base}")

                    if eof_received and expected_base == eof_seq:
                        logging.info("All data received and EOF processed")
                        duration = time.time() - start_time
                        transfer_rate = total_bytes / (1024 * duration) if duration > 0 else 0
                        
                        logging.info(f"Reception complete: {total_bytes} bytes received in {duration:.2f}s")
                        logging.info(f"Duplicate packets: {duplicate_packets}, Transfer rate: {transfer_rate:.2f} KB/s")
                        return total_bytes, duration, duplicate_packets
                        
            except socket.timeout:
                continue


