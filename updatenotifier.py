#!/usr/bin/env python
#
# Copyright (c) 2010, Samuel Spiza
# All rights reserved.
#
"""Update Notifier

A script that checks if updated versions of software is available for download.
"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__copyright__ = "Copyright (c) 2010, Samuel Spiza"
__version__ = "0.1"

import re
import os
import json
import urllib
import urllib2
import sys

opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
urllib2.install_opener(opener)

HEADER = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
          'Accept-Language': 'de',
          'Accept-Encoding': 'utf-8'}

FAILED     = "{0:{1}} {2:{3}} No Match."
UPDATE     = "{0:{1}} {2:{3}} Version {4} available."
UP_TO_DATE = "{0:{1}} {2:{3}}"

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

def main():
    printlog = False
    file = open("updatenotifier.json", "r")
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
        file = open("updatenotifer.log", "w")
        file.write(logout)
        file.close()
    if 0 < len(output):
        file = open("updatenotifications.txt", "w")
        file.write(output)
        file.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
