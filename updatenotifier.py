#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# 
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
# 
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# 
# For more information, please refer to <http://unlicense.org/>
#
"""Update Notifier

A script that checks if updated versions of software is available for download.
"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__license__ = "Public Domain"
__version__ = "0.1.1"

import re
import os
import json
import urllib
import urllib2
import optparse
import sys

JSON_FILE = "updatenotifier.json"
LOG_FILE = "updatenotifer.log"
OUTPUT_FILE = "updatenotifications.txt"

FAILED     = "{0:{1}} {2:{3}} No Match."
UPDATE     = "{0:{1}} {2:{3}} Version {4} available."
UP_TO_DATE = "{0:{1}} {2:{3}}"

opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
urllib2.install_opener(opener)

HEADER = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
          'Accept-Language': 'de',
          'Accept-Encoding': 'utf-8'}

def getOptions(argv):
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output",
                      dest="output", metavar="PATH", default=None,
                      help="Change the path of the output file.")
    parser.add_option("-i", "--input",
                      dest="input", metavar="PATH", default=None,
                      help="Change the path of the input file.")
    return parser.parse_args(argv)[0]

def getResponse(url, postData=None):
    if(postData is not None):
        postData = urllib.urlencode(postData)
    req = urllib2.Request(url, postData, HEADER)
    return urllib2.urlopen(req)

def safe_getResponse(url, postData=None):
    try:
        return getResponse(url, postData=postData)
    except urllib2.HTTPError, e:
        print "Error Code: %s" % e.code
    except ValueError, e:
        print e
    except urllib2.URLError, e:
        print "Reason: %s" % e.reason
    return None

def check(name, url, regexp, current, nameLen, versionLen):
    content = safe_getResponse(url).read()
    m = re.search(regexp, content)
    if m is None:
        out = FAILED.format(name, nameLen, "ERROR:", versionLen)
        return out, out + "\n"
    elif current != m.group(0):
        out = UPDATE.format(name, nameLen, current, versionLen, m.group(0))
        return out, out + "\n"
    else:
        out = UP_TO_DATE.format(name, nameLen, current, versionLen)
        return out, ""

def main(argv):
    options = getOptions(argv)
    printlog = False
    if options.input is not None:
        JSON_FILE = options.input
    file = open(JSON_FILE, "r")
    toolsToCheck = json.loads(file.read())
    file.close()
    nameLen = max([len(i['name']) for i in toolsToCheck])
    # In die Versionsspalte muss "ERROR:" passen.
    versionLen = max([len(i['current']) for i in toolsToCheck] + [6])
    output = ""
    logout = ""
    for tool in toolsToCheck:
        log, out = check(tool['name'], tool['url'], tool['regexp'],
                         tool['current'], nameLen, versionLen)
        print log
        output += out
        logout += log + "\n"
    if printlog:
        file = open(LOG_FILE, "w")
        file.write(logout)
        file.close()
    if 0 < len(output):
        if options.output is not None:
            OUTPUT_FILE = options.output
        file = open(OUTPUT_FILE, "w")
        file.write(output)
        file.close()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
