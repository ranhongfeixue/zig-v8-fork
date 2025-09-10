#!/usr/bin/env python

import sys
import json

def Var(arg):
    if arg == 'chromium_url':
        return 'https://chromium.googlesource.com'
    return '@' + arg

def Str(arg):
    return '@' + arg

def main():
    with open(sys.argv[1], 'r') as f:
        content = f.read()

    out = {}
    exec(content, globals(), out)
    print(json.dumps(out['deps']))

if __name__ == "__main__":
    main()
