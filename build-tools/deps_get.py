#!/usr/bin/env python

import sys
import json

def main():
    with open(sys.argv[1], 'r') as f:
        lookup = json.load(f)
    entry = lookup[sys.argv[2]];
    if isinstance(entry, str):
        print(entry)
    else:
        print(entry["url"])

if __name__ == "__main__":
    main()
