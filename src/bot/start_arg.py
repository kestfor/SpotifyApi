class StartArg:
    class Type:
        AUTH = f'_auth_'
        TOKEN = '_token_'
        EMPTY = ''

    def _parse(self, raw_string: str) -> (str, str):
        if raw_string.startswith(self.Type.AUTH):
            return self.Type.AUTH, raw_string[len(self.Type.AUTH):]
        elif raw_string.startswith(self.Type.TOKEN):
            return self.Type.TOKEN, raw_string[len(self.Type.TOKEN):]
        else:
            return self.Type.EMPTY, ""

    def __init__(self, args):
        args = "" if args is None else args
        self._type, self._value = self._parse(args)

    @property
    def value(self):
        return self._value

    @property
    def type(self):
        return self._type
