

class EDecaErrorParse(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class EDecaFileExists(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class EDecaFileMissing(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class EDecaBuildError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class EDecaIncorrectFileFormat(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class EDecaOutOfData(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class EDecaUnknownCompressionType(Exception):
    def __init__(self, type_id, *args, **kwargs):
        Exception.__init__(self, *args)
        self.type_id = type_id


class EDecaMissingAdfType(Exception):
    def __init__(self, type_id, *args, **kwargs):
        Exception.__init__(self, *args)
        self.type_id = type_id
