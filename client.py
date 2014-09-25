import metainfo
import tracker
import hashlib
import bencode
import struct
import socket
import logging
from message import Message
import math

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
        self.pieced_needed = [i for range(self.num_pieces)] # list of pieces the client still needs


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



class Peer(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.am_choking = 1 # whether this peer is choking the client
        self.am_interested = 0 # whether this peer is interested in the client
        self.client_choking = 1 # whether the client is choking this peer
        self.client_interested = 0 # whether the client is interested in this peer
        self.handshaked = False
        self.unprocessed_messages = []
        self.pieces = [] # list of pieces that the peer has

        
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
        reserved = struct.pack("B", 0)*8
        info = client_.metainfo.get("info")
        bcoded_info = bencode.Bencode.encodeDict(info)
        info_hash = hashlib.sha1(bcoded_info).digest()
        handshake_message = struct.pack("B", pstrlen) + pstr + reserved\
                            + info_hash +  client_.peer_id
        try:
            self.sock.send(handshake_message)
            packet = self.sock.recv(len(handshake_message))
            self.handshaked = True
        except (socket.timeout, socket.error):
            return False
        if not (info_hash == packet[28:-20]):
            return False
        else: 
            return packet

    def send_interested(self):
        msg = Message.encode_message('interested')
        try:
            logging.debug('sending interested message to peer(%s:%d)...',\
                          self.ip, self.port)
            self.sock.send(msg)
            logging.debug('interested message sent to peer(%s:%d)',\
                          self.ip, self.port)
            self.client_interested = 1 # 1: interested, 0: not interested
        except socket.error:
            logging.error('ERROR in sending message to peer(%s:%d)',\
                          self.ip, self.port)

    def recv_and_load_message(self):
        logging.debug('receiving message from peer(%s:%d)',\
                       self.ip, self.port)
        buff = ''
        while True:
            try:
                msg = self.sock.recv(4096)
                if len(msg) == 0:
                    break
                buff += msg
            except socket.error:
                logging.error('ERROR in receiving message from peer(%s:%d)',\
                              self.ip, self.port)
                break
        try:
            logging.debug("(%s:%d) receiving messages...", self.ip, self.port)
            decoded_messages = Message.decode_all_messages(buff)
            self.unprocessed_messages += decoded_messages
            logging.debug("(%s:%d) following messages successfully loaded...",  self.ip, self.port)
            logging.debug(decoded_messages)
        except ValueError:
            logging.error("invalid message. Skipping to next peer")
            pass

    def process_messages(self):
        """ use messages loaded in self.unprocessed_messages update self attributes
        """
        for each_message in self.unprocessed_messages:
            if not ( 'message_type' in each_message):
                logging.error("(%s:%d) invalid message found...ignoring the message",\
                              self.ip, self.port)
            else:
                if ( each_message['message_type'] is 'unchoke'):
                    self.am_choking = 0
                elif ( each_message['message_type'] is 'choke'):
                    self.am_choking = 1
                elif ( each_message['message_type'] is 'interested'):
                    self.am_interested = 1
                elif ( each_message['message_type'] is 'not interested'):
                    self.am_interested = 0
                elif ( each_message['message_type'] is 'have'):
                    self.pieces.append(each_message['piece_index'])
                elif ( each_message['message_type'] is 'bitfield'):
                    bitfield = each_message['bitfield']
                    for index, each_bit in enumerate(bitfield):
                        if ( each_bit is '1'):
                            self.pieces.append(index)


