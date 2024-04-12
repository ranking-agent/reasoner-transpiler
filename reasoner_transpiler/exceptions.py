
class InvalidPredicateError(Exception):
    def __init__(self, error_message: str):
        super().__init__(error_message)


class InvalidQualifierError(Exception):
    def __init__(self, error_message: str):
        super().__init__(error_message)


class InvalidQualifierValueError(Exception):
    def __init__(self, error_message: str):
        super().__init__(error_message)


class UnsupportedError(Exception):
    def __init__(self, error_message: str):
        super().__init__(error_message)
