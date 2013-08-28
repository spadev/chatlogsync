from __future__ import unicode_literals
from __future__ import absolute_import

class ParseError(StandardError):
    """Raised when there is an error parsing data"""
class ArgumentError(StandardError):
    """Raised when an invalid argument is encountered"""
class AbortedError(StandardError):
    """Raised when user aborts program"""
