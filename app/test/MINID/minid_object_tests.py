from unittest.mock import MagicMock, patch

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance
from parameterized import parameterized

from flask import Response
from app.components.identifier_objects import Minid, OutOfPath400, Identifier404 


minid_examples = ['ark:/57799/b90t23', 'ark:/57799/b90w82']

ark_examples = ['ark:/234980/bweroj']



broken_examples = ['ark:/08234/sdf', 'ark:/woijegg/sdfgh', 'ark:/notaminid/myminid']
broken_inpath_examples =  ['ark:/57799/weoifjoweijoiwjegow']


all_examples = minid_examples+ark_examples+broken_examples



@parameterized(minid_examples)
def test_working_minid(identifier): 
    ''' Test minids that should not error with no error handling
    '''
    minid_obj = Minid(identifier)

    assert_is_not_none(minid_obj) 

    assert_is_not_none(minid_obj.ark)
    assert_equal(minid_obj.ark, identifier)

    minid_obj.fetch()
    assert_is_not_none(minid_obj.anvl)
    assert_is_instance(minid_obj.anvl, dict)    
 
    json_ld = minid_obj.to_json_ld()
    assert_is_not_none(json_ld)
    assert_is_instance(json_ld, dict)
        

@parameterized(broken_examples)
def test_out_of_path(identifier):
    ''' Test that out of path is handled correctly 
    '''
    try:
        minid_obj = Minid(identifier)

    except (OutOfPath400) as err:
        json_err = err.json_response()

        assert_is_not_none(json_err)
        assert_is_instance(json_err, Response)

        assert_is_not_none(json_err.response)


@parameterized(broken_examples)
def test_minid_not_returned(identifier):
    ''' Test if a 404 from ezid is handled
    '''
    try:
        minid_obj = Minid('ark:/57799/b90t23')
        minid_obj.ark = identifier
        minid_obj.fetch()

    except Identifier404 as err:
        json_response = err.json_response()
        assert_is_not_none(err.json_response())
        


