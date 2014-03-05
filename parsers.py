'''
Created on Jan 12, 2010

@author: tpetr
'''

import re, sgmllib

PP_STARTEND_TAG = 1
PP_START_TAG = 2
PP_END_TAG = 3
PP_CHAR_REF = 4
PP_ENTITY_REF = 5
PP_DATA = 6
PP_COMMENT = 7
PP_DECL = 8
PP_PI = 9

class ParsedCourse(object):
    def __init__(self, subject, number, title, id):
        self.subject = subject
        self.number = number
        self.title = title
        self.id = id
        self.sections = []
    
    def __repr__(self):
        return '<ParsedCourse "%s %s">' % (self.subject, self.number)

class ParsedSection(object):
    def __init__(self, course, type, school_id):
        self.type = type
        self.school_id = school_id
        self.ins = set()
        self.dts = []

class ParsedMeetingTime(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.mon = False
        self.tue = False
        self.wed = False
        self.thu = False
        self.fri = False
    
    def __repr__(self):
        return '<ParsedMeetingTime "%s to %s">' % (self.start, self.end)

class ParsedLocation(object):
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return '<ParsedLocation "%s">' % (self.name)

class NoMoreTokensError(Exception): pass

class Token(object):
    def __init__(self, type, data, attrs=()):
        self.type = type
        self.data = data
        self.attrs = dict(attrs)
        
    def __eq__(self, other):
        if isinstance(other, Token):
            return ((self.type == other.type) and (self.data == other.data) and (self.attrs == other.attrs))
        elif isinstance(other, Tag):
            return other == self
        else:
            return False
            
    def __getitem__(self, key): return self.attrs.get(key, None)
    
    def __ne__(self, other): return not self.__eq__(other)
    
    def __repr__(self):
        args = ", ".join(map(repr, [self.type, self.data, self.attrs]))
        return self.__class__.__name__+"(%s)" % args

class Tag(object):
    def __init__(self, name, type=None, eq={}, startswith={}):
        self.name = name
        self.attrs_eq = eq
        self.attrs_startswith = startswith
        self.type = type
    
    def __eq__(self, t):
        if isinstance(t, Token):
            if self.name != t.data: return False
            if self.type and self.type != t.type: return False
            
            for k, v in self.attrs_eq.items():
                if t.attrs.get(k, None) != v: return False
            
            for k, v in self.attrs_startswith.items():
                if not t.attrs.get(k, '').startswith(v): return False
            return True
        elif isinstance(t, tuple):
            type, tag, attrs = t
            attrs = dict(attrs)
            
            if self.name != tag: return False
            if self.type and self.type != type: return False
            
            for k, v in self.attrs_eq.items():
                if attrs.get(k, None) != v: return False
            
            for k, v in self.attrs_startswith.items():
                if not attrs.get(k, '').startswith(v): return False
            return True
        return False
    
    def __repr__(self):
        return "<%s %s eq=%s startswith=%s>" % (self.__class__.__name__, self.name, self.attrs_eq, self.attrs_startswith)

class StartTag(Tag):
    def __init__(self, *args, **kwargs):
        super(StartTag, self).__init__(*args, **kwargs)
        self.type = PP_START_TAG

class EndTag(Tag):
    def __init__(self, name):
        super(EndTag, self).__init__(name)
        self.type = PP_END_TAG

def iter_until_exception(fn, exception, *args, **kwds):
    while 1:
        try:
            yield fn(*args, **kwds)
        except exception:
            raise StopIteration

class _AbstractParser:
    chunk = 1024
    compress_re = re.compile(r"\s+")
    def __init__(self, fh):
        self._fh = fh
        self._tokenstack = []  # FIFO
    
    def update(self, fh, resume=None):
        self._fh = fh
        self._tokenstack = []
        if resume:
            return self.seek(resume)

    def __iter__(self): return self
    
    def seek(self, token, until=None):
        if token.type is None: token.type = PP_START_TAG
        args = (token.name,)
        if until:
            args = args + (until.name,)
            if not until.type: until.type = PP_END_TAG
        
        try:
            while 1:
                t = self.get_tag(*args)
                if until and until == t: return None
                if token == t: return t
        except NoMoreTokensError: pass
        
        return None
    
    def tags(self, token, until=None):
        args = (token.name,)
        if until:
            args = args + (until.name,)
            if not until.type: until.type = PP_END_TAG
        
        while 1:
            try:
                t = self.get_tag(*args)
                if until and until == t: raise StopIteration
                if token == t: yield t
            except NoMoreTokensError:
                raise StopIteration

    def tokens(self, *tokentypes):
        return iter_until_exception(self.get_token, NoMoreTokensError, *tokentypes)

    def next(self):
        try:
            return self.get_token()
        except NoMoreTokensError:
            raise StopIteration()

    def get_token(self, *tokentypes):
        while 1:
            while self._tokenstack:
                token = self._tokenstack.pop(0)
                if tokentypes:
                    if token.type in tokentypes:
                        return token
                else:
                    return token
            data = self._fh.read(self.chunk)
            if not data:
                raise NoMoreTokensError()
            self.feed(data)

    def unget_token(self, token):
        self._tokenstack.insert(0, token)

    def get_tag(self, *names):
        while 1:
            tok = self.get_token()
            if tok.type not in (PP_START_TAG, PP_END_TAG, PP_STARTEND_TAG):
                continue
            if names:
                if tok.data in names:
                    return tok
            else:
                return tok

    def get_text(self, endat=None):
        text = []
        tok = None
        while 1:
            try:
                tok = self.get_token()
            except NoMoreTokensError:
                # unget last token (not the one we just failed to get)
                if tok: self.unget_token(tok)
                break
            if tok.type == PP_DATA:
                text.append(tok.data)
            elif tok.type == PP_ENTITY_REF:
                if tok.data == 'nbsp':
                    pass
                elif tok.data == 'amp':
                    text.append('&')
                else:
                    text.append("&%s;" % tok.data)
            elif tok.type == PP_CHAR_REF:
                text.append(tok.data)
            elif tok.type in (PP_START_TAG, PP_END_TAG, PP_STARTEND_TAG):
                tag_name = tok.data
                if endat is None or endat == (tok.type, tag_name):
                    self.unget_token(tok)
                    break
        return "".join(text)

    def get_compressed_text(self, *args, **kwds):
        text = self.get_text(*args, **kwds)
        text = text.strip()
        return self.compress_re.sub(" ", text)

    def handle_startendtag(self, tag, attrs):
        self._tokenstack.append(Token(PP_STARTEND_TAG, tag, attrs))
    def finish_starttag(self, tag, attrs):
        self._tokenstack.append(Token(PP_START_TAG, tag, attrs))
    def finish_endtag(self, tag):
        self._tokenstack.append(Token(PP_END_TAG, tag))
    def handle_charref(self, name):
        self._tokenstack.append(Token(PP_CHAR_REF, name))
    def handle_entityref(self, name):
        self._tokenstack.append(Token(PP_ENTITY_REF, name))
    def handle_data(self, data):
        self._tokenstack.append(Token(PP_DATA, data))
    def handle_comment(self, data):
        self._tokenstack.append(Token(PP_COMMENT, data))
    def handle_decl(self, decl):
        self._tokenstack.append(Token(PP_DECL, decl))
    def unknown_decl(self, data):
        # XXX should this call self.error instead?
        #self.error("unknown declaration: " + `data`)
        self._tokenstack.append(Token(PP_DECL, data))
    def handle_pi(self, data):
        self._tokenstack.append(Token(PP_PI, data))

    def unescape_attrs(self, attrs):
        escaped_attrs = []
        for key, val in attrs:
            escaped_attrs.append((key, self.unescape_attr(val)))
        return escaped_attrs

class PullParser(_AbstractParser, sgmllib.SGMLParser):
    def __init__(self, *args, **kwargs):
        sgmllib.SGMLParser.__init__(self)
        _AbstractParser.__init__(self, *args, **kwargs)
