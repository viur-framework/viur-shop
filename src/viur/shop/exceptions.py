from viur.core import errors


class ViURShopException(Exception):
    ...


class InvalidStateError(ViURShopException):
    ...


class ViURShopHttpException(errors.HTTPException):
    ...


class InvalidKeyException(ViURShopHttpException):
    def __init__(self, key: str, argument_name: str = "key"):
        self.key = key
        self.argument_name = argument_name
        super().__init__(
            status=400, name="Bad Request",
            descr=f"The provided key '{key}' (parameter {argument_name}) is not a valid db.Key"
        )
