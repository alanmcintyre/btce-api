# Copyright (c) 2013 Alan McIntyre

from HTMLParser import HTMLParser
import datetime
import warnings
from common import BTCEConnection

class BTCEScraper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.messageId = None
        self.messageTime = None
        self.messageUser = None
        self.messageText = None
        self.messages = []    
        self.bitInstantReserves = None
        self.aurumXchangeReserves = None
        
        self.inMessageA = False
        self.inMessageSpan = False
        self.inBitInstantSpan = False
        self.inAurumXchangeSpan = False

    def handle_data(self, data):
        # Capture contents of <a> and <span> tags, which contain
        # the user ID and the message text, respectively.
        if self.inMessageA:
            self.messageUser = data.strip()
        elif self.inMessageSpan:
            self.messageText = data.strip()
        elif self.inBitInstantSpan:
            self.bitInstantReserves = int(data)
        elif self.inAurumXchangeSpan:
            self.aurumXchangeReserves = int(data)
        
    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            # Check whether this <p> tag has id="msgXXXXXX" and 
            # class="chatmessage"; if not, it doesn't contain a message.
            messageId = None
            for k, v in attrs:
                if k == 'id':
                    if v[:3] != 'msg':
                        return
                    messageId = v
                if k == 'class' and v != 'chatmessage':
                    return
            
            # This appears to be a message <p> tag, so set the message ID.
            # Other code in this class assumes that if self.messageId is None,
            # the tags being processed are not relevant.
            if messageId is not None:
                self.messageId = messageId
        elif tag == 'a' and self.messageId is not None:
            # Check whether this <a> tag has class="chatmessage" and a time
            # string in the title attribute; if not, it's not part of a message.
            messageTime = None
            for k, v in attrs:
                if k == 'title':
                    messageTime = v
                if k == 'class' and v != 'chatmessage':
                    return
                    
            if messageTime is None:
                return
            
            # This appears to be a message <a> tag, so remember the message time
            # and set the inMessageA flag so the tag's data can be captured in 
            # the handle_data method.
            self.inMessageA = True
            self.messageTime = messageTime
        elif tag == 'span':
            if self.messageId is not None:
                self.inMessageSpan = True
            else:
                for k, v in attrs:
                    if k == 'id':
                        if v == 'BI_reserve':
                            self.inBitInstantSpan = True
                            return
                        elif v == 'AXC_reserve':
                            self.inAurumXchangeSpan = True
                            return

    def handle_endtag(self, tag):
        if tag == 'p' and self.messageId is not None:
            # exiting from the message <p> tag
            
            # check for invalid message contents
            if self.messageId is None:
                warnings.warn("Missing message ID")
            if self.messageUser is None:
                warnings.warn("Missing message user")
            if self.messageTime is None:
                warnings.warn("Missing message time")
                
            if self.messageText is None:
                # messageText will be None if the message consists entirely
                # of emoticons.
                self.messageText = ''
                
            # parse message time
            t = datetime.datetime.now()
            messageTime = t.strptime(self.messageTime, '%d.%m.%y %H:%M:%S')
                
            self.messages.append((self.messageId, self.messageUser,
                messageTime, self.messageText))
            self.messageId = None
            self.messageUser = None
            self.messageTime = None
            self.messageText = None            
        elif tag == 'a' and self.messageId is not None:
            self.inMessageA = False
        elif tag == 'span':
            if self.messageId is not None:
                self.inMessageSpan = False
           
            if self.inBitInstantSpan:
                self.inBitInstantSpan = False
                
            if self.inAurumXchangeSpan:
                self.inAurumXchangeSpan = False

class ScraperResults:   
    __slots__ = ('messages', 'bitInstantReserves', 'aurumXchangeReserves')
        
                
def scrapeMainPage(connection = None):
    if connection is None:
        connection = BTCEConnection()
    
    parser = BTCEScraper()
    parser.feed(connection.makeRequest('/'))
    parser.close()
    
    r = ScraperResults()
    r.messages = parser.messages
    r.bitInstantReserves = parser.bitInstantReserves
    r.aurumXchangeReserves = parser.aurumXchangeReserves
    
    return r
