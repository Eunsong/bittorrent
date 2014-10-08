#! /usr/bin/python

import client
import tracker
import bencode
import peer
import logging
import message
from peer import Peer

logging.basicConfig(level=logging.DEBUG)
#infile = open("b.torrent")
#infile = open("halio02_archive.torrent")
infile = open("tomstracker.torrent")
str = ""
for each_line in infile:
	str += each_line
infile.close()

mycl = client.Client(str)
print "file name : ", mycl.metainfo.get('info')['name']
mycl.connect_peers()
mycl.handshake()
mycl.send_interested_to_all()
mycl.recv_message()
import select
reqs = client.MessageScheduler(mycl.pieces_needed)

while mycl.connected_peers:
    readables, writables, execptions = select.select(mycl.connected_peers, mycl.connected_peers, [])
    logging.info('receiving messages from readables')
    mycl.recv_message(readables)       
    logging.info('finished receiving messages from readables...')
    logging.info('start sending requests') 
    reqs.schedule_messages(writables)
    for each_peer in writables:
        each_peer.send_scheduled_messages()
    logging.info('finished sending requests')

# for peer in mycl.connected_peers:
#     if ( peer.is_choking == 0 ):
#         print peer.pieces
#         peer.send_request(0, 0, 16384)
# mycl.recv_message()

