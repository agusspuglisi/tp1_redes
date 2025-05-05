import socket
import time
import logging
import threading
from protocols.package import Package

WINDOW_SIZE = 50
TIMEOUT = 0.5
CHUNK_SIZE = 4096
MAX_RETRIES = 10

def selective_repeat_send(sock: socket.socket, addr, filepath: str):
    sock.settimeout(TIMEOUT)
    
    # Read file and create packets
    packets = []
    seq = 0
    file_size = 0
    
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                packets.append(Package(seq_num=seq, ack=False, data=b'EOF'))
                break
            file_size += len(data)
            packets.append(Package(seq_num=seq, ack=False, data=data))
            seq += 1
    
    logging.info(f"Sending file: {file_size/1024/1024:.2f} MB, {len(packets)-1} packets")
    
    base = 0
    next_seq = 0
    acked = set()
    window_size = WINDOW_SIZE
    
    # For tracking performance
    start_time = time.time()
    last_report_time = start_time
    last_report_base = 0
    
    packet_sent_times = {}
    packet_retry_counts = {}
    
    # Use a thread to listen for ACKs
    ack_queue = []
    ack_lock = threading.Lock()
    stop_thread = threading.Event()
    
    def receive_acks():
        while not stop_thread.is_set():
            try:
                raw, _ = sock.recvfrom(2048) 
                ack_pkt = Package.from_bytes(raw)
                
                if ack_pkt.ack and ack_pkt.data:
                    with ack_lock:
                        ack_queue.append(ack_pkt)
            except socket.timeout:
                pass
            except Exception as e:
                logging.error(f"ACK receiver error: {e}")
    
    # receiver thread
    ack_thread = threading.Thread(target=receive_acks)
    ack_thread.daemon = True
    ack_thread.start()
    
    try:
        last_progress_time = time.time()
        
        while base < len(packets):
            current_time = time.time()
            
            # Process received ACKs
            with ack_lock:
                while ack_queue:
                    ack_pkt = ack_queue.pop(0)
                    try:
                        received_seqs_str = ack_pkt.data.decode()
                        received_seqs = list(map(int, received_seqs_str.split(','))) if ',' in received_seqs_str else [int(received_seqs_str)]
                        
                        for seq_num in received_seqs:
                            if seq_num < len(packets):
                                acked.add(seq_num)
                                packet_retry_counts[seq_num] = 0
                    except Exception as e:
                        logging.error(f"Error processing ACK data: {e}")
            
            # Move window based on acknowledged packets
            old_base = base
            while base < len(packets) and base in acked:
                packet_sent_times.pop(base, None)
                packet_retry_counts.pop(base, None)
                acked.remove(base)
                base += 1
            
            if base > old_base:
                # Progress made
                last_progress_time = current_time
                window_size = min(WINDOW_SIZE, window_size + 1)
            
            # Check for timeouts on individual packets
            expired_packets = [seq_num for seq_num, sent_time in list(packet_sent_times.items()) 
                              if seq_num >= base and current_time - sent_time > TIMEOUT]
            
            # Retransmit expired packets
            if expired_packets:
                for seq_num in sorted(expired_packets):
                    if seq_num < len(packets) and seq_num >= base:
                        retry_count = packet_retry_counts.get(seq_num, 0) + 1
                        packet_retry_counts[seq_num] = retry_count
                        
                        if retry_count >= MAX_RETRIES:
                            window_size = max(5, window_size // 2)
                            
                        pkt = packets[seq_num]
                        try:
                            sock.sendto(pkt.to_bytes(), addr)
                            packet_sent_times[seq_num] = current_time
                            time.sleep(0.001)  # Small delay to prevent network congestion
                        except socket.error as e:
                            logging.error(f"Socket error during retransmission: {e}")
            
            # Check for stall
            if base == old_base and current_time - last_progress_time > 5.0:
                window_size = max(5, window_size // 2)
                next_seq = base  # Reset sending position
                last_progress_time = current_time
                logging.warning(f"Stalled at sequence {base}, reducing window size to {window_size}")
                packet_sent_times.clear()
                packet_retry_counts.clear()
            
            # Send new packets in window
            while next_seq < min(base + window_size, len(packets)):
                if next_seq in acked:
                    next_seq += 1
                    continue
                    
                pkt = packets[next_seq]
                try:
                    sock.sendto(pkt.to_bytes(), addr)
                    packet_sent_times[next_seq] = current_time
                    packet_retry_counts.setdefault(next_seq, 0)
                    next_seq += 1
                    
                    # Small delay every few packets
                    if next_seq % 10 == 0:
                        time.sleep(0.001)
                        
                except socket.error as e:
                    logging.error(f"Socket error while sending: {e}")
                    window_size = max(5, window_size // 2)
                    break
                
            # Small sleep to avoid tight loop
            if base == old_base and not expired_packets:
                time.sleep(0.01)
    
    finally:
        # Clean up thread
        stop_thread.set()
        ack_thread.join(timeout=1.0)
        
        # Send EOF markers repeatedly
        eof_pkt = packets[-1]
        fin_pkt = Package(seq_num=len(packets), ack=False, data=b'FIN')
        for _ in range(10):
            try:
                sock.sendto(eof_pkt.to_bytes(), addr)
                sock.sendto(fin_pkt.to_bytes(), addr)
                time.sleep(0.1)
            except:
                pass
    
    total_time = time.time() - start_time
    throughput = file_size / (1024 * 1024 * total_time) if total_time > 0 else 0
    logging.info(f"Transfer completed in {total_time:.2f} seconds. Throughput: {throughput:.2f} MB/s")

def selective_repeat_receive(sock: socket.socket, addr, filepath: str):
    sock.settimeout(TIMEOUT * 2)
    expected_seq = 0
    buffer = {}
    last_progress_time = time.time()
    file_size = 0
    start_time = time.time()
    received_eof = False
    max_seq_seen = -1
    last_ack_time = 0
    
    with open(filepath, 'wb') as f:
        while True:
            try:
                current_time = time.time()
                
                # Send ACKs periodically
                if current_time - last_ack_time > 0.1:
                    ack_list = sorted(list(buffer.keys()))
                    if ack_list:
                        # If large list, prioritize important packets
                        if len(ack_list) > 50:
                            critical_range = list(range(max(0, expected_seq - 5), expected_seq + 45))
                            critical_packets = [s for s in critical_range if s in buffer]
                            higher_packets = sorted([s for s in ack_list if s > expected_seq + 45])[:20]
                            ack_list = critical_packets + higher_packets
                        
                        ack_data = ','.join(map(str, ack_list))
                        ack_pkt = Package(seq_num=expected_seq, ack=True, data=ack_data.encode())
                        sock.sendto(ack_pkt.to_bytes(), addr)
                        last_ack_time = current_time
                
                # Receive packet
                raw, client_addr = sock.recvfrom(CHUNK_SIZE + 256)
                addr = client_addr  # Update address in case it changed
                pkt = Package.from_bytes(raw)
                
                if pkt.data == b'FIN':
                    fin_ack = Package(seq_num=pkt.seq_num, ack=True, data=f"{pkt.seq_num}".encode())
                    sock.sendto(fin_ack.to_bytes(), addr)
                    if received_eof and expected_seq > max_seq_seen:
                        break
                    continue
                
                # Track highest sequence number
                if pkt.seq_num > max_seq_seen:
                    max_seq_seen = pkt.seq_num
                
                # Check for EOF
                if pkt.data == b'EOF':
                    received_eof = True
                    eof_ack = Package(seq_num=pkt.seq_num, ack=True, data=f"{pkt.seq_num}".encode())
                    sock.sendto(eof_ack.to_bytes(), addr)
                    
                    if expected_seq == pkt.seq_num:
                        elapsed = time.time() - start_time
                        speed = file_size / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        logging.info(f"Transfer completed. {file_size/1024/1024:.2f} MB in {elapsed:.2f}s ({speed:.2f} MB/s)")
                        return
                
                # Store packet if not already in buffer
                if pkt.seq_num not in buffer:
                    buffer[pkt.seq_num] = pkt.data
                    if pkt.data != b'EOF':
                        file_size += len(pkt.data)
                
                last_progress_time = time.time()
                
                # Send immediate ACK for this packet
                ack_list = sorted(list(buffer.keys()))
                ack_data = ','.join(map(str, ack_list))
                ack_pkt = Package(seq_num=expected_seq, ack=True, data=ack_data.encode())
                sock.sendto(ack_pkt.to_bytes(), addr)
                last_ack_time = current_time
                
                # Write packets in order
                while expected_seq in buffer:
                    data = buffer.pop(expected_seq)
                    if data == b'EOF':
                        elapsed = time.time() - start_time
                        speed = file_size / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        logging.info(f"Transfer completed. {file_size/1024/1024:.2f} MB in {elapsed:.2f}s ({speed:.2f} MB/s)")
                        
                        # Send final acknowledgment multiple times
                        for _ in range(5):
                            sock.sendto(ack_pkt.to_bytes(), addr)
                            time.sleep(0.05)
                        return
                    f.write(data)
                    expected_seq += 1
                
            except socket.timeout:
                # Send ACKs on timeout
                if buffer:
                    ack_list = sorted(list(buffer.keys()))
                    ack_data = ','.join(map(str, ack_list))
                    ack_pkt = Package(seq_num=expected_seq, ack=True, data=ack_data.encode())
                    sock.sendto(ack_pkt.to_bytes(), addr)
                
                # Check if we've received EOF and written all data
                if received_eof and expected_seq > max_seq_seen:
                    logging.info(f"Transfer completed. {file_size/1024/1024:.2f} MB received.")
                    return
                
                # Handle timeout
                if time.time() - last_progress_time > 8.0:
                    if expected_seq > 0:
                        if received_eof:
                            logging.info(f"Transfer completed (EOF received). {file_size/1024/1024:.2f} MB received.")
                        else:
                            logging.warning(f"Transfer timeout after receiving {expected_seq} packets ({file_size/1024/1024:.2f} MB).")
                        return
                    else:
                        logging.error("Fatal timeout - no packets received")
                        break
            
            except Exception as e:
                logging.error(f"Unexpected error in receiver: {e}")