import util

class Conversation(object):
    def __init__(self, source, destination, protocol, time):
        self.source = source
        self.destination = destination
        self.protocol = protocol
        self.time = time
        self.entries = []

    def __unicode__(self):
        s = 'source: %s, destination: %s, protocol: %s, time: %s\n' % \
            (self.source, self.destination, self.protocol, self.time)
        s += '\n'.join(['  '+unicode(x) for x in self.entries])
        return s

class Entry(object):
    def __init__(self, **kwargs):
        self.alias = ''
        self.sender = ''
        self.time = None
        self.text = ''
        self.html = ''
        self.type = None

        for k, v in iter(kwargs.items()):
            setattr(self, k, v)

        self.alias = util.to_unicode(self.alias)
        self.sender = util.to_unicode(self.sender)
        self.text = util.to_unicode(self.text)
        self.html = util.to_unicode(self.html)

    def __unicode__(self):
        return '%s (%s) [%s]: %s' % (self.sender, self.alias,
                                     self.time.strftime('%X'), self.text)

class Message(Entry):
    def __init__(self, alias, sender, time, text, html=None):
        super(Message, self).__init__(alias=alias, sender=sender,
                                      text=text, html=html)

class Status(Entry):
    OFFLINE = 0
    ONLINE = 1
    DISCONNECTED = 2
    CONNECTED = 3
    AVAILABLE = 5
    AWAY = 6
    IDLE = 7
    CHATERROR = 10
    PURPLE = 11

    def __init__(self, alias, sender, time, type, text, html=None):
        super(Status, self).__init__(alias=alias, sender=sender, type=type,
                                     text=text, html=html)

class Event(Entry):
    WINDOWCLOSED = 0
    WINDOWOPENED = 1

    def __init__(self, alias, sender, time, type, text, html=None):
        super(Event, self).__init__(alias=alias, sender=sender,
                                    text=text, html=html)
