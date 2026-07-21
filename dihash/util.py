import hashlib


def invert_list(lst):
    ret = {}
    for (i, elem) in enumerate(lst):
        ret[elem] = i
    return ret

def escape(s):
    # Replace backslashes with double backslash and quotes with escaped quotes
    return s.replace('\\', '\\\\').replace('"', '\\"')

def to_str(data):
    if isinstance(data, list):
        return "[{}]".format(",".join([to_str(elem) for elem in data]))
    elif isinstance(data, str):
        return '"{}"'.format(escape(data))
    elif isinstance(data, tuple):
        return "({})".format(",".join([to_str(elem) for elem in data]))
    elif isinstance(data, int):
        return str(data)
    else:
        raise TypeError("Unable to call to_str on " + str(data))

def hash_sha256(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()