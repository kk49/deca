import os

class UniPath():
    def __init__():
        pass

    def abspath(path):
        return __class__.unify(os.path.abspath(path))
    
    def basename(path):
        return os.path.basename(path)

    def dirname(path):
        return __class__.unify(os.path.dirname(path))

    def exists(path):
        return os.path.exists(path)
    
    def expanduser(path):
        return os.path.expanduser(path)

    def isdir(path):
        return os.path.isdir(path)

    def isfile(path):
        return os.path.isfile(path)

    def join(path, *paths):
        return __class__.unify(os.path.join(path, *paths))

    def normpath(path):
        return __class__.unify(os.path.normpath(path))

    def split(path):
        head, tail = os.path.split(path)
        return __class__.unify(head), __class__.unify(tail)

    def splitext(path):
        root, ext = os.path.splitext(path)
        return __class__.unify(root), ext

    def unify(path):
        if isinstance(path, bytes):
            sep = b'\\'
            extsep = b'/'
        else:
            sep = '\\'
            extsep = '/'
        return path.replace(sep, extsep)
    
