#! /usr/bin/python

import metainfo
import client
import tracker
import bencode
import peer
import logging

logging.basicConfig(level=logging.DEBUG)
#infile = open("b.torrent")
infile = open("tomstracker.torrent")
str = ""
for each_line in infile:
	str += each_line
infile.close()

meta = metainfo.Metainfo(str)
mycl = client.Client(meta)
mycl.connect_peers()
mycl.handshake()
mycl.send_interested_to_all()
mycl.recv_message()



"""
print mycl.get_peers()
import socket
sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ip = mycl.get_peers()[1]['ip']
port = mycl.get_peers()[1]['port']
sock1 = socket.create_connection((ip, port), 60)
ip = mycl.get_peers()[2]['ip']
port = mycl.get_peers()[2]['port']
sock2 = socket.create_connection((ip, port), 60)

socks = [sock1, sock2]
import select
print "calling select()"
readable, writable, errors = select.select(socks, socks, [])
print "printing redables"
print readable
print "printing writables"
print writable
"""
"""
peer = peer.Peer(mycl.get_peers()[2]['ip'], mycl.get_peers()[2]['port']) 
mycl.handshake(peer)"""
