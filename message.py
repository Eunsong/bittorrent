import bencode
import struct
import logging

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
        6: 'request',
        7: 'piece'
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
        try:
            return struct.pack("!IBIII", 13, 6, index, begin, length)
        except struct.error:
            print("%d, %d, %d"%(index, begin, length))

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
                        logging.warning('unmathced bitfield found.\
                            requiesting client to disconnect from this peer')
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
                    assert length is 13
                    index, begin, requested_length = struct.unpack("!III", org_messages[5:17])
                    message_type = cls.MESSAGE_IDS[msg_id]
                    msg = {'message_id': msg_id, 'message_type': message_type,\
                           'index': index, 'begin': begin, 'length': requested_length}
                    decoded_messages = cls.decode_all_messages(org_messages[17:])
                    decoded_messages.append(msg)
                    return decoded_messages
                elif ( msg_id is 7 ):
                    blocksize = length - 9
                    index, begin = struct.unpack("!II", org_messages[5:13])
                    message_type = cls.MESSAGE_IDS[msg_id]
                    block = org_messages[ 13 : 13 + blocksize ]
                    msg = {'message_id': msg_id, 'message_type': message_type,\
                            'block': block, 'index': index, 'begin': begin}
                    decoded_messages = cls.decode_all_messages(org_messages[13 + blocksize:])
                    decoded_messages.append(msg)
                    return decoded_messages
                return []






