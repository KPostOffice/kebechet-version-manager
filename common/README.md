# Common bits

This folder is meant for shared bits between the app and the worker. It should
NOT contain functional code but rather common data like enums. It may make more
sense to spec this out to be yaml specs that are read in by the respective
applications rather than a Python module. The reason I made it Python is because
both components are written in Python
