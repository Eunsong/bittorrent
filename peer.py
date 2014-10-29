import socket
import bencode
import struct
import logging
import hashlib
from message import Message
from queue import Queue

class Peer(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.is_choking = 1 # whether this peer is choking the client
        self.is_interested = 0 # whether this peer is interested in the client
        self.client_choking = 1 # whether the client is choking this peer
        self.client_interested = 0 # whether the client is interested in this peer
        self.is_handshaked = False
        self.unprocessed_messages = []
        self.pieces = [] # list of pieces that the peer has
        self.scheduled_messages = Queue()
        #self.requested_pieces = [] # list of piece_number of requested pieces

    def enqueue_message(self, msg):
        self.scheduled_messages.put(msg)

    def send_scheduled_messages(self):
        while not self.scheduled_messages.empty():
            msg = self.scheduled_messages.get()
            try:
                self.sock.send(msg)
            except socket.error:
                logging.warning('cannot send scheduled message to peer(%s:%d)',\
                               self.ip, self.port)

    def fileno(self):
        return self.sock.fileno()

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
        pstr = b'BitTorrent protocol'
        reserved = struct.pack("B", 0)*8
        info = client_.metainfo.get(b"info")
        bcoded_info = bencode.Bencode.encodeDict(info)
        info_hash = hashlib.sha1(bcoded_info).digest()
        handshake_message = struct.pack("B", pstrlen) + pstr + reserved\
                            + info_hash +  client_.peer_id
        try:
            self.sock.send(handshake_message)
            packet = self.sock.recv(len(handshake_message))
            self.is_handshaked = True
        except (socket.timeout, socket.error):
            return False
        if not (info_hash == packet[28:-20]):
            return False
        else: 
            return packet

    def send_interested(self):
        msg = Message.encode_message('interested')
        try:
            self.sock.send(msg)
            logging.debug('interested message sent to peer(%s:%d)',\
                          self.ip, self.port)
            self.client_interested = 1 # 1: interested, 0: not interested
        except socket.error:
            logging.warning('socket.error in sending message to peer(%s:%d)',\
                          self.ip, self.port)


    def schedule_request(self, piece, requested_length=16384):
        piece_index = piece.NUMBER
        offset = piece.downloaded
        if ( piece.SIZE - offset < requested_length):
            requested_length = piece.SIZE - offset
        # verify if the peer is not choking the client
        if self.is_choking:
            logging.debug('cannot send request since the peer is choking the client')
            return False
        msg = Message.encode_request_message(piece_index, offset, requested_length)
        self.scheduled_messages.put(msg)        

    def recv_and_load_messages(self):
        """ decode received messages, update peer state based on the messages,
            and return pieces """
        logging.debug('receiving message from peer(%s:%d)',\
                       self.ip, self.port)
        buff = b''
        while True:
            try:
                msg = self.sock.recv(4096)
                if len(msg) == 0:
                    break
                buff += msg
            except socket.error:
                logging.warning('socket.error in receiving message from peer(%s:%d)',\
                              self.ip, self.port)
                break
        try:
            logging.debug("(%s:%d) receiving messages...", self.ip, self.port)
            decoded_messages = Message.decode_all_messages(buff)
            pieces = self._remove_pieces(decoded_messages)
            self.unprocessed_messages += decoded_messages
            logging.debug("(%s:%d) following messages successfully loaded...",  self.ip, self.port)
            logging.debug(decoded_messages)
            return pieces
        except ValueError:
            logging.error("invalid message. Skipping to next peer")
            pass
    @staticmethod
    def _remove_pieces(messages):
        piece_list = []
        for message in messages:
            if ( message['message_type'] is 'piece'):
                piece_list.append(message)
                messages.remove(message)
        return piece_list

    def process_messages(self):
        """ use messages loaded in self.unprocessed_messages to update self attributes
        """
        for each_message in self.unprocessed_messages:
            if not ( 'message_type' in each_message):
                logging.error("(%s:%d) invalid message found...ignoring the message",\
                              self.ip, self.port)
            else:
                if ( each_message['message_type'] is 'unchoke'):
                    self.is_choking = 0
                elif ( each_message['message_type'] is 'choke'):
                    self.is_choking = 1
                elif ( each_message['message_type'] is 'interested'):
                    self.is_interested = 1
                elif ( each_message['message_type'] is 'not interested'):
                    self.is_interested = 0
                elif ( each_message['message_type'] is 'have'):
                    self.pieces.append(each_message['piece_index'])
                elif ( each_message['message_type'] is 'bitfield'):
                    bitfield = each_message['bitfield']
                    for index, each_bit in enumerate(bitfield):
                        if ( each_bit is '1'):
                            self.pieces.append(index)


