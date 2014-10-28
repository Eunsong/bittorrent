class Bencode(object):
    def __init__(self, str_=''):
        self.str = str_
        self.idx = 0 # index position   
    @staticmethod
    def encodeDict(dict_):
        if not (type(dict_) is dict):
            raise ValueError("not a valid dictionary")
        retval = b'd'
        # sort the dictionary based on the keys
        sortedKeys = []
        for key in dict_.keys():
            sortedKeys.append(key)
        sortedKeys.sort()
        for key in sortedKeys:  
            strlen = len(key)
            retval += str(strlen).encode('utf8') + b":" + key
            val = dict_[key]
            valType = type(val)
            if ( valType is bytes):
                strlen = len(val)
                retval += str(strlen).encode('utf8') + b":" + val
            elif ( valType is int):
                retval += b"i" + str(val).encode('utf8') + b"e"
            elif ( valType is list):
                retval += Bencode.encodeList(val)
            elif ( valType is dict):
                retval += Bencode.encodeDict(val)
            else:
                raise ValueError("unknown type value in the dictionary")
        retval += b"e"
        return retval
    @staticmethod
    def encodeList(list_):
        if not (type(list_) is list):
            raise ValueError("not a valid list")
        retval = "l"
        for item in list_:
            itemType = type(item)
            if ( itemType is str):
                strlen = len(item)
                retval += str(strlen).encode('utf8') + b":" + item.encode('utf8')
            elif ( itemType is int):
                retval += b"i" + str(item).encode('utf8') + b"e"
            elif ( itemType is list):
                retval += Bencode.encodeList(item)
            elif ( itemType is dict):
                retval += Bencode.encodeDict(item)
            else:
                raise ValueError("unknown type item in the list")
        retval += b"e"
        return retval
    def decode(self, str_=''):
        self.idx = 0
        if str_:
            self.str = str_
        type_ = self.str[self.idx]
        if ( type_ == b'd'[0]):
            return self._getDictionary()
        elif ( type_ == b'l'[0] ):
            return self._getList()
        else:
            raise ValueError("invalid metainfo file")
    def _getDictionary(self):
        dic = {}
        if not (self.str[self.idx] == b'd'[0]):
            raise ValueError("Unrecognizable metainfo file")
        while True:
#            import pdb; pdb.set_trace()
            self.idx += 1
            if ( self.idx >= len(self.str)):
                raise ValueError("invalid bencoded dictionary type")
            key = 0
            value = 0
            # end of dictionary
            if ( self.str[self.idx] == b'e'[0]):
                return dic
            # begining of string for key
            elif ( self.str[self.idx:self.idx+1].decode('utf8').isdigit()):
                key = self._getString()
                self.idx += 1
            # get value (if starts with a string)
            if ( self.str[self.idx : self.idx + 1].decode('utf8').isdigit()):
                value  = self._getString()
            # if the value is an integer
            elif ( self.str[self.idx] == b'i'[0]):
                value = self._getInt()
            # if the value is a list
            elif ( self.str[self.idx] == b'l'[0]):
                value = self._getList()
            # if the value is a nested dictionary
            elif ( self.str[self.idx] == b'd'[0]):
                value = self._getDictionary()
            dic[key] = value
    def _getList(self):
        list_ = []
        if not (self.str[self.idx] == b'l'[0]):
            raise ValueError("Unrecognizable metainfo file")
        while True:
            self.idx += 1
            if ( self.idx >= len(self.str)):
                raise ValueError("invalid bencoded list type")
            item = 0
            # end of the list
            if ( self.str[self.idx] == b'e'[0]):
                return list_
            # begining of string item
            elif ( self.str[self.idx: self.idx +1].decode('utf8').isdigit()):
                item  = self._getString()
            # if the item is an integer
            elif ( self.str[self.idx] == b'i'[0]):
                item = self._getInt()
            # if the item is a nested list
            elif ( self.str[self.idx] == b'l'[0]):
                item = self._getList()
            # if the item is a nested dictionary
            elif ( self.str[self.idx] == b'd'[0]):
                item = self._getDictionary()
            list_.append(item)
    def _getInt(self):
        if not ( self.str[self.idx] == b'i'[0]):
            raise ValueError("invalid bencoded integer type")
        self.idx += 1
        cnt = 0
        while ( self.str[self.idx + cnt] != b'e'[0]):
            cnt += 1
        intval = int(self.str[self.idx : self.idx + cnt])
        self.idx += cnt
        return intval
    def _getString(self):
        # begining of string for key
        if not ( self.str[self.idx:self.idx+1].decode('utf8').isdigit()):
            raise ValueError("invalid bencoded string type")
        strlen = self._getStringLength()
        self.idx += 1
        _str = self.str[self.idx : self.idx + strlen]
        self.idx += strlen - 1
        return _str
    def _getStringLength(self):
        cnt = 0
        while ( self.str[self.idx + cnt:self.idx + cnt + 1].decode('utf8').isdigit()):
            cnt += 1
        numDigits = cnt
        strlen = 0
        for i in range (numDigits):
            strlen += int(self.str[self.idx + i: self.idx + i + 1].decode('utf8'))*10**(numDigits-i-1)
        self.idx += numDigits
        return strlen
