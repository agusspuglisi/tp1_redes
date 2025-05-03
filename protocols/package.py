class Package:
    def __init__ (self, seq_num, ack, data):
        self.seq_num = seq_num
        self.ack = ack
        self.data = data
    
    def to_bytes(self):
        seq_bytes = self.seq_num.to_bytes(4, byteorder='big')
        ack_byte = bytes([1 if self.ack else 0])
        return seq_bytes + ack_byte + self.data

    @staticmethod
    def from_bytes(raw_bytes):
        seq_num = int.from_bytes(raw_bytes[0:4], byteorder='big')
        ack_flag = raw_bytes[4]
        data = raw_bytes[5:]
        return Package(seq_num, bool(ack_flag), data)
