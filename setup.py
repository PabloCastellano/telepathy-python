#!/usr/bin/python

from distutils.core import setup
from telepathy import __version__

setup(
    name='telepathy-python',
    version=__version__,
    packages=[
        'telepathy',
        'telepathy.client',
        'telepathy.server'
        ],
    )

