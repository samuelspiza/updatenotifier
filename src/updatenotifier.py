#!/usr/bin/env python3
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
[This](http://gist.github.com/616971) is an example for the JSON structure for
this file. In addition to the default way of storing this file locally, there
are currently two ways to access remote files. If '--resource web' is set, the
parameter of '--tools' will be interpreted as an URL. If '--resource gist' is
set, it will be interpreted as 'ID:FILE_NAME' with 'ID' being the Gist ID and
'FILE_NAME' the name of the file in the gist repository.
"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__version__ = "0.6.3"

import re
import codecs
import os
import json
import logging
import logging.handlers
import urllib.request
import urllib.parse
import urllib.error
import gzip
import optparse
import sys
import threading

def getOptions(argv):
    """A method for parsing the argument list."""
    installDirectory = os.path.dirname(os.path.abspath((__file__)))
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output",
                      dest="output", metavar="PATH",
                      default="updatenotifications.htm",
                      help="Change the path of the output file.")
    parser.add_option("-i", "--input",
                      dest="input", metavar="PATH",
                      default=os.path.expanduser("~/updatenotifier.json"),
                      help="Change the path of the input file.")
    parser.add_option("-r", "--resource",
                      dest="resource", metavar="TYPE", default="local",
                      help="Change the resource type to 'web' or 'gist'.")
    parser.add_option("-t", "--tools",
                      dest="tools", metavar="PATH",
                      default=installDirectory + "/toolslist.json",
                      help="Change the path of the tools list file.")
    parser.add_option("-l", "--log",
                      dest="log", action="store_true", default=False,
                      help="Write a log.")
    parser.add_option("-m", "--logPath",
                      dest="logpath", metavar="PATH",
                      default=installDirectory + "/updatenotifier.log",
                      help="Change the path of the log file.")
    return parser.parse_args(argv)[0]

HEADER = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
          'Accept-Language': 'de',
          'Accept-Encoding': 'utf-8'}

def absUrl(site, href):
    """Returns an absolute URL.
    
    It takes the a site and a path (e.g. argument to an 'href' or 'src'
    parameter of a HTML tag). The absolute URL will be composed in the same way
    a web browser does.
    """
    href = href.replace("\\", "/")
    if href.startswith("http://") or href.startswith("https://"):
        return href
    comps = href.split("/")
    if href[:1] == "/":
        comps[0:1] = site.split("/")[:3]
    else:
        comps[0:0] = site.split("/")[:-1]
    i = 2
    while i < len(comps):
        if comps[i] == '.':
            del comps[i]
        elif comps[i] == '..':
            if i > 0 and comps[i-1] != '..':
                del comps[i-1:i+1]
                i -= 1
            else:
                i += 1
        else:
            i += 1
    return "/".join(comps)

def getResponse(url, postData=None):
    """Opens an URL with POST data.
    
    The POST data must be a dictionary.
    """
    if postData is not None:
        postData = urllib.parse.urlencode(postData).encode("utf-8")
    req = urllib.request.Request(url, postData)
    for key in HEADER:
        req.add_header(key, HEADER[key])
    return urllib.request.urlopen(req)

def safeGetResponse(url, postData=None):
    """Opens an URL with POST data and handles exceptions.
    
    Returns None if an error occurs. Catches HTTPError and URLError.
    """
    try:
        return getResponse(url, postData=postData)
    except urllib.error.HTTPError as e:
        if e.code == 302:
            return getResponse(absUrl(url, e.info().get("Location")))
        else:
            print(url, " Error Code: ", e.code)
    except urllib.error.URLError as e:
        print(url, " Reason: ", e.reason)
    return None

def getContentFromResponse(response, bytes=False, encoding="utf-8"):
    if response is None:
        return None
    if response.info().get("Content-Encoding") == "gzip":
        data = gzip.decompress(response.read())
    else:
        data = response.read()
    if bytes:
        return data
    else:
        return data.decode(encoding)

def safeGetContent(url, postData=None, bytes=False, encoding="utf-8"):
    """Opens an URL with POST data and returns decoded UTF-8 string.
    
    Supports GZIP encoded resposes.
    """
    response = safeGetResponse(url, postData)
    return getContentFromResponse(response, bytes=bytes, encoding=encoding)

class ContentAsFileObjectWrapper:
    def __init__(self, content):
        self.content = content

    def read(self):
        return self.content

    def __exit__(self, errorType, value, traceback):
        pass

    def __enter__(self):
        return self

class FormaterSkeleton:
    """A skeleton for a Formater."""
    
    def __init__(self):
        self.lock = threading.Lock()

    def webError(self, name):
        pass

    def failed(self, name, url):
        pass

    def update(self, name, url, installed, version):
        pass

    def upToDate(self, name, installed):
        pass

    def close(self):
        pass

class StreamFormater(FormaterSkeleton):
    """A class for formating the console output.
    
    Provides methods for different results of the update check. The output is
    formated in a table layout. The width of the cols can be passed to the
    Formater on creation and changed via a method.
    """

    def __init__(self, width=(1, 1)):
        """The constructor.
        
        The minimum width of the cols defaults to one.
        """
        super().__init__()
        self.setColWidth(width)

    def setColWidth(self, width=(1, 1)):
        """Method to change the width of the cols.
        
        Width is a tupel of two integers that set the minimum width of first
        and second col. The default values are one.
        """
        self.strWebError = "{0:%s} {1:%s} No HTTP response." % width
        self.strFailed   = "{0:%s} {1:%s} No Match." % width
        self.strUpdate   = "{0:%s} {1:%s} Version {2} available." % width
        self.strUpToDate = "{0:%s} {1:%s}" % width

    def webError(self, name):
        print(self.strWebError.format(name, "Error:"))

    def failed(self, name, url):
        print(self.strFailed.format(name, "Error:"))

    def update(self, name, url, installed, version):
        print(self.strUpdate.format(name, installed, version))

    def upToDate(self, name, installed):
        print(self.strUpToDate.format(name, installed))

class HtmlFormater(FormaterSkeleton):
    """A class for formating the notification file.
    
    Provides methods for different results of the update check. The output is
    formated as a HTML table cell.
    """

    def __init__(self, outputFile):
        """The constructor."""
        super().__init__()
        self.outputFile = outputFile
        self.output = ""
        self.strFailed = """      <tr>
        <td><a href="{0}">{1}</a></td>
        <td>Error:</td>
        <td>No Match.</td>
      </tr>
"""
        self.strUpdate = """      <tr>
        <td><a href="{0}">{1}</a></td>
        <td>{2}</td>
        <td>Version {3} available.</td>
      </tr>
"""
        self.htmlHead  = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Updatenotification</title>
  </head>
  <body>
    <table>
"""
        self.htmlTail  = """    <table>
  <body>
<html>
"""

    def failed(self, name, url):
        self.output += self.strFailed.format(url, name)

    def update(self, name, url, installed, version):
        self.output += self.strUpdate.format(url, name, installed, version)

    def close(self):
        if 0 < len(self.output):
            with codecs.open(self.outputFile, encoding="utf-8", mode="w") as f:
                f.write(self.htmlHead + self.output + self.htmlTail)

class Tool(threading.Thread):
    """A class for each tool to be check.
    
    It provides a method to initiate the check.
    """

    def __init__(self, name, url, regexp, installed):
        """The constructor.
        
        The name is the humanreadable name of the tool. The URL points to the
        download page. The regexp matches a version string in the content of
        the download page. Installed is the version string of the currently
        installed version of the tool on the host. The Formater objects will
        be used to format the different outputs.
        """
        super().__init__()
        self.name      = name
        self.url       = url
        self.regexp    = regexp
        self.installed = installed
        self.encoding  = "utf-8"
        self.formaters = []

    def setEncoding(self, encoding):
        self.encoding = encoding

    def run(self):
        """Method to check if a newer version is available.
        
        It prints the result of the check to the console and updates
        self.notification except the check is successful and no new version is
        available.
        """
        content = safeGetContent(self.url, encoding=self.encoding)
        if content is None:
            self.webError()
        else:
            m = re.search(self.regexp, content)
            if m is None:
                self.failed()
            elif self.installed != m.group(0):
                self.update(self.installed, m.group(0))
            else:
                self.upToDate(self.installed)

    def attachFormater(self, formater):
        self.formaters.append(formater)

    def webError(self):
        logger = logging.getLogger('Tool.check')
        logger.debug("Failed to retrieve HTTP response for %s", self.name)
        for f in self.formaters:
            f.lock.acquire()
            f.webError(self.name)
            f.lock.release()

    def failed(self):
        logger = logging.getLogger('Tool.check')
        logger.debug("Failed to match version string for %s",
                     self.name)
        for f in self.formaters:
            f.lock.acquire()
            f.failed(self.name, self.url)
            f.lock.release()

    def update(self, installed, new):
        logger = logging.getLogger('Tool.check')
        logger.info("%s @ %s -> %s", self.name, installed, new)
        for f in self.formaters:
            f.lock.acquire()
            f.update(self.name, self.url, installed, new)
            f.lock.release()

    def upToDate(self, installed):
        logger = logging.getLogger('Tool.check')
        logger.debug("%s @ %s", self.name, installed)
        for f in self.formaters:
            f.lock.acquire()
            f.upToDate(self.name, installed)
            f.lock.release()

class UpdateNotifier:
    """A class to perform a check for software updates."""

    def __init__(self, outputFile, toolsList, toolsToCheck):
        """The constructor.
        
        OutputFile is the filepath of the file that will be written if at least
        one available update was found or not all matches for version strings
        were successful. ToolsList and ToolsToCheck are dictionaries of the
        corresponding JSON objects.
        """
        logger = logging.getLogger('UpdateNotifier')
        self.outputFile   = outputFile
        self.toolsList    = toolsList
        self.toolsToCheck = {}
        for tool in toolsToCheck:
            if tool in self.toolsList:
                self.toolsToCheck[tool] = toolsToCheck[tool]
            else:
                logger.warning("Unknown tool '%s'.", tool)
        self.formater = [StreamFormater(self.getRowWidth()),
                         HtmlFormater(self.outputFile)]

    def __enter__(self):
        return self

    def __exit__(self, errorType, value, traceback):
        self.closeFormater()

    def closeFormater(self):
        for f in self.formater:
            f.close()

    def getRowWidth(self):
        """Determines the width of the cols for the output."""
        names = [len(self.toolsList[t]['name']) for t in self.toolsToCheck]
        nameLen = max(names)
        # add [6] for "ERROR:"
        versionLen = max([len(v) for v in self.toolsToCheck.values()] + [6])
        return (nameLen, versionLen)

    def check(self):
        """Initiates the check for updates for each tool."""
        tools = []
        for tool in sorted(self.toolsToCheck):
            t = Tool(self.toolsList[tool]['name'],
                     self.toolsList[tool]['url'],
                     self.toolsList[tool]['regexp'],
                     self.toolsToCheck[tool])
            if "encoding" in self.toolsList[tool]:
                t.setEncoding(self.toolsList[tool]['encoding'])
            for f in self.formater:
                t.attachFormater(f)
            t.start()
            tools.append(t)
        for tool in tools:
            tool.join()

class Gist:
    """A class to use files in a gist as FileObjects."""

    def __init__(self, resource):
        """The constructor.
        
        The resource is the gist ID and the name of the file in the gist colon
        seperated.
        """
        self.id, self.fileName = resource.split(":")
        self.repoContent = None
        self.url = None
        self.fileObject = None

    def __enter__(self):
        return self.getFileObject()

    def __exit__(self, errorType, value, traceback):
        pass

    def getRepoContent(self):
        if self.repoContent is None:
            url = "http://gist.github.com/" + self.id
            self.repoContent = safeGetContent(url)
        return self.repoContent

    def getUrl(self):
        if self.url is None:
            regexp = "/raw/%s/[0-9a-f]*/%s" % (self.id, self.fileName)
            m = re.search(regexp, self.getRepoContent())
            self.url = "http://gist.github.com" + m.group(0)
        return self.url

    def getFileObject(self):
        if self.fileObject is None:
            content = safeGetContent(self.getUrl())
            self.fileObject = ContentAsFileObjectWrapper(content)
        return self.fileObject

def main(argv):
    options = getOptions(argv)

    # Configure the logging.
    logging.getLogger().setLevel(logging.INFO)
    if options.log:
        handler = logging.handlers.RotatingFileHandler(
                      options.logpath, maxBytes=65000, backupCount=1)
        formatString = "%(asctime)s %(name)-20s %(levelname)-8s %(message)s"
        handler.setFormatter(logging.Formatter(formatString))
    else:
        handler = logging.handlers.NullHandler()
    logging.getLogger().addHandler(handler)

    logger = logging.getLogger()
    logger.info("updatenotifier.py START")

    # Read the tools and their installed version form the input file
    with open(options.input, "r") as file:
        toolsToCheck = json.load(file)

    # Create the FileObject based on the resource option. The content is a JSON
    # object that contains all supported tools, URLs to their corresponding
    # download pages and a regexp to match the version string on that page.
    if options.resource.lower() == "web":
        fo = ContentAsFileObjectWrapper(safeGetContent(options.tools))
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
