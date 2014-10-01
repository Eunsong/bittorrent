import tracker
import bencode
import struct
import socket
import logging
from message import Message
import math
from peer import Peer

class Client(object):
    def __init__(self, metainfo):
        self.peer_id = self._gen_peer_id()
        self.metainfo = Metainfo(metainfo)
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
        logging.info('file length : %d', self.file_length)
        logging.debug('received the following response from the tracker : ')
        logging.debug(self.trackerResponse)
        logging.info('number of pieces : %d', self.num_pieces)
        self.pieces_needed = self.gen_pieces() # list of pieces the client has
        self.pieces_completed = [] # list of pieces the client still needs
        #self.request_buffer = [] # scheduled outgoing messages

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
            if ( peer.is_handshaked ):
                peer.send_interested()
        logging.info('completed sending interested messages')

    def recv_message(self):
        logging.info('receiving messages from all connected peers...')
        for peer in self.connected_peers:
            if ( peer.is_handshaked):
                pieces = peer.recv_and_load_messages()
                peer.process_messages()
                self._update_pieces(pieces)

    def _update_pieces(self, list_of_piece_messages):
        for each_piece in list_of_piece_messages:
            piece_number = each_piece['index']
            offset = each_piece['begin']
            block = each_piece['block']
            for each_incomplete_piece in self.pieces_needed:
                if ( each_incomplete_piece.NUMBER == piece_number):
                    each_incomplete_piece.add_to_buffer(block, offset)

    def handshake(self):
        logging.info('trying to handshake with connected peers...')
        for peer in self.connected_peers:
            packet = peer.handshake(self)
            if packet:
                logging.debug('handshake succeeded and verified with ip:%s', peer.ip)

    def gen_pieces(self):
        """ returns a list of Piece objects """
        num_pieces = int(math.ceil(self.file_length/self.piece_length))
        last_piece_length = self.file_length - (num_pieces-1)*self.piece_length
        piece_list = []
        for i in range(num_pieces):
            if ( i == num_pieces - 1 ):
                piece = Piece(last_piece_length, i)
            else:
                piece = Piece(self.piece_length, i)
            piece_list.append(piece)
        return piece_list
    def combine_pieces(self):
        """ if all the pieces have been downloaded, combine them together
            to get the target file """
        if ( self.num_pieces == len(self.pieces_completed)):
            logging.log('combining downloaded pieces...')
            file_name = self.metainfo.info_dic['info']['name']
            with open(file_name, 'a') as outfile:
                for i, each_piece in enumerate(self.pieces_completed):
                    offset = i*self.piece_length
                    outfile.seek(offset)
                    with open(each_piece.file, 'r') as infile:
                        outfile.write(infile.read())
            logging.log('combining pieces finished. %s file has created', file_name)
        else:
            logging.error('cannot generate file. not all pieces are downloaded yet.')
            raise ValueError()


    def send_messages_to_peer(self, peer):
        """ when writable peer is passed in, this method sends
            appropriate messages to the peer (e.g. request, have, unchoke, choke, etc)"""
        # find if the peers has a needed piece and send request 
        for each_piece in self.pieces_needed:
            if each_piece.NUMBER in peer.pieces:
                # currently does not check if request has been sent already
                peer.send_request(each_piece)
                break

class RequestManager(object):
    def __init__(self, pieces_needed, lifetime=5):
        self.pieces_needed = pieces_needed
        self.pieces_buffer = dict(enumerate(pieces_needed))
        self.LIFE_TIME = lifetime
    class Piece_request(object):
        def __init__(self, peer, lifetime=5):
            self.peer = peer
            self.lifetime = lifetime
        def set_piece(piece):
            self.piece = piece
            self.lifetime -= 1
    def send_requests(writables):
        for writable in writables:
            for i in self.pieces_buffer:
                if self.pieces_buffer[i].NUMBER in writable.pieces:
                    try:
                        writable.send_request(self.pieces_buffer[i])
                        self.pieces_buffer[i] = ''
                    except (socket.error, socket.timeout):
                        logging.debug('(%s:%d) cannot send request message',\
                        writable.ip, writable.port)




class Metainfo(object):
    def __init__(self, str_):
        self.info_dic = bencode.Bencode(str_).decode()
        assert type(self.info_dic) is dict
    def getDict(self):
        return self.info_dic
    def get(self, key):
        return self.info_dic[key]

class Piece(object):
    def __init__(self, piece_size, piece_number, outputfile_prefix='tmp_piece'):
        self.SIZE = piece_size
        self.NUMBER = piece_number
        self.downloaded = 0
        self.file = outputfile_prefix + str(self.NUMBER) + '.pc'
        self.buff = ''

    def is_complete(self):
        return ( self.downloaded == self.SIZE )

    def write_to_file(self):
        try:
            with open(self.file, 'a') as output:
                output.seek(self.downloaded)
                output.write(self.buff)
                buff = ''
        except IOError:
            logging.error('cannot write piece data into file %s', self.file)

    def add_to_buffer(self, msg, begin=0):
        print str(self.downloaded)
        if ( self.is_complete() ):
            logging.debug('piece%d is already completed. Ignoring add_to_buffer request.')
            return
        if not ( self.downloaded == begin):
            logging.debug('unmated file offset. Ignoring add_to_buffer request')
            return
        self.buff += msg
        self.downloaded += len(msg)
        if ( self.downloaded == self.SIZE):
            logging.debug('piece%d download completed...', self.NUMBER)
            self.write_to_file()
        elif ( self.downloaded > self.SIZE):
            logging.error('trying to write file bigger than piece size')
            raise ValueError()



