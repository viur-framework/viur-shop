class Sentinel:
    """
    A unique sentinel class used as a special marker value.

    An instance of this class can be used to indicate, for example,
    a unique default value or a special state that is distinct from
    normal values.

    Attributes
    ----------
    - The representation is ``<SENTINEL>`` for improved readability during debugging.
    - The boolean evaluation is ``False``, so the sentinel behaves as
      falsey in conditions like ``if sentinel:``.
    """

    def __repr__(self) -> str:
        return "<SENTINEL>"

    def __bool__(self) -> bool:
        return False
