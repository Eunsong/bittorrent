#! /usr/bin/python

import argparse
import client
import tracker
import bencode
import peer
import logging
import message
from peer import Peer
import select


def main(torrent_file):
    with open(torrent_file, 'rb') as f:
        torrent_info = b""
        for each_line in f:
            torrent_info += each_line
    mycl = client.Client(torrent_info)
    logging.info('starting client to download a file : %s', mycl.metainfo.get(b'info')[b'name'])
    mycl.connect_peers()
    mycl.handshake()
    mycl.send_interested_to_all()
    mycl.recv_message()
    reqs = client.MessageScheduler(mycl.pieces_needed)

    while mycl.connected_peers:
        readables, writables, execptions = select.select(mycl.connected_peers, mycl.connected_peers, [])
        mycl.recv_message(readables)       
        reqs.schedule_messages(writables)
        for each_peer in writables:
            each_peer.send_scheduled_messages()
        if ( len(mycl.pieces_needed) is 0 ):
            mycl.combine_pieces()
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('torrent', help = 'input torrent file')
    parser.add_argument('--logging', '-l', default='error', help = \
                        'level of displaying logging info (error, info, debug)',\
                        choices = ['debug', 'info', 'error'])
    arg = parser.parse_args()
    logging.basicConfig(level=arg.logging.upper())
    main(arg.torrent)

