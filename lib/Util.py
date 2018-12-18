import re


def to_snake_case(name, separator="_", case=False):
    """Transforms a `CamelCased` string to `snake_cased` string.

    :param separator: The snake sepator
    :param case: if case of the result should be adapted: upper-case (`True`), lower-case (`False`), unchanged (`None`)
    """

    regex = r'\1' + separator + r'\2'
    sub = re.sub('(.)([A-Z][a-z]+)', regex, name)
    result = re.sub('([a-z0-9])([A-Z])', regex, sub)
    if case is not None and case:
        result = result.upper()
    elif case is not None and not case:
        result = result.lower()
    return result
