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
__version__ = "0.3"

import re
import os
import json
import urllib
import urllib2
import optparse
import sys

opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
urllib2.install_opener(opener)

HEADER = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
          'Accept-Language': 'de',
          'Accept-Encoding': 'utf-8'}

def getOptions(argv):
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output",
                      dest="output", metavar="PATH",
                      default="updatenotifications.txt",
                      help="Change the path of the output file.")
    parser.add_option("-i", "--input",
                      dest="input", metavar="PATH",
                      default=os.path.expanduser("~/.updatenotifier.json"),
                      help="Change the path of the input file.")
    parser.add_option("-t", "--tools",
                      dest="tools", metavar="PATH",
                      default="toolslist.json",
                      help="Change the path of the tools list file.")
    parser.add_option("-l", "--log",
                      dest="log", action="store_true", default=False,
                      help="Write a full log.")
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

class UpdateNotifier:
    def __init__(self, outputFile, nameLen, versionLen):
        splited = os.path.splitext(outputFile)
        self.outputFile = outputFile
        self.logFile    = splited[0] + ".log"
        self.debugFile  = splited[0] + "-debug" + splited[1]
        replace = (nameLen, versionLen)
        self.failed     = "{0:%s} {1:%s} No Match." % replace
        self.update     = "{0:%s} {1:%s} Version {2} available." % replace
        self.upToDate   = "{0:%s} {1:%s}" % replace
        self.debug      = ""
        self.output     = ""
        self.log        = ""

    def check(self, name, url, regexp, current):
        content = safe_getResponse(url).read()
        m = re.search(regexp, content)
        if m is None:
            log = self.failed.format(name, "ERROR:")
            self.log    += log + "\n"
            self.debug  += "%s\n%s\n" % (name, content)
        elif current != m.group(0):
            log = self.update.format(name, current, m.group(0))
            self.output += log + "\n"
            self.log    += log + "\n"
        else:
            log = self.upToDate.format(name, current)
            self.log    += log + "\n"
        print log

    def write(self, log=False):
        if log:
            file = open(self.logFile, "w")
            file.write(self.log)
            file.close()
        elif 0 < len(self.output):
            file = open(self.outputFile, "w")
            file.write(self.output)
            file.close()
        if 0 < len(self.debug):
            file = open(self.debugFile, "w")
            file.write(self.debug)
            file.close()

def main(argv):
    options = getOptions(argv)
    file = open(options.input, "r")
    toolsToCheck = json.loads(file.read())
    file.close()
    file = open(options.tools, "r")
    toolsList = json.loads(file.read())
    file.close()
    nameLen = max([len(toolsList[tool]['name']) for tool in toolsToCheck])
    # In die Versionsspalte muss "ERROR:" passen.
    versionLen = max([len(current) for current in toolsToCheck.values()] + [6])
    un = UpdateNotifier(options.output, nameLen, versionLen)
    for tool in toolsToCheck:
        un.check(toolsList[tool]['name'], toolsList[tool]['url'],
                 toolsList[tool]['regexp'], toolsToCheck[tool])
    un.write(options.log)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
