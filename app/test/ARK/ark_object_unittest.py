import unittest
import requests
from jsonschema import ValidationError, validate
from flask import Response
from neomodel import config

config.DATABASE_URL = 'bolt://neo4j:'+ 'localtest' +'@'+ 'localhost' +':7687'


from app.components.identifier_objects import Ark
from app.components.jsonschema import ark_schema
from app.components.models.auth import UserNode


'''
class FetchArk():
    @classmethod
    def setUpClass(self):
        self.ark_obj = Ark(guid=self.guid)
        self.ark_obj.fetch()
        self.json_ld, self.profile = self.ark_obj.to_json_ld()

    def test_fetch(self):
        self.assertIsNotNone(self.ark_obj.anvl)
        self.assertTrue(isinstance(self.ark_obj.anvl, dict))

    def test_conversion(self):
        # type checking
        self.assertIsNotNone(self.json_ld)
        self.assertTrue(isinstance(self.json_ld, dict))

        # check if profile is expected
        self.assertTrue(self.profile in ['erc', 'dc', 'datacite', 'NIHdc'])

    def test_validate(self):
        try:
            validate(instance=self.json_ld, schema=ark_schema)
        except ValidationError as err:
            print(err)
            self.assertTrue(False)

class FetchDemo(FetchArk, unittest.TestCase):
    guid = 'ark:/13030/d3sodiumtest'
'''

class ArkCrud():
    @classmethod
    def setUpClass(self):
        # validate payload
        try:
            validate(instance=self.data, schema=ark_schema)
        except ValidationError as err:
            print(err)
            self.assertTrue(False)

        test_user = UserNode.nodes.get_or_none(email='mal8ch@virginia.edu')
        if test_user is None:
            self.assertTrue(False)

        self.ark_obj = Ark(data=self.data)
        self.response = self.ark_obj.post_api(test_user)

    def test_put(self):
        response = self.response
        status_code = self.response.status_code
        response_message = json.loads(
            self.response.response[0].decode('utf-8')
            )

        # type checking
        self.assertTrue(isinstance(response, Response))
        self.assertTrue(isinstance(response_message, dict))
        self.assertTrue(isinstance(status_code, int))

        # check if post was successfull
        self.assertTrue(response.status_code==200 or self.response.status_code==201)
        self.identifier = response_message.get('@id')


    def test_neomodel(self):
        pass


    def test_fetch(self):
        pass

    @classmethod
    def tearDownClass(self):
        ark_obj = Ark(guid=self.identifier)
        delete_response = ark_obj.delete_api()

        assert delete_response.status_code == 200


class MinidGuidless(ArkCrud, unittest.TestCase):
    data = {
        "checksum": "cd1c9c120df5460ae556c083a5b8ff89",
        "checksumMethod": "md5",
        "dateCreated": "7/13/18",
        "contentUrl": ["https://example.org/"],
        "name": "Significant eQTLs of rs1361754",
        "author": "Max Levinson"
        }

'''
class MinidGuid(CrudTest, unittest.TestCase):
    data = {
        "@id": "ark://"
        "@context": "https://schema.org",
        "@type": 'Dataset',
        "checksum": "cd1c9c120df5460ae556c083a5b8ff89",
        "checksumMethod": "md5",
        "dateCreated": "7/13/18",
        "contentUrl": ["https://example.org/"],
        "name": "Significant eQTLs of rs1361754",
        "author": "Max Levinson"
        }
'''


class ArkGuid(ArkCrud, unittest.TestCase):
    data = {

    }
