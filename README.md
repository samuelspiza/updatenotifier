Update Notifier
===============

This script helps you keep track of software updates. It can be handy for
software without an effective update mechanism and for rarely used software you
still want to keep up to date.

The Update Notifier script dosen't update software directly. It just simplifies
the way you can check for available updates. 

[Update Notifier](http://github.com/samuelspiza/updatenotifier) is hosted on
Github.

Usage
-----

The script uses two data resources.

### Input file ###
A host specific input file contains the tools you want to check and their
currently installed version. This [template](http://gist.github.com/488675)
contains an example JSON structure for this file.

### Toolslist ###
The second file contains all supported tools, URLs to their corresponding
download pages and a regexp to match the version string on that page.
[This](http://gist.github.com/488675) is an example for the JSON structure for
this file. In addition to the default way of storing this file locally, there
are currently two ways to access remote files. If '--resource web' is set, the
parameter of '--tools' will be interpreted as a URL. If '--resource gist' is
set, it will be interpreted as 'ID|FILE_NAME' with 'ID' being the Gist ID and
'FILE_NAME' the name of the file in the gist repository.
