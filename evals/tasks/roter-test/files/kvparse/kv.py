def parse(text):
    """'a=1;b=2' -> {'a': '1', 'b': '2'}"""
    result = {}
    for pair in text.split(";"):
        if not pair:
            continue
        key, value = pair.split("=")[:2]
        result[key] = value
    return result
