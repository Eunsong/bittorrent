#! /usr/bin/python

import metainfo
import client
import tracker
import bencode
infile = open("halio02_archive.torrent")
#infile = open("tomstracker.torrent")
str = ""
for each_line in infile:
	str += each_line
infile.close()

meta = metainfo.Metainfo(str)
mycl = client.Client(meta)
print mycl.get_peers()


