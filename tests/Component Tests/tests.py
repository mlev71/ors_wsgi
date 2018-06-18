import unittest
import base64
import os
import sys
import flask
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

Auth = {'Authorization': 'Basic '+ base64.b64encode(b'apitest:apitest').decode('utf-8')}

AuthJSON = {'Authorization': 'Basic '+ base64.b64encode(b'apitest:apitest').decode('utf-8'), 'Content-Type':'application/json'}

AuthHTML = {'Authorization': 'Basic '+ base64.b64encode(b'apitest:apitest').decode('utf-8'), 'Content-Type':'text/html'}

class TestSubmission():

    # executes after every test
    def setUp(self):
        #app.config['TESTING'] = True
        #app.config['WTF_CSRF_ENABLED'] = False
        #app.config['DEBUG'] = True
        self.app = app.test_client()
        self.app.testing = True

#        exists =  self.app.get('/id/ark:/99999/fk4r8776t')
#        if exists.status_code == 404:
#            putAttempt = self.TestClient.put(self.putURL, headers=AuthJSON, data= self.JSON)
 #           if putAttempt.status_code != 201:
 #               print(putAttempt.data)

    # executes after every sucsessful test
    def tearDown(self):
        pass
 #       exists =  self.TestClient.get(self.getURL)
 #       if exists.status_code == 200:
 #           delAttempt = self.TestClient.delete(self.getURL, headers=AuthJSON)
 #           if delAttempt.status_code != 200:
 #               print(delAttempt.status_code)
 #               print(delAttempt.data)


    def test_get_json(self):
        response =  self.app.get(self.getURL)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.data), json.loads(self.JSON) )

    #def test_get_html(self):
    #    pass

class MinidTest(TestSubmission, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.JSON = '{"identifier": "ark:/99999/fk4r8776t","created": "2015-11-10 04:44:44.387671","creator": "0000-0003-2129-5269","checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f","checksumMethod":"sha1","status": "ACTIVE","locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"],"titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"]}'
        self.putURL = '/id/mint'
        self.getURL = '/id/ark:/99999/fk4r8776t'


    @classmethod
    def tearDownClass(self):
        pass




if __name__ == "__main__":
    unittest.main(warnings='ignore')
