import socket
import bencode
import struct
import logging
import hashlib
from message import Message

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

    def send_request(self, piece_index, offset, requested_length):
        msg = Message.encode_request_message(piece_index, offset, requested_length)
        try:
            logging.debug('(%s:%d) sending request for a piece #%d(offset %d) to peer ',\
                          self.ip, self.port, piece_index, offset)
            self.sock.send(msg)
            logging.debug('(%s:%d) request sent')
        except socket.error:
            logging.error('ERROR in sending request to peer(%s:%d)',\
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


