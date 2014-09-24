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

    def send_interested_to_all(self, timeout=0.5):
        logging.info('sending interested message to all handshaked peers...')
        for peer in self.connected_peers:
            if ( peer.handshaked ):
                peer.send_interested()
        logging.info('completed sending interested messages')

    def recv_message(self):
        logging.info('receiving messages from all connected peers...')
        for peer in self.connected_peers:
            print peer.recv_decoded_message()


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

    def recv_decoded_message(self):
        logging.debug('receiving message from peer(%s:%d)',\
                       self.ip, self.port)
        buff = ''
        while True:
            try:
                msg = self.sock.recv(4096)
                print msg
                if len(msg) == 0:
                    break
                buff += msg
            except socket.error:
                logging.error('ERROR in receiving message from peer(%s:%d)',\
                              self.ip, self.port)
                break
        try:
            print "printing bare message from %s: " %self.ip
            print buff
            print "printing decoded message :"
            print Message.decode_all_messages(buff)
            return Message.decode_all_messages(buff)
        except ValueError:
            logging.error("invalid message. Skipping to next peer")
            pass

class Message(object):

    MESSAGE_TYPES = {
        'keep-alive': struct.pack("!I", 0),
        'choke': struct.pack("!IB", 1, 0),
        'unchoke': struct.pack("!IB", 1, 1),
        'interested': struct.pack("!IB", 1, 2),
        'not interested': struct.pack("!IB", 1, 3),
        'have': struct.pack("!IB", 5, 4),
    }

    MESSAGE_IDS = {
        0: 'choke',
        1: 'unchoke',
        2: 'interested',
        3: 'not interested',
        4: 'have',
        5: 'bitfield',
        6: 'request'
    }

    @classmethod
    def encode_message(cls, message_type, index=-1):
        if message_type is 'have':
            if not index is -1:
                return cls.MESSAGE_TYPES['have'] + struct.pack("!I", index)
            else:
                raise ValueError('piece index is required for have message')
        else:
            try:
                return cls.MESSAGE_TYPES[message_type]
            except KeyError:
                raise KeyError("Invalid message type selected")

    @staticmethod
    def encode_request_message(index, begin, length):
        return struct.pack("!IBIII", 13, 6, index, begin, length)   

    @classmethod
    def decode_all_messages(cls, org_messages):
        if ( len(org_messages) < 4):
            return []
        else:
            length = struct.unpack("!I", org_messages[:4])[0]
            if ( length is 0 ): # keep-alive
                msg = {'message_type': 'keep-alive'}
                decoded_messages = cls.decode_all_messages(org_messages[4:])
                decoded_messages.append(msg)
                return decoded_messages
            elif ( length is 1 ):
                msg_id = struct.unpack("B", org_messages[4:5])[0]
                message_type = cls.MESSAGE_IDS[msg_id]
                msg = {'message_id': msg_id, 'message_type': message_type}
                decoded_messages = cls.decode_all_messages(org_messages[5:])
                decoded_messages.append(msg)
                return decoded_messages
            else:
                msg_id = struct.unpack("B", org_messages[4:5])[0]
                if ( msg_id is 4): # have
                    piece_index = struct.unpack("!I", org_messages[5:9])[0]
                    message_type = cls.MESSAGE_IDS[msg_id]
                    msg = {'message_id': msg_id,'message_type': message_type,\
                            'piece_index': piece_index}
                    decoded_messages = cls.decode_all_messages(org_messages[9:])
                    decoded_messages.append(msg)
                    return decoded_messages
                elif ( msg_id is 5): # bitfield
                    logging.debug('trying to decode a bitfield message...')
                    format = ''
                    for i in range(length-1):
                        format += 'B'
                    try:
                        unpacked = struct.unpack(format, org_messages[5:4+length])
                    except struct.error: # return -1 to tell client to drop the connection 
                        return [-1]
                    bitfield = ''
                    decoded_bitfield = unpacked
                    for each_byte in decoded_bitfield:
                        bin_number = bin(each_byte)[2:].zfill(8)
                        bitfield += bin_number
                    message_type = cls.MESSAGE_IDS[msg_id]
                    logging.debug('completed decoding the bitfield message...')
                    msg = {'message_id': msg_id, 'message_type': message_type,\
                        'bitfield': bitfield}
                    decoded_messages = cls.decode_all_messages(org_messages[4+length:])
                    decoded_messages.append(msg)
                    return decoded_messages
                elif ( msg_id is 6):
                    index, begin, requested_length = struct.unpack("!III", msg[5:17])
                    message_type = cls.MESSAGE_IDS[msg_id]
                    msg = {'message_id': msg_id, 'message_type': message_type,\
                           'index': index, 'begin': begin, 'length': requested_length}
                    decoded_messages = cls.decode_all_messages(org_messages[17:])
                    decoded_messages.append(msg)
                    return decoded_messages
                return []


"""
    @classmethod
    def decode_message(cls, messages):
        if ( len(messages) < 4):
            raise ValueError("invalid message(shorter than the shortest message)")
        else:
            length = struct.unpack("!I", msg)
            if ( length is 0 ): # keep-alive
                return {'message_type': 'keep-alive'}
            elif ( length is 1 ):
                msg_id = struct.unpack("B", msg[4:5])
                return {'message_id': msg_id, 'message_type': message_type}

        elif ( len(messages) is 4):
            length = struct.unpack("!I", msg)
            if ( length is 0 ):
                return {'message_type': 'keep-alive'}
            else:
                raise ValueError("invalid message received")
        elif ( len(messages) is 5):
            length, msg_id = struct.unpack("!IB", msg)
            assert length == 1
            meesage_type = cls.MESSAGE_IDS[msg_id]
            return {'message_id': msg_id, 'message_type': message_type}
        else: # len(msg) > 5 
            length, msg_id = struct.unpack("!IB", msg[:5])
            if ( msg_id is 4 ):
                length, msg_id, piece_index = struct.unpack("!IBI", msg[:9])
                meesage_type = cls.MESSAGE_IDS[msg_id]
                return {'message_id': msg_id,'message_type': message_type,\
                        'piece_index': piece_index}
            elif ( msg_id is 5):
                logging.debug('trying to decode a bitfield message...')
                format = '!IB'
                for i in range(length-1):
                    format += 'B'
                try:
                    unpacked = struct.unpack(format, msg)
                except struct.error:
                    logging.error('unmatched bitfield length. require %d but %d found.',\
                                   (length-1), len(msg)-5)
                    return -1
                bitfield = ''
                decoded_bitfield = unpacked[2:]
                for each_byte in decoded_bitfield:
                    bin_number = bin(each_byte)[2:]
                    bitfield += bin_number
                message_type = cls.MESSAGE_IDS[msg_id]
                logging.debug('completed decoding the bitfield message...')
                return {'message_id': msg_id, 'message_type': message_type,\
                        'bitfield': bitfield}
            elif ( msg_id is 6):
                format = "!IBIII"
                index, begin, requested_length = struct.unpack(format, msg[5:])
                message_type = cls.MESSAGE_IDS[msg_id]
                return {'message_id': msg_id, 'message_type': message_type,\
                        'index': index, 'begin': begin, 'length': requested_length}
"""











