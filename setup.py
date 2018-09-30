#! /usr/bin/env python
#
# Copyright (C) 2018 Mikko Kotila

DESCRIPTION = "Randomizer"
LONG_DESCRIPTION = """\
Randomizer provides a simple utility to access random methods in a unified
manner. The package implements pseudo, quasi, and true random methods, including
an actual quantum random method and ambience sound based true random method.
"""

DISTNAME = 'randomizer'
MAINTAINER = 'Mikko Kotila'
MAINTAINER_EMAIL = 'mailme@mikkokotila.com'
URL = 'http://autonom.io'
LICENSE = 'MIT'
DOWNLOAD_URL = 'https://github.com/autonomio/randomizer/'
VERSION = '0.1.1'

try:
    from setuptools import setup
    _has_setuptools = True
except ImportError:
    from distutils.core import setup


def check_dependencies():

    install_requires = []

    try:
        import numpy
    except ImportError:
        install_requires.append('numpy')

    try:
        import matplotlib
    except ImportError:
        install_requires.append('matplotlib')

    return install_requires


if __name__ == "__main__":

    install_requires = check_dependencies()

    setup(name=DISTNAME,
          author=MAINTAINER,
          author_email=MAINTAINER_EMAIL,
          maintainer=MAINTAINER,
          maintainer_email=MAINTAINER_EMAIL,
          description=DESCRIPTION,
          long_description=LONG_DESCRIPTION,
          license=LICENSE,
          url=URL,
          version=VERSION,
          download_url=DOWNLOAD_URL,
          install_requires=install_requires,
          packages=['randomizer',
                    'randomizer.lhs_sudoku',
                    'randomizer.hypercube',
                    'randomizer.sobol',
                    'randomizer.quantum',
                    'randomizer.ambient'],

          classifiers=[
                 'Intended Audience :: Science/Research',
                 'Programming Language :: Python :: 3.6',
                 'License :: OSI Approved :: MIT License',
                 'Topic :: Scientific/Engineering :: Mathematics',
                 'Operating System :: POSIX',
                 'Operating System :: Unix',
                 'Operating System :: MacOS'],)
