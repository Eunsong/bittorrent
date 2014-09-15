#! /usr/bin/python

import bencode
import metainfo
infile = open("tomstracker.torrent")
str = ""
for each_line in infile:
	str += each_line
infile.close()
meta = metainfo.metainfo(str)
print meta.get("announce")
print meta.get("info")
import client
mycl = client.client()
print mycl.peer_id
"""
tmp = bencode.bencode()
dic = tmp.decode(str)
print dic
bcoded = bencode.bencode.encodeDict(dic["info"])
print bcoded
"""
