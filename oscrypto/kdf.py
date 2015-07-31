# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import hashlib
from datetime import datetime

if sys.platform == 'darwin':
    from ._osx.util import pbkdf2, pkcs12_kdf, rand_bytes  #pylint: disable=W0611
elif sys.platform == 'win32':
    from ._win.util import pbkdf2, pkcs12_kdf, rand_bytes  #pylint: disable=W0611
else:
    from ._openssl.util import pbkdf2, pkcs12_kdf, rand_bytes  #pylint: disable=W0611


if sys.version_info < (3,):
    byte_cls = str
    int_types = (int, long)  #pylint: disable=E0602

else:
    byte_cls = bytes
    int_types = int


def determine_pbkdf2_iterations(hash_algorithm, key_length, target_ms=100, quiet=False):
    """
    Runs pbkdf2() until the derivation process takes a number of milliseconds.
    Use this on a production machine to dynamically adjust the number of
    iterations as high as you can.

    :param hash_algorithm:
        The string name of the hash algorithm to use: "md5", "sha1", "sha224", "sha256", "sha384", "sha512"

    :param key_length:
        The length of the desired key in bytes

    :param target_ms:
        The number of milliseconds the derivation should take

    :param quiet:
        If no output should be printed as attempts are made

    :return:
        An integer number of iterations of PBKDF2 using the specified hash
        that will take at least target_ms
    """

    if hash_algorithm not in {'sha1', 'sha224', 'sha256', 'sha384', 'sha512'}:
        raise ValueError('hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384", "sha512", not %s' % repr(hash_algorithm))

    if not isinstance(key_length, int_types):
        raise ValueError('key_length must be an integer, not %s' % key_length.__class__.__name__)

    if key_length < 1:
        raise ValueError('key_length must be greater than 0 - is %s' % repr(key_length))

    if not isinstance(target_ms, int_types):
        raise ValueError('target_ms must be an integer, not %s' % target_ms.__class__.__name__)

    if target_ms < 1:
        raise ValueError('target_ms must be greater than 0 - is %s' % repr(target_ms))

    if pbkdf2.pure_python:
        raise OSError('Only a very slow, pure-python version of PBKDF2 is available, making this function useless')

    iterations = 10000
    password = 'this is a test'.encode('utf-8')
    salt = rand_bytes(key_length)

    def _measure():
        start = datetime.now()
        pbkdf2(hash_algorithm, password, salt, iterations, key_length)
        length = datetime.now() - start
        observed_ms = int(length.total_seconds() * 1000)
        if not quiet:
            print('%s iterations in %sms' % (iterations, observed_ms))
        return 1.0 / target_ms * observed_ms

    # Measure the initial guess, then estimate how many iterations it would
    # take to reach 1/2 of the target ms and try it to get a good final number
    fraction = _measure()
    iterations = int(iterations / fraction / 2.0)

    fraction = _measure()
    return int(round(iterations / fraction, -3))


def pbkdf1(hash_algorithm, password, salt, iterations, key_length):
    """
    An implementation of PBKDF1 - should only be used for interop with legacy
    systems, not new architectures

    :param hash_algorithm:
        The string name of the hash algorithm to use: "md2", "md5", "sha1"

    :param password:
        A byte string of the password to use an input to the KDF

    :param salt:
        A cryptographic random byte string

    :param iterations:
        The numbers of iterations to use when deriving the key

    :param key_length:
        The length of the desired key in bytes

    :return:
        The derived key as a byte string
    """

    if not isinstance(password, byte_cls):
        raise ValueError('password must be a byte string, not %s' % (password.__class__.__name__))

    if not isinstance(salt, byte_cls):
        raise ValueError('salt must be a byte string, not %s' % (salt.__class__.__name__))

    if not isinstance(iterations, int_types):
        raise ValueError('iterations must be an integer, not %s' % (iterations.__class__.__name__))

    if iterations < 1:
        raise ValueError('iterations must be greater than 0 - is %s' % repr(iterations))

    if not isinstance(key_length, int_types):
        raise ValueError('key_length must be an integer, not %s' % (key_length.__class__.__name__))

    if key_length < 1:
        raise ValueError('key_length must be greater than 0 - is %s' % repr(key_length))

    if hash_algorithm not in {'md2', 'md5', 'sha1'}:
        raise ValueError('hash_algorithm must be one of "md2", "md5", "sha1", not %s' % repr(hash_algorithm))

    if key_length > 16 and hash_algorithm in {'md2', 'md5'}:
        raise ValueError('key_length can not be longer than 16 for %s - is %s' % (hash_algorithm, repr(key_length)))

    if key_length > 20 and hash_algorithm == 'sha1':
        raise ValueError('key_length can not be longer than 20 for sha1 - is %s' % repr(key_length))

    algo = getattr(hashlib, hash_algorithm)
    output = algo(password + salt).digest()
    for _ in range(2, iterations + 1):
        output = algo(output).digest()

    return output[:key_length]
