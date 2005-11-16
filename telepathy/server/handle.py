class Handle(object):
    def __init__(self, id, handle_type, name):
        self._id = id
        self._type = handle_type
        self._name = name

    def get_id(self):
        return self._id
    __int__ = get_id

    def get_type(self):
        return self._type

    def get_name(self):
        return self._name
