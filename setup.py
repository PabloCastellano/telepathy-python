#!/usr/bin/python

from distutils.core import setup

setup(
    name='telepathy-python',
    version='0.0.1',
    packages=[
        'telepathy',
        'telepathy.client',
        'telepathy.server'
        ],
    )

