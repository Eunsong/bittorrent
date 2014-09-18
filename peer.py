import socket

class Peer(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.am_choking = 1 # whether this peer is choking the client
        self.am_interested = 0 # whether this peer is interested in the client
        self.client_choking = 1 # whether the client is choking this peer
        self.client_interested = 0 # whether the client is choking this peer
        
    def connect(self):
        self.sock.connect((self.ip, self.port))