import metainfo
import tracker
import hashlib
import bencode
import struct
import socket
import logging

class Client(object):
    def __init__(self, metainfo_):
        self.peer_id = self._gen_peer_id()
        self.metainfo = metainfo_
        self.tracker = tracker.Tracker(self)
        self.trackerResponse = self.request_tracker()
        # list of {'ip': ip, 'port': port} peer dictionaries
        self.peers = self.get_peers()
        self.connected_peers = []
    def update_peers(self):
        self.peers = self.get_peers()
    def get_peers(self):
        logging.info('updating peer list')
        peers = []
        arg = self.trackerResponse['peers']
        if ( type(arg) is str): # if binary model
            assert (len(arg) % 6 == 0)
            num_peers = len(arg)/6
            for n in range(num_peers):
                ip = '.'.join([str(ord(c)) for c in arg[n*6: n*6 + 4]])
                port = ord(arg[n*6 + 4])*256 + ord(arg[n*6 + 5])
                peer = Peer(ip, port)
                peers.append(peer)
        else: # dictionary model is not implemented yet
            raise ValueError("unsupported tracker response format")
        logging.info('peer list updated')
        return peers
    def request_tracker(self):
        return self.tracker.getRequest()
    def _gen_peer_id(self):
        import time
        myid = "-" + "MY" + "0001" + str(time.time())
        return struct.pack("20s", myid) 
    def get_peer_id(self):
        return self.peer_id
    
    def connect_peers(self, timeout=0.5):
        logging.info('connecting to peers...')
        for peer in self.peers:
            if peer.connect(timeout):
                self.connected_peers.append(peer)
        num_peers = len(self.peers)
        num_connected = len(self.connected_peers)
        logging.info('connected to %d peers out of %d peers',\
                     num_connected, num_peers)
        for i, peer in enumerate(self.connected_peers):
            ip = peer.ip
            port = peer.port
            logging.debug('connected peer%d : %s:%d', i+1, ip, port)

    def handshake(self):
        logging.info('trying to handshake with connected peers...')
        for peer in self.connected_peers:
            packet = peer.handshake(self)
            if packet:
                logging.debug('handshake succeeded and verified with ip:%s', peer.ip)


class Peer(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.am_choking = 1 # whether this peer is choking the client
        self.am_interested = 0 # whether this peer is interested in the client
        self.client_choking = 1 # whether the client is choking this peer
        self.client_interested = 0 # whether the client is choking this peer
        
    def connect(self, timeout=0.5):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        try:
            self.sock.connect((self.ip, self.port))
            return True
        except (socket.timeout, socket.error):
            self.sock.close()
            return False

    def handshake(self, client_):
        pstrlen = 19
        pstr = 'BitTorrent protocol'
        reserved = "00000000"
        info = client_.metainfo.get("info")
        bcoded_info = bencode.Bencode.encodeDict(info)
        info_hash = hashlib.sha1(bcoded_info).digest()
        handshake_message = struct.pack("B", pstrlen) + pstr + reserved\
                            + info_hash +  client_.peer_id
        try:
            self.sock.send(handshake_message)
            packet = self.sock.recv(len(handshake_message))
        except (socket.timeout, socket.error):
            return False
        if not (info_hash == packet[28:-20]):
            return False
        else: 
            return packet



