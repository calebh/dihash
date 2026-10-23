import hashlib


def invert_list(lst):
    ret = {}
    for (i, elem) in enumerate(lst):
        ret[elem] = i
    return ret

def escape(s):
    # Replace backslashes with double backslash and quotes with escaped quotes
    return s.replace('\\', '\\\\').replace('"', '\\"')

def encode(data):
    if isinstance(data, list):
        return f"[{','.join(encode(elem) for elem in data)}]"
    elif isinstance(data, str):
        return f'"{escape(data)}"'
    elif isinstance(data, tuple):
        return f"({','.join(encode(elem) for elem in data)})"
    elif isinstance(data, int):
        return str(data)
    else:
        raise TypeError("Unable to call to_str on " + str(data))

def hash_sha256(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def invert_dict(d):
    return {v: k for (k, v) in d.items()}
