"""
Custom exceptions
"""


class NoSignatureInfo(Exception):
    """
    Raised when no signature info is found
    """


class InvalidSignature(Exception):
    """
    Raised when the signature is not validated
    """


class UnknownServiceError(Exception):
    """
    Raised when a service is not known to mc
    """