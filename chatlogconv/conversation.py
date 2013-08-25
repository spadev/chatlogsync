import util

class Conversation(object):
    def __init__(self, path, source, destination, service, time, images=[]):
        self.source = source
        self.destination = destination
        self.service = service
        self.time = time
        self.path = path
        self.images = images # always relative paths
        self.entries = []

    def __unicode__(self):
        s = 'source: %s, destination: %s, service: %s, time: %s' % \
            (self.source, self.destination, self.service, self.time)
        if self.images:
            s += ' images: %s' % ', '.join(self.images)
        e = ['  '+unicode(x) for x in self.entries]
        if e:
            s += '\n'+'\n'.join(e)
        return s


    def __hash__(self):
        h = hash(self.source)
        for k in ('destination', 'service', 'time'):
            h = h^hash(getattr(self, k))
        for k in ('images', 'entries'):
            h = h^hash(tuple(getattr(self, k)))

        return h

    def __eq__(self, other):
        for k in ('source', 'destination', 'service', 'time',
                  'images', 'entries'):
            if getattr(self, k) != getattr(other, k):
                return False
        return True

class Entry(object):
    def __init__(self, **kwargs):
        self._alias = u''
        self._sender = u''
        self._text = u''
        self.time = None
        self.html = None
        self.type = None

        for k, v in iter(kwargs.items()):
            setattr(self, k, v)

    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, alias):
        self._alias = util.to_unicode(alias)

    @property
    def text(self):
        if not self._text and self.html:
            self._text = util.get_text(self.html)

        return self._text

    @text.setter
    def text(self, text):
        self._text = util.to_unicode(text)

    @property
    def sender(self):
        return self._sender

    @sender.setter
    def sender(self, sender):
        self._sender = util.to_unicode(sender)

    def __unicode__(self):
        return '%s (%s) [%s]: %s' % (self.sender, self.alias,
                                     self.time.strftime('%X'), self.text)

class Message(Entry):
    def __init__(self, alias, sender, time, text='', html=None):
        super(Message, self).__init__(alias=alias, sender=sender, time=time,
                                      text=text, html=html)

class Status(Entry):
    OFFLINE = 1
    ONLINE = 2
    DISCONNECTED = 3
    CONNECTED = 4
    AVAILABLE = 5
    AWAY = 6
    IDLE = 7
    CHATERROR = 10
    PURPLE = 11

    def __init__(self, alias, sender, time, type, text='', html=None):
        super(Status, self).__init__(alias=alias, sender=sender, type=type,
                                     time=time, text=text, html=html)

class Event(Entry):
    WINDOWCLOSED = 1
    WINDOWOPENED = 2

    def __init__(self, alias, sender, time, type, text='', html=None):
        super(Event, self).__init__(alias=alias, sender=sender, type=type,
                                    time=time, text=text, html=html)
