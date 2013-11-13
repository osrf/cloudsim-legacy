#!/usr/bin/env python

import os
import codecs
import re
import sys

# Borrowed from rosunit

## unit test suites are not good about screening out illegal
## unicode characters. This little recipe I from http://boodebr.org/main/python/all-about-python-and-unicode#UNI_XML
## screens these out
RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                 (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                  unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                  unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
_safe_xml_regex = re.compile(RE_XML_ILLEGAL)

def _read_file_safe_xml(test_file, write_back_sanitized=True):
    """
read in file, screen out unsafe unicode characters
"""
    f = None
    try:
        # this is ugly, but the files in question that are problematic
        # do not declare unicode type.
        if not os.path.isfile(test_file):
            raise Exception("test file does not exist")
        try:
            f = codecs.open(test_file, "r", "utf-8" )
            x = f.read()
        except:
            if f is not None:
                f.close()
            f = codecs.open(test_file, "r", "iso8859-1" )
            x = f.read()

        for match in _safe_xml_regex.finditer(x):
            x = x[:match.start()] + "?" + x[match.end():]
        x = x.encode("utf-8")
        if write_back_sanitized:
            with open(test_file, 'w') as h:
                h.write(x)
        return x
    finally:
        if f is not None:
            f.close()

if __name__ == '__main__':
    for f in sys.argv[1:]:
        _read_file_safe_xml(f, True)
