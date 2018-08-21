import requests, json
from unittest.mock import MagicMock, patch
from nose.tools import assert_equal, assert_true

from app.components.ezid_anvl import *
from app.components.identifier_objects import Minid 

from parameterized import parameterized

minid_examples = ['ark:/57799/b90t23', 'ark:/57799/b90w82']

@parameterized(minid_examples)
def init_minid(identifier):
    try:
        minid_obj = Minid(identifier)
        assert minid_obj is not None
    except OutOfPath as e:
        assert e.repsonse is not None



