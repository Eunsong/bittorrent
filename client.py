import tracker
import bencode
import struct
import socket
import logging
from message import Message
import math
from peer import Peer
from random import random
import os

class Client(object):
    def __init__(self, metainfo):
        self.peer_id = self._gen_peer_id()
        self.metainfo = Metainfo(metainfo)
        self.tracker = tracker.Tracker(self)
        self.trackerResponse = self.request_tracker()
        logging.debug('meta info details...')
        logging.debug(self.metainfo.get(b'info'))
        # list of {'ip': ip, 'port': port} peer dictionaries
        self.file_length = 0
        if ( b'length' in self.metainfo.get(b'info') ):
            self.file_length = self.metainfo.get(b'info')[b'length']
        elif ( b'files' in self.metainfo.get(b'info')):
            for each_file in self.metainfo.get(b'info')[b'files']:
                self.file_length += each_file[b'length']
        else:
            raise ValueError('file length not defined in the torrent file')
        self.piece_length = self.metainfo.get(b'info')[b'piece length']
        self.num_pieces = int(self.file_length/self.piece_length) + 1
        self.peers = self.get_peers()
        self.connected_peers = []
        logging.info('file length : %d', self.file_length)
        logging.debug('received the following response from the tracker : ')
        logging.debug(self.trackerResponse)
        logging.info('number of pieces : %d', self.num_pieces)
        self.pieces_needed = self.gen_pieces() # list of pieces the client still needs
        self.pieces_completed = [] # list of pieces the client has

    def update_peers(self):
        self.peers = self.get_peers()
    def get_peers(self):
        logging.info('updating peer list')
        peers = []
        arg = self.trackerResponse[b'peers']
        if ( type(arg) is bytes): # if binary model
            assert (len(arg) % 6 == 0)
            num_peers = int(len(arg)/6)
            for n in range(num_peers):
                ip = '.'.join([str(c) for c in arg[n*6: n*6 + 4]])
                port = arg[n*6 + 4]*256 + arg[n*6 + 5]
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
        return struct.pack("20s", bytes(myid, 'utf8')) 
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

    def send_interested_to_all(self):
        logging.debug('sending interested message to all handshaked peers...')
        for peer in self.connected_peers:
            if ( peer.is_handshaked ):
                peer.send_interested()
        logging.debug('completed sending interested messages')

    def recv_message(self, readable_peers=None):
        if ( readable_peers is None ):
            readable_peers = self.connected_peers
        logging.debug('receiving messages from all connected peers...')
        for peer in readable_peers:
            if ( peer.is_handshaked):
                pieces = peer.recv_and_load_messages()
                peer.process_messages()
                self._update_pieces(pieces)

    def _update_pieces(self, list_of_piece_messages):
        for each_message in list_of_piece_messages:
            piece_number = each_message['index']
            offset = each_message['begin']
            block = each_message['block']
            for each_incomplete_piece in self.pieces_needed:
                if ( each_incomplete_piece.NUMBER == piece_number):
                    each_incomplete_piece.add_to_buffer(block, offset)
                    # remove the completed piece from the pieces_needed 
                    # add put it into the pieces_completed
                    if ( each_incomplete_piece.is_complete() ):
                        self.pieces_needed.remove(each_incomplete_piece)
                        self.pieces_completed.append(each_incomplete_piece)

    def handshake(self):
        logging.info('trying to handshake with connected peers...')
        for peer in self.connected_peers:
            packet = peer.handshake(self)
            if packet:
                logging.debug('handshake succeeded and verified with ip:%s', peer.ip)

    def gen_pieces(self):
        """ returns a list of Piece objects """
        num_pieces = int(math.floor(self.file_length/self.piece_length)) + 1
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
        if ( len(self.pieces_completed) == self.num_pieces):
            logging.info('combining downloaded pieces...')
            # sort completed list using the piece numbers
            self.pieces_completed.sort( key=lambda piece: piece.NUMBER )
            file_name = self.metainfo.info_dic[b'info'][b'name']
            with open(file_name, 'ab') as outfile:
                for i, each_message in enumerate(self.pieces_completed):
                    offset = i*self.piece_length
                    outfile.seek(offset)
                    with open(each_message.file, 'rb') as infile:
                        outfile.write(infile.read())
                    os.system('rm ' + each_message.file)
            logging.info('combining pieces finished. %s file has created', file_name)
        else:
            logging.error('cannot generate file. not all pieces are downloaded yet.')
            raise ValueError()

    def send_messages_to_peer(self, peer):
        """ when writable peer is passed in, this method sends
            appropriate messages to the peer (e.g. request, have, unchoke, choke, etc)"""
        # find if the peers has a needed piece and send request 
        for each_message in self.pieces_needed:
            if each_message.NUMBER in peer.pieces:
                # currently does not check if request has been sent already
                peer.send_request(each_message)
                break

class MessageScheduler(object):
    def __init__(self, pieces_needed, life_time=100):
        self.peer_piece_pairs = {}
        self.pieces_buffer = list(pieces_needed)
        self.LIFE_TIME = life_time

    class PeerPiece(object):
        def __init__(self, peer, life_time=100):
            self.peer = peer
            self.LIFE_TIME = life_time
            self.rounds_left = life_time
        def set_piece(self, piece):
            self.piece = piece
            self.rounds_left = self.LIFE_TIME
        def is_complete(self):
            return self.piece.is_complete()
        def is_expired(self):
            return ( self.rounds_left < 1 )

    def schedule_messages(self, writables):
        """
        assign a new piece to available peers that currently don't have
        assigned piece or that have been expired/completed, and schedule 
        request messages. 
        If a piece is completed, sechdule sending have messages to all peers
        """
        s = ''
        for piece in self.pieces_buffer:
            s += str(piece.NUMBER) + "  "
        logging.debug('currently in the piece buffer : %s', s)
        # update pieces_buffer (completed pieces may have been removed)
        for each_piece in self.pieces_buffer:
            # so if the piece remaining in the buffer is completed, remove it
            # and schedule sending have message to all peers
            if ( each_piece.is_complete() ):
                self.pieces_buffer.remove(each_piece)
                self._schedule_have(each_piece, writables)
        # similarly, peers should be released if they are binded with completed piece
        removables = []
        for peer in self.peer_piece_pairs:
            if ( self.peer_piece_pairs[peer].is_complete() ):
                removables.append(peer)
        for each_peer in removables:
            del self.peer_piece_pairs[each_peer]

        # assign new (incomplete) pieces to currently available peers
        for each_peer in writables:
            if ( each_peer in self.peer_piece_pairs and\
                not self.peer_piece_pairs[each_peer].is_expired() ):
                self.peer_piece_pairs[each_peer].rounds_left -= 1
            else:
                if ( each_peer in self.peer_piece_pairs and\
                    self.peer_piece_pairs[each_peer].is_expired() ):
                    logging.debug('removing expired request for piece %d from peer %s',\
                                   self.peer_piece_pairs[each_peer].piece.NUMBER,\
                                   each_peer.ip)
                    self.pieces_buffer.append( self.peer_piece_pairs[each_peer].piece)
                # pick a piece randomly from buffer
                piece = self._random_piece()
                if piece:
                    peer_piece = self.PeerPiece(each_peer)
                    peer_piece.set_piece(piece)
                    logging.debug('assigning piece %d to peer %s',\
                                   piece.NUMBER, each_peer.ip)
                    logging.debug('sending requests to peers')
                    self.peer_piece_pairs[each_peer] = peer_piece
                    each_peer.schedule_request(piece)                

    def _random_piece(self):
        """ returns a piece picked randomly from the buffer """
        piece_number = int(random()*len(self.pieces_buffer))
        if self.pieces_buffer:
            piece = self.pieces_buffer.pop(piece_number)
            return piece
        else:
            logging.warning('requesting a piece from the empty buffer')
            return False

    def _schedule_have(self, piece, writables):
        msg = Message.encode_message('have', piece.NUMBER)
        for each_peer in writables:
            each_peer.enqueue_message(msg)


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
        self.buff = b''

    def is_complete(self):
        return ( self.downloaded == self.SIZE )

    def _write_to_file(self):
        try:
            with open(self.file, 'ab') as output:
                output.seek(self.downloaded)
                output.write(self.buff)
                buff = b''
        except IOError:
            logging.error('cannot write piece data into file %s', self.file)

    def add_to_buffer(self, msg, begin=0):
        if ( self.is_complete() ):
            logging.debug('piece%d is already completed. Ignoring add_to_buffer request.')
            return
        if not ( self.downloaded == begin):
            logging.debug('unmatched file offset. Ignoring add_to_buffer request')
            return
        logging.debug('adding a block of piece%d (size:%d, offset:%d) to buffer...',\
                       self.NUMBER, len(msg), self.downloaded) 
        self.buff += msg
        self.downloaded += len(msg)
        if ( self.downloaded == self.SIZE):
            logging.debug('piece%d download completed...', self.NUMBER)
            self._write_to_file()
        elif ( self.downloaded > self.SIZE):
            logging.error('trying to write file bigger than piece size')
            raise ValueError()



