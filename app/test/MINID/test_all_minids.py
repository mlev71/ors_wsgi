
from unittest.mock import MagicMock, patch

from nose.tools import assert_equal, assert_true, assert_is_not_none, assert_is_instance
from parameterized import parameterized

from flask import Response, render_template, Flask

app = Flask('test', template_folder = 'app/templates')
from app.components.identifier_objects import Minid, OutOfPath400, Identifier404 

import logging

logging.basicConfig(filename='minid.log', filemode ='w', level=logging.INFO)


with open('app/test/minids.txt', 'r') as minid_file:
    bulk_minids = minid_file.read().splitlines()


@parameterized(bulk_minids[1:30])
def test_all_minids(identifier):
    ''' Test minids with error handling '''
    try:
        minid_obj = Minid(identifier)
        minid_obj.fetch()
        payload = minid_obj.to_json_ld()



        assert_is_not_none(minid_obj)
        assert_is_not_none(payload)
        assert_is_instance(payload, dict)

        logging.getLogger('minid').info({
            'identifier': identifier, 
            'json_ld': payload
            })

    except (Identifier404) as err:
        # test json response
        err_json = err.json_response()
        err_html = err.html_response()

        assert_is_not_none(err_json)
        assert_is_instance(err_json, Response)
        assert_equal(err_json.status, '404 NOT FOUND')


        # dumped json should be bytes
        assert_is_not_none(err_json.response[0])

        # test html
        assert_is_not_none(err_html)

        logging.getLogger('minid').error({ 
            'identifier': identifier,
            'error': err_json.status, 
            'message': err_json.response[0].decode('utf-8'),
            'html': err_html
            })
    
    except(OutOfPath400) as err:
        # test json response
        err_json = err.json_response()
        err_html = err.html_response()

        assert_is_not_none(err_json)
        assert_is_instance(err_json, Response)
        assert_equal(err_json.status, '400 BAD REQUEST')


        # dumped json should be bytes
        assert_is_instance(err_json.response, list)
        assert_true(err_json.response[0] != b'')

        logging.getLogger('minid').error({ 
            'identifier': identifier,
            'error': err_json.status, 
            'message': err_json.response[0].decode('utf-8'),
            'html': err_html
            })

        # test html
        assert_is_not_none(err_html)

