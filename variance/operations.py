from collections import namedtuple
import functools
import re
from bs4 import BeautifulSoup
import logging

from intervaltree import Interval

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
newline = "\n"
mapping = {
    # "…": "'…",
    # ".": "'.",
    # "»": "'»",
    # "«": "«'",
    "</p><p>": newline,
    "<p>": "",
    "</p>": newline,
    "<p/>": newline,
    "<emph>": "\\",
    "</emph>": "\\",
}

annotation_tags = ["pb", "div"]


Replacement = namedtuple("Replacement", "start end old new")
Insertion = namedtuple("Insertion", "start text")

# TODO remove insertions as it is it can be expressed as a replacement
Text = namedtuple("Text", "text replacements insertions")


def xml2medite(text: str) -> Text:
    """transform xml text to medite text"""
    text_raw = text
    replacements = ()

    def gen_regexes():
        # we first match the annotations
        for tag in annotation_tags:
            yield re.compile(f"<{tag}.*?>|</{tag}>")

        def gen():
            yield from mapping.keys()

        yield re.compile("|".join([re.escape(k) for k in gen()]))

    for regex in gen_regexes():
        logger.info(f"replacing {regex=}")
        while match := regex.search(text):
            old = match.group()
            new = mapping.get(old, "")
            start, end = match.span()
            # print(old, start,end, len(text))
            replacement = Replacement(start=start, end=end, old=old, new=new)
            text = text[:start] + new + text[end:]
            logger.debug(f"[{repr(old):<15}] --> [{repr(new)}]")

            replacements = replacements + (replacement,)
    # there are actually no insertions necessary
    z = Text(text=text, replacements=replacements, insertions=())
    # We verify the operation is reversible
    text_ = medite2xml(z)
    assert text_ == text_raw

    # we verifyt we can reverse the transormation
    z_ = reverse_transform(z)
    assert z_.text == text_raw
    return z


@functools.lru_cache(maxsize=128)
def reverse_transform(text: Text) -> Text:
    """reverse the transformation"""
    x = text.text
    assert not text.insertions
    # if we have no transformations, we can just return the text
    if not text.replacements:
        return text
    replacements = ()
    for r in text.replacements[::-1]:
        replacement = Replacement(
            start=r.start, end=r.start + len(r.new), old=r.new, new=r.old
        )
        replacements = replacements + (replacement,)
        x = x[: r.start] + r.old + x[r.start + len(r.new) :]
    return Text(text=x, replacements=replacements, insertions=())


def medite2xml(text: Text) -> str:
    """transform medite text to xml text"""
    x = text.text
    if not text.insertions:
        # we start with the last replacement and go backward
        for r in text.replacements[::-1]:
            # we replace the new with the old
            x = x[: r.start] + r.old + x[r.start + len(r.new) :]
        return x
    replacements = list(text.replacements)
    insertions = sorted(text.insertions, key=lambda x: x.start)
    insertion, insertions = insertions[0], insertions[1:]
    N = len(insertion.text)
    # we need to correct the insertions that are after the current insertion
    insertions = [k._replace(start=k.start + N) for k in insertions]

    def gen():
        for r in replacements:
            # if the replacement is after the insertion
            if r.start > insertion.start:
                yield r._replace(start=r.start + N)
            else:
                yield r

    replacements = list(gen())
    x = x[: insertion.start] + insertion.text + x[insertion.start :]
    # we apply recursively the function until there are no more insertions
    return medite2xml(Text(text=x, replacements=replacements, insertions=insertions))


def extract(text: Text, start: int, end: int) -> str:
    """retrieve what has become of the original between start and end"""
    start_, end_ = start, end
    # old_txt = text[start:end]
    text_ = reverse_transform(text)
    assert not text.insertions
    if start == end:
        return ""
    if not start < end:
        raise IndexError("start should be less than end {start=}, {end=}")
    for xr in text.replacements:
        # we go through each replacement
        M = Interval(start, end)
        change = Interval(xr.start, xr.end)
        # if there are portions
        if xr.end <= start:
            # we need to offset by how much the string has grown/shrunk
            start += len(xr.new) - len(xr.old)
            end += len(xr.new) - len(xr.old)
        # if the changes are after the portion we are looking at, there is nothing to do
        elif end <= xr.start:
            # nothing to do as the change is after the interval
            pass
        else:
            # breakpoint()
            if M.contains_interval(change):
                end += len(xr.new) - len(xr.old)
            else:
                raise IndexError(f"Cannot extract replaced portions")

    if start_ == 0:
        start = 0
    if end_ >= len(text_.text):
        end = len(text.text)
    return text.text[start:end]
