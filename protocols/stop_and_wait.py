# Send -> Leo de a chunks
# -> Mando cada chunk y espero ACK
# -> Si no llega ack retransmito
# -> Al terminar archivo mando paquete vacio

# Receive -> Leo, escribo y mando ACK por c/chunk recibido
# -> Cuando el paquete viene vacio significa EOF

# Si ack=True y el seq_num coincide el fragmento llego bien
    
import socket
from protocols.package import Package

def stop_and_wait_send(sock, addr, filepath):
    sock.settimeout(1.0)
    seq_num = 0
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(256)
            packet = Package(seq_num, False, data)
            while True:
                sock.sendto(packet.to_bytes(), addr)
                try:
                    raw_ack, _ = sock.recvfrom(2)
                    ack_packet = Package.from_bytes(raw_ack)
                    if ack_packet.ack and ack_packet.seq_num == seq_num:
                        print(f"ACK received for packet {seq_num}")
                        seq_num = 1 - seq_num
                        break
                except socket.timeout:
                    continue
            if not data:
                print("File transfer complete.")
                break


def stop_and_wait_receive(sock, addr, filepath):
    expected_seq = 0
    with open(filepath, 'wb') as f:
        while True:
            raw_data, sender = sock.recvfrom(258)
            packet = Package.from_bytes(raw_data)
            if packet.seq_num == expected_seq:
                if not packet.data:
                    ack = Package(expected_seq, True, b'')
                    sock.sendto(ack.to_bytes(), addr)
                    print(f"ACK sent for empty packet, indicating EOF {expected_seq}")
                    break
                f.write(packet.data)
                ack = Package(expected_seq, True, b'')
                sock.sendto(ack.to_bytes(), addr)
                print(f"ACK sent for packet {expected_seq}")
                expected_seq = 1 - expected_seq
            else:
                expected_seq_alt = 1 - expected_seq
                ack = Package(expected_seq_alt , True, b'')
                sock.sendto(ack.to_bytes(), addr)
