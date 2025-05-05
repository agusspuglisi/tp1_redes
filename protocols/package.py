class Package:
    def __init__(self, seq_num, ack, data):
        self.seq_num = seq_num
        self.ack = ack
        self.data = data
    
    def to_bytes(self):
        try:
            # Format: 4-byte seq_num, 1-byte ack flag, data
            seq_bytes = self.seq_num.to_bytes(4, byteorder='big')
            ack_byte = bytes([1 if self.ack else 0])
            return seq_bytes + ack_byte + self.data
        except Exception as e:
            print(f"Error in to_bytes: {e}")
            seq_bytes = (0 if self.seq_num is None else self.seq_num).to_bytes(4, byteorder='big')
            ack_byte = bytes([1 if self.ack else 0])
            return seq_bytes + ack_byte + (b'' if self.data is None else self.data)

    @staticmethod
    def from_bytes(raw_bytes):
        try:
            if len(raw_bytes) < 5:
                # Invalid packet, return a dummy package
                return Package(0, False, b'')
                
            seq_num = int.from_bytes(raw_bytes[0:4], byteorder='big')
            ack_flag = bool(raw_bytes[4])
            data = raw_bytes[5:]
            return Package(seq_num, ack_flag, data)
        except Exception as e:
            # Return a dummy package in case of error
            print(f"Error parsing package: {e}")
            return Package(0, False, b'')
    
    def __str__(self):
        """String representation for debugging"""
        if self.ack:
            return f"ACK Package(seq={self.seq_num}, data_len={len(self.data) if self.data else 0})"
        else:
            is_eof = self.data == b'EOF'
            return f"DATA Package(seq={self.seq_num}, {'EOF' if is_eof else f'data_len={len(self.data)}'})"