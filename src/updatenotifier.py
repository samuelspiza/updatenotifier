#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

This script helps you keep track of software updates. It can be handy for
software without an effective update mechanism and for rarely used software you
still want to keep up to date.

The Update Notifier script dosen't update software directly. It just simplifies
the way you can check for available updates. 

[Update Notifier](http://github.com/samuelspiza/updatenotifier) is hosted on
Github.

Usage

The script uses two data resources.

Input file
A host specific input file contains the tools you want to check and their
currently installed version. This [template](http://gist.github.com/488675)
contains an example JSON structure for this file.

Toolslist
The second file contains all supported tools, URLs to their corresponding
download pages and a regexp to match the version string on that page.
[This](http://gist.github.com/488675) is an example for the JSON structure for
this file. In addition to the default way of storing this file locally, there
are currently two ways to access remote files. If '--resource web' is set, the
parameter of '--tools' will be interpreted as a URL. If '--resource gist' is
set, it will be interpreted as 'ID|FILE_NAME' with 'ID' being the Gist ID and
'FILE_NAME' the name of the file in the gist repository.
"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__version__ = "0.4"

import re
import os
import json
import logging
import logging.handlers
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
    parser.add_option("-r", "--resource",
                      dest="resource", metavar="TYPE", default="local",
                      help="Change the resource type to 'web' or 'gist'.")
    parser.add_option("-t", "--tools",
                      dest="tools", metavar="PATH",
                      default=os.path.dirname(sys.argv[0])+"/toolslist.json",
                      help="Change the path of the tools list file.")
    parser.add_option("-l", "--log",
                      dest="log", action="store_true", default=False,
                      help="Write a log.")
    parser.add_option("-m", "--logPath",
                      dest="logpath", metavar="PATH",
                      default=os.path.dirname(sys.argv[0])+"/updatenotifier.log",
                      help="Change the path of the log file.")
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
    def __init__(self, outputFile, toolsList, toolsToCheck):
        logger = logging.getLogger('UpdateNotifier')
        self.outputFile   = outputFile
        self.toolsList    = toolsList
        self.toolsToCheck = {}
        for tool in toolsToCheck:
            if tool in self.toolsList:
                self.toolsToCheck[tool] = toolsToCheck[tool]
            else:
                logger.warning("Unknown tool '%s'.", tool)
        replace = self.getRowWidth()
        self.failed   = "{0:%s} {1:%s} No Match." % replace
        self.update   = "{0:%s} {1:%s} Version {2} available." % replace
        self.upToDate = "{0:%s} {1:%s}" % replace
        self.out      = ""

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.write()

    def getRowWidth(self):
        names = [len(self.toolsList[t]['name']) for t in self.toolsToCheck]
        nameLen = max(names)
        # add [6] for "ERROR:"
        versionLen = max([len(v) for v in self.toolsToCheck.values()] + [6])
        return (nameLen, versionLen)

    def check(self):
        for tool in sorted(self.toolsToCheck):
            self.checkTool(self.toolsList[tool]['name'],
                           self.toolsList[tool]['url'],
                           self.toolsList[tool]['regexp'],
                           self.toolsToCheck[tool])

    def checkTool(self, name, url, regexp, installed):
        logger = logging.getLogger('UpdateNotifier.checkTool')
        content = safe_getResponse(url).read()
        m = re.search(regexp, content)
        if m is None:
            out = self.failed.format(name, "ERROR:")
            self.out    += out + "\n"
        elif installed != m.group(0):
            out = self.update.format(name, installed, m.group(0))
            self.out    += out + "\n"
            logger.info("%s @ %s -> %s", name, installed, m.group(0))
        else:
            out = self.upToDate.format(name, installed)
            logger.debug("%s @ %s", name, installed)
        print out

    def write(self):
        if 0 < len(self.out):
            with open(self.outputFile, "w") as file:
                file.write(self.out)

class Gist:
    def __init__(self, resource):
        self.id, self.fileName = resource.split(":")
        self.repoContent = None
        self.url = None
        self.fileObject = None

    def __enter__(self):
        return self.getFileObject()

    def __exit__(self, type, value, traceback):
        pass

    def getRepoContent(self):
        if self.repoContent is None:
            url = "http://gist.github.com/" + self.id
            self.repoContent = safe_getResponse(url).read()
        return self.repoContent

    def getUrl(self):
        if self.url is None:
            regexp = "/raw/%s/[0-9a-f]*/%s" % (self.id, self.fileName)
            m = re.search(regexp, self.getRepoContent())
            self.url = "http://gist.github.com" + m.group(0)
        return self.url

    def getFileObject(self):
        if self.fileObject is None:
            self.fileObject = safe_getResponse(self.getUrl())
        return self.fileObject

def main(argv):
    options = getOptions(argv)

    logging.getLogger('').setLevel(logging.INFO)
    if options.log:
        handler = logging.handlers.RotatingFileHandler(
                      options.logpath, maxBytes=65000, backupCount=1)
        format = "%(asctime)s %(name)-24s %(levelname)-8s %(message)s"
        handler.setFormatter(logging.Formatter(format))
    else:
        # NullHandler is part of the logging package in Python 3.1
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass
        handler = NullHandler()
    logging.getLogger('').addHandler(handler)

    logger = logging.getLogger('')
    logger.info("updatenotifier.py START")

    # Read the tools and their installed version form the input file
    with open(options.input, "r") as file:
        toolsToCheck = json.load(file)

    # Create the FileObject based on the resource option. The content is a JSON
    # object that contains all supported tools, URLs to their corresponding
    # download pages and a regexp to match the version string on that page.
    if options.resource.lower() == "web":
        fo = safe_getResponse(options.tools)
    elif options.resource.lower() == "gist":
        fo = Gist(options.tools)
    else:
        fo = open(options.tools, "r")
    with fo as file:
        toolsList = json.load(file)

    # Check all installed tools for updates
    with UpdateNotifier(options.output, toolsList, toolsToCheck) as un:
        un.check()

    logger.info("updatenotifier.py END")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))