class Bencode(object):
    def __init__(self, str_=''):
        self.str = str_
        self.idx = 0 # index position   
    @staticmethod
    def encodeDict(dict_):
        if not (type(dict_) is dict):
            raise ValueError("not a valid dictionary")
        retval = 'd'
        # sort the dictionary based on the keys
        sortedKeys = []
        for key in dict_.keys():
            sortedKeys.append(key)
        sortedKeys.sort()
        for key in sortedKeys:  
            strlen = len(key)
            retval += str(strlen) + ":" + key
            val = dict_[key]
            valType = type(val)
            if ( valType is str):
                strlen = len(val)
                retval += str(strlen) + ":" + val
            elif ( valType is int):
                retval += "i" + str(val) + "e"
            elif ( valType is list):
                retval += Bencode.encodeList(val)
            elif ( valType is dict):
                retval += Bencode.encodeDict(val)
            else:
                raise ValueError("unknown type value in the dictionary")
        retval += "e"
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
                retval += str(strlen) + ":" + item
            elif ( itemType is int):
                retval += "i" + str(item) + "e"
            elif ( itemType is list):
                retval += Bencode.encodeList(item)
            elif ( itemType is dict):
                retval += Bencode.encodeDict(item)
            else:
                raise ValueError("unknown type item in the list")
        retval += "e"
        return retval
    def decode(self, str_=''):
        self.idx = 0
        if str_:
            self.str = str_
        type_ = self.str[self.idx]
        if ( type_ == 'd'):
            return self._getDictionary()
        elif ( type_ == 'l' ):
            return self._getList()
        else:
            raise ValueError("invalid metainfo file")
    def _getDictionary(self):
        dic = {}
        if not (self.str[self.idx] == 'd'):
            raise ValueError("Unrecognizable metainfo file")
        while True:
            self.idx += 1
            if ( self.idx >= len(self.str)):
                raise ValueError("invalid bencoded dictionary type")
            key = 0
            value = 0
            # end of dictionary
            if ( self.str[self.idx] == 'e'):
                return dic
            # begining of string for key
            elif ( self.str[self.idx].isdigit()):
                key = self._getString()
                self.idx += 1
            # get value (if starts with a string)
            if ( self.str[self.idx].isdigit()):
                value  = self._getString()
            # if the value is an integer
            elif ( self.str[self.idx] == 'i'):
                value = self._getInt()
            # if the value is a list
            elif ( self.str[self.idx] == 'l'):
                value = self._getList()
            # if the value is a nested dictionary
            elif ( self.str[self.idx] == 'd'):
                value = self._getDictionary()
            dic[key] = value
    def _getList(self):
        list_ = []
        if not (self.str[self.idx] == 'l'):
            raise ValueError("Unrecognizable metainfo file")
        while True:
            self.idx += 1
            if ( self.idx >= len(self.str)):
                raise ValueError("invalid bencoded list type")
            item = 0
            # end of the list
            if ( self.str[self.idx] == 'e'):
                return list_
            # begining of string item
            elif ( self.str[self.idx].isdigit()):
                item  = self._getString()
            # if the item is an integer
            elif ( self.str[self.idx] == 'i'):
                item = self._getInt()
            # if the item is a nested list
            elif ( self.str[self.idx] == 'l'):
                item = self._getList()
            # if the item is a nested dictionary
            elif ( self.str[self.idx] == 'd'):
                item = self._getDictionary()
            list_.append(item)
    def _getInt(self):
        if not ( self.str[self.idx] == 'i'):
            raise ValueError("invalid bencoded integer type")
        self.idx += 1
        cnt = 0
        while ( self.str[self.idx + cnt] != 'e'):
            cnt += 1
        intval = int(self.str[self.idx : self.idx + cnt])
        self.idx += cnt
        return intval
    def _getString(self):
        # begining of string for key
        if not ( self.str[self.idx].isdigit()):
            raise ValueError("invalid bencoded string type")
        strlen = self._getStringLength()
        self.idx += 1
        _str = self.str[self.idx : self.idx + strlen]
        self.idx += strlen - 1
        return _str
    def _getStringLength(self):
        cnt = 0
        while ( self.str[self.idx + cnt].isdigit()):
            cnt += 1
        numDigits = cnt
        strlen = 0
        for i in range (numDigits):
            strlen += int(self.str[self.idx + i])*10**(numDigits-i-1)
        self.idx += numDigits
        return strlen
