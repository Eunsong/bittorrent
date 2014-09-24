LP = '!IB' # "Length Prefix" (req'd by protocol)
MESSAGE_TYPES = {
    -1: 'keep_alive',
    0: ('choke', LP, 1),
    1: ('unchoke', LP, 1),
    2: ('interested', LP, 1),
    3: ('not interested', LP, 1),
    4: ('have', LP+'I', 5),
    # bitfield: Append <bitfield> later. Dynamic length.
    5: ('bitfield', LP),
    6: ('request', LP+'III', 13),
    # piece: Append <index><begin><block> later. Dynamic length.
    7: ('piece', LP+'II'),
    8: ('cancel', LP+'III', 13),
    9: ('port', LP+'BB', 3)
}

