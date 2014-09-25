import tracker
import bencode
import struct
import socket
import logging
from message import Message
import math
from peer import Peer

class Client(object):
    def __init__(self, metainfo_):
        self.peer_id = self._gen_peer_id()
        self.metainfo = metainfo_
        self.tracker = tracker.Tracker(self)
        self.trackerResponse = self.request_tracker()
        logging.debug('meta info details...')
        logging.debug(self.metainfo.get('info'))
        # list of {'ip': ip, 'port': port} peer dictionaries
        self.file_length = 0
        if ( 'length' in self.metainfo.get('info') ):
            self.file_length = self.metainfo.get('info')['length']
        elif ( 'files' in self.metainfo.get('info')):
            for each_file in self.metainfo.get('info')['files']:
                self.file_length += each_file['length']
        else:
            raise ValueError('file length not defined in the torrent file')
        self.piece_length = self.metainfo.get('info')['piece length']
        self.num_pieces = int(math.ceil(self.file_length/self.piece_length))
        self.peers = self.get_peers()
        self.connected_peers = []
        self.pieces = [] # list of pieces the client has
        logging.info('file length : %d', self.file_length)
        logging.debug('received the following response from the tracker : ')
        logging.debug(self.trackerResponse)
        logging.info('number of pieces : %d', self.num_pieces)
        self.pieced_needed = [i for i in range(self.num_pieces)] # list of pieces the client still needs
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

    def send_interested_to_all(self, timeout=0.5):
        logging.info('sending interested message to all handshaked peers...')
        for peer in self.connected_peers:
            if ( peer.handshaked ):
                peer.send_interested()
        logging.info('completed sending interested messages')

    def recv_message(self):
        logging.info('receiving messages from all connected peers...')
        for peer in self.connected_peers:
            if ( peer.handshaked):
                peer.recv_and_load_message()
                peer.process_messages()

    def handshake(self):
        logging.info('trying to handshake with connected peers...')
        for peer in self.connected_peers:
            packet = peer.handshake(self)
            if packet:
                logging.debug('handshake succeeded and verified with ip:%s', peer.ip)


class Metainfo(object):
    def __init__(self, str_):
        self.info_dic = bencode.Bencode(str_).decode()
        assert type(self.info_dic) is dict
    def getDict(self):
        return self.info_dic
    def get(self, key):
        return self.info_dic[key]



