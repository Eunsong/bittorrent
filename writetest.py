#! /usr/bin/python

import client
rem = 1277987
p1 = client.Piece(1277987, 0)
with open('flag.jpg','r') as toread:
	while ( not p1.is_complete() ):
		if (rem < 4096 ):
			req = rem
		else:
			req = 4096
		rem -= req
		msg = toread.read(req)
		p1.add_to_buffer(msg)


