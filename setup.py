#!/usr/bin/python

from distutils.core import setup

setup(
    name='telepathy-python',
    version='0.13.3',
    packages=[
        'telepathy',
        'telepathy.client',
        'telepathy.server'
        ],
    )

