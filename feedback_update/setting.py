# -*- coding: utf-8 -*-

import argparse
import sys
import logging.config

def basic_logging_config():
    """basic logging setting
    >>> import sys
    >>> sys.argv = ['test.py', '--logging_level', 'DEBUG', '--test2']
    >>> logger = basic_logging_config()
    >>> print sys.argv
    ['test.py', '--test2']
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--logging_level', metavar='LEVEL', help='logging level',
        default='INFO')
    parser.add_argument(
        '--logging_file', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the log should be written')

    args, remaining = parser.parse_known_args()
    sys.argv = sys.argv[:1] + remaining

    logging_config = dict(
        version = 1,
        formatters = {
            'formatter': {
                'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
            }
        },
        handlers = {
            'stream_handler': {
                'class' : 'logging.StreamHandler',
                'stream' : args.logging_file,
                'formatter' : 'formatter',
                'level' : logging.getLevelName(args.logging_level)
            }
        },
        root = {
            'handlers': ['stream_handler'],
            'level': logging.getLevelName(args.logging_level)
        },
    )

    logging.config.dictConfig(logging_config)
