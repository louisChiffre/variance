from collections import namedtuple
import re
from bs4 import BeautifulSoup
import logging
logger = logging.getLogger(__name__)
esc = "'"
# we keep track of the escape characters
medite_special_characters = [esc, "|"]
escape_characters_mapping = {
    # not necessary if they are included in sep parameters
    # "…": "'…",
    # ".": "'.",
    # "»": "'»",
    # "«": "«'",
}

escape_characters_regex = re.escape("|".join(escape_characters_mapping.keys()))
newline = """'|""" + "\n"
mapping = {
    # "…": "'…",
    # ".": "'.",
    # "»": "'»",
    # "«": "«'",
    "<p>": "",
    "</p>": newline,
    "<emph>": "\\",
    "</emph>": "\\",
}

annotation_tags = [
    "pb",
    "div"
]


Replacement = namedtuple("Replacement", "start end old new")
Insertion = namedtuple("Insertion", "start text")
Text = namedtuple('Text', 'text replacements insertions')

def xml2medite(text)->Text:
    """transform xml text to medite text"""
    text_raw = text
    replacements = []

    def gen_regexes():
        # we first match the annotations
        for tag in annotation_tags:
            yield re.compile(f"<{tag}.*?>|</{tag}>")
        def gen():
            yield from mapping.keys()
        yield  re.compile("|".join([re.escape(k) for k in gen()]))

    
    for regex in gen_regexes():
        logger.info(f'replacing {regex=}')
        while match := regex.search(text):
            old = match.group()
            new = mapping.get(old,'')
            start, end = match.span()
            #print(old, start,end, len(text))
            replacement = Replacement(start=start, end=end, old=old, new=new)
            text = text[:start] + new + text[end:]
            replacements.append(replacement)

    z = Text(text=text, replacements=replacements, insertions=[])
    text_ = medite2xml(z)
    #
    assert text_ == text_raw
    return z

def medite2xml(text:Text)->str:
    """transform medite text to xml text"""
    x = text.text
    if not text.insertions:
        for r in text.replacements[::-1]:
            x= x[:r.start] + r.old + x[r.start+len(r.new):]
        return x
    replacements = list(text.replacements)
    insertions = sorted(text.insertions, key=lambda x: x.start)
    insertion, insertions = insertions[0],insertions[1:]
    N = len(insertion.text)
    # we need to correct the insertions that are after the current insertion
    insertions = [k._replace(start=k.start+N) for k in insertions]
    def gen():
        for r in replacements:
            # if the replacement is after the insertion
            if r.start>insertion.start:
                yield r._replace(start= r.start+N)
            else:
                yield r
            
    replacements = list(gen())
    x = x[:insertion.start] + insertion.text + x[insertion.start:]
    return medite2xml(Text(text=x, replacements=replacements, insertions=insertions))

from intervaltree import Interval
def extract(text:Text, start:int, end:int)->str:
    """extract a substring from a text"""
    if start==end:
        return ""
    start_text = medite2xml(text)
    M = Interval(start, end)
    for r in text.replacements:
        change = Interval(r.start, r.end)
        if r.end <= start:
            start += len(r.new) - len(r.old)
            end += len(r.new) - len(r.old)
        elif end < r.start:
            # nothing to do as the change is after the interval
            pass
        else:
            #
            if M.contains_interval(change):
                end += len(r.new) - len(r.old)
            else:
                breakpoint()
    return text.text[start:end]
    
    
    
    
