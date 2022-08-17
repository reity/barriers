"""
Python decorators for including/removing type checks, value/bounds checks, and
other code blocks within the compiled bytecode of functions and methods.
"""
from __future__ import annotations
import doctest

class barriers: # pylint: disable=too-few-public-methods
    """
    Class for per-module configuration objects that can be used to define and
    toggle inclusion of categories of checks, for decorating functions, and for
    marking code blocks.

    >>> b = barriers()
    """

if __name__ == '__main__':
    doctest.testmod() # pragma: no cover
