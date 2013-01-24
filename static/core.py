#!/usr/bin/env python
# -*- coding: utf-8 -*-


from clint import args
from clint.textui import puts, indent, colored
from .utils import get_app_root, NotFoundAppRoot
import sys
import os


def pull():
    try:
        app_root = get_app_root()
        with indent(2, quote=colored.blue('#')):
            puts(colored.green('App root at: %s' % app_root))
    except NotFoundAppRoot:
        with indent(2, quote=colored.blue('#')):
            puts(colored.red('Not a app dir (or any of the parent directories)'))
        sys.exit(1)


def main():
    if args.not_files[0]:
        pull()

if __name__ == '__main__':
    main()
