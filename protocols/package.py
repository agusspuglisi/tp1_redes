class Package:
    def __init__ (self, seq_num, ack, data):
        self.seq_num = seq_num
        self.ack = ack
        self.data = data
    
    def to_bytes(self):
        return bytes([self.seq_num, int(self.ack)]) + self.data
    
    @staticmethod
    def from_bytes(data_bytes):
        seq_num = data_bytes[0]
        ack = data_bytes[1]
        data = data_bytes[2:]
        return Package(seq_num, ack, data)