import re

from errors import ParseError

def to_unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

def get_text(nodes):
    textlist = []
    for node in nodes:
        if node.nodeType == node.TEXT_NODE:
            textlist.append(node.data)
        elif node.childNodes:
            textlist.append(get_text(node.childNodes))

    return ''.join(textlist)

def get_html(nodes):
    return ''.join([x.toxml() for x in nodes])

def parse_path(path, pattern):
    s = re.split('<(.*?)>', pattern)
    keys = {}
    for i in range(0, len(s), 2):
        s[i] = re.escape(s[i])
    for i in range(1, len(s), 2):
        key = s[i]
        if key not in keys:
            keys[key] = 0
        keys[key] += 1
        s[i] = "(?P<%s%i>.*?)" % (s[i], keys[key])
    regex_pattern = ''.join(s)
    s = re.search(regex_pattern, path)

    results = {}
    for key, value in iter(s.groupdict().items()):
        k = re.sub('\d', '', key)
        if k in results and results[k] != value:
            raise ParseError('Problem parsing path %s' % path)
        results[k] = value

    return results
