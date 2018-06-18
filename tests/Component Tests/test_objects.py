import unittest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from components.objects import *

class BasicTests():
    '''
    Tests for all of the objects, see if data is being processed correctly
    from both sides, and ends up equivlent
    '''
    def test_objects_exist(self):
        self.assertIsNotNone(self.ANVL)
        self.assertIsNotNone(self.JSON)

    def test_read_json(self):
        self.assertIsNotNone(self.JSON.JSONdict)
        self.assertDictEqual(self.JSON.JSONdict, self.JSONDICT)

    def test_read_anvl(self):
        self.assertIsNotNone(self.ANVL.ANVLdict)
        self.assertDictEqual(self.ANVL.ANVLdict, self.ANVLDICT)

    def test_json_to_anvl(self):
        self.JSON.ANVLdict = None
        self.assertIsNone(self.JSON.ANVLdict)

        self.JSON.JSONtoANVL()
        self.assertIsNotNone(self.JSON.ANVLdict)
        self.assertDictEqual(self.JSON.ANVLdict, self.ANVLDICT)

    def test_anvl_to_json(self):
        self.ANVL.JSONdict = None
        self.assertIsNone(self.ANVL.JSONdict)

        self.ANVL.ANVLtoJSON()
        self.assertIsNotNone(self.ANVL.JSONdict)
        self.assertDictEqual(self.ANVL.JSONdict, self.JSONDICT)

    def test_objects_anvl_eq(self):
        self.JSON.JSONtoANVL()
        self.assertDictEqual(self.ANVL.ANVLdict, self.JSON.ANVLdict)

    def test_objects_json_eq(self):
        self.ANVL.ANVLtoJSON()
        self.assertEqual(self.ANVL.JSONdict, self.JSONDICT)

    def test_return_anvl(self):
        jsonANVL = self.JSON.returnANVL()
        anvlANVL = self.ANVL.returnANVL() 
        self.assertTrue(isinstance(jsonANVL, bytes))
        self.assertTrue(isinstance(anvlANVL, bytes))

    def test_return_json(self):
        jsonJSON = self.JSON.returnJSON()
        anvlJSON = self.ANVL.returnJSON() 
        self.assertTrue(isinstance(jsonJSON, str))
        self.assertTrue(isinstance(anvlJSON, str))

        # No Longer true because json convert will add EZID or PROXY url b
        #self.assertEqual(json.loads(jsonJSON), json.loads(self.JSONraw))
        #self.assertEqual(json.loads(anvlJSON), json.loads(self.JSONraw))
        #Just check equality of converted json

class FactoryTest():
    '''
    Tests the Factory Function
        Does it create objects
        Does it create proper objects
        Does it create the important attributes
    '''

    def test_created(self):
        self.assertIsNotNone(self.PayloadJSON)
        self.assertIsNotNone(self.PayloadJSON.JSONdict)
        self.assertIsNotNone(self.PayloadANVL)
        self.assertIsNotNone(self.PayloadANVL.ANVLdict)

    def test_appropriate_subclass(self):
        self.assertIsInstance(self.PayloadJSON, type(self.JSON))
        self.assertIsInstance(self.PayloadANVL, type(self.ANVL))
        self.assertIsInstance(self.PayloadANVL, type(self.PayloadJSON))

    def test_native_dicts_equal(self):
        self.assertDictEqual(self.PayloadANVL.ANVLdict, self.ANVL.ANVLdict)
        self.assertDictEqual(self.PayloadJSON.JSONdict, self.JSON.JSONdict)

    def test_translated_dicts_equal(self):
        self.PayloadANVL.ANVLtoJSON()
        self.PayloadJSON.JSONtoANVL()

        self.ANVL.ANVLtoJSON()
        self.JSON.JSONtoANVL()

        self.assertDictEqual(self.PayloadANVL.JSONdict, self.ANVL.JSONdict)
        self.assertDictEqual(self.PayloadJSON.ANVLdict, self.JSON.ANVLdict)

        self.assertDictEqual(self.PayloadANVL.ANVLdict, self.PayloadJSON.ANVLdict)
        self.assertDictEqual(self.PayloadANVL.JSONdict, self.PayloadJSON.JSONdict)

    def test_output_payload(self):
        self.PayloadANVL.ANVLtoJSON()
        self.PayloadJSON.JSONtoANVL()

        self.ANVL.ANVLtoJSON()
        self.JSON.JSONtoANVL()

        self.assertDictEqual(json.loads(self.PayloadANVL.returnJSON()), 
                json.loads(self.PayloadJSON.returnJSON()) )
        # not really appropriate, the order of the keys in the plaintext dont matter
            # if it passes above test, and dicts are equal -> probobly fine
        #self.assertEqual(self.PayloadANVL.returnANVL(), self.PayloadJSON.returnANVL())

    def test_url_on_convert(self):
        self.PayloadANVL.URL = None
        self.PayloadJSON.URL = None
        self.PayloadANVL.JSONdict = None
        self.PayloadJSON.ANVLdict = None

        self.PayloadANVL.ANVLtoJSON()
        self.PayloadJSON.JSONtoANVL()

        self.assertIsNotNone(self.PayloadJSON.URL)
        self.assertIsNone(self.PayloadANVL.URL)
        

class MinidTest(unittest.TestCase, BasicTests, FactoryTest):
    def setUp(self):
        self.maxDiff = None

        # correctly mapped json payload
        self.JSONDICT = { "identifier": "ark:/99999/fk4r8059v", \
                "created": "2015-11-10 04:44:44.387671", \
                "creator": "0000-0003-2129-5269", \
                "checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f", \
                "checksumMethod":"sha1", \
                "status": "ACTIVE", \
                "locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"], \
                "titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"] \
                }

        self.ANVLDICT = {'_target': "https://ezid.cdlib.org/id/ark:/99999/fk4r8059v", \
                '_profile': 'minid', \
                '_status': 'reserved', \
                'minid.created': '2015-11-10 04:44:44.387671', \
                'minid.creator': "0000-0003-2129-5269", \
                'minid.checksum': "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f", \
                'minid.checksumMethod': "sha1", \
                'minid.status': "ACTIVE", \
                'minid.locations': "http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf", \
                'minid.titles': "minid: A BD2K Minimal Viable Identifier Pilot v0.1" \
                }

        self.JSONraw = '{"identifier": "ark:/99999/fk4r8059v","created": "2015-11-10 04:44:44.387671","creator": "0000-0003-2129-5269","checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f","checksumMethod":"sha1","status": "ACTIVE","locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"],"titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"]}'

        self.ANVLraw = b'_target: https://ezid.cdlib.org/id/ark:/99999/fk4r8059v\n_profile: minid\n_status: reserved\nminid.created: 2015-11-10 04:44:44.387671\nminid.creator: 0000-0003-2129-5269\nminid.checksum: cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f\nminid.checksumMethod: sha1\nminid.status: ACTIVE\nminid.locations: http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf\nminid.titles: minid: A BD2K Minimal Viable Identifier Pilot v0.1'

        self.JSON = Minid(ResponseText = self.JSONraw, Type = "JSON")
        self.ANVL = Minid(ResponseText = self.ANVLraw, Type = "ANVL")

        self.PayloadJSON = PayloadFactory(ResponseText = self.JSONraw, Type = "JSON")
        self.PayloadANVL = PayloadFactory(ResponseText = self.ANVLraw, Type = "ANVL")

    def tearDown(self):
        pass

class DataCatalogTest(unittest.TestCase, BasicTests, FactoryTest):
    def setUp(self):
        self.maxDiff = None

        self.JSONraw  = '{"@context" : "http://schema.org", "@id" : "ark:/99999/fk4Gtex","identifier": "https://www.gtexportal.org/home/","name": "GTEx Portal", "description": "tissues and expression"}' 

        self.JSONDICT = {"@context": "http://schema.org","@id" : "ark:/99999/fk4Gtex","identifier": "https://www.gtexportal.org/home/","name": "GTEx Portal", "description": "tissues and expression"}
 
        self.ANVLraw = "_status: reserved\n_profile: NIHdc\n_target: https://ezid.cdlib.org/id/ark:/99999/fk4Gtex\nNIHdc.identifier: https://www.gtexportal.org/home/\nNIHdc.name: GTEx Portal\nNIHdc.description: tissues and expression" 

        self.ANVLDICT = { "_status": "reserved", "_profile": "NIHdc","_target" : "https://ezid.cdlib.org/id/ark:/99999/fk4Gtex","NIHdc.identifier": "https://www.gtexportal.org/home/","NIHdc.name": "GTEx Portal","NIHdc.description": "tissues and expression"}

        self.JSON = DataCatalog(ResponseText = self.JSONraw, Type = "JSON")
        self.ANVL = DataCatalog(ResponseText = self.ANVLraw, Type = "ANVL")

        self.PayloadJSON = PayloadFactory(ResponseText = self.JSONraw, Type = "JSON")
        self.PayloadANVL = PayloadFactory(ResponseText = self.ANVLraw, Type = "ANVL")

    def tearDown(self):
        pass


class DatasetTest(unittest.TestCase, BasicTests, FactoryTest):
    def setUp(self):
        
        self.maxDiff = None

        self.JSONraw  = '{"@context" : "http://schema.org", "@id" : "ark:/99999/fk4Dataset1","identifier": "https://www.gtexportal.org/home/","includedInDataCatalog": "ark:/99999/fk4GTEx", "dateCreated": "1-01-18"}' 

        self.JSONDICT = {"@context": "http://schema.org","@id" : "ark:/99999/fk4Dataset1","identifier": "https://www.gtexportal.org/home/","includedInDataCatalog": "ark:/99999/fk4GTEx", "dateCreated": "1-01-18"}
 
        self.ANVLraw = "_status: reserved\n_profile: NIHdc\n_target: https://ezid.cdlib.org/id/ark:/99999/fk4Dataset1\nNIHdc.identifier: https://www.gtexportal.org/home/\nNIHdc.includedInDataCatalog: ark:/99999/fk4GTEx\nNIHdc.dateCreated: 1-01-18" 

        self.ANVLDICT = { "_status": "reserved", "_profile": "NIHdc","_target" : "https://ezid.cdlib.org/id/ark:/99999/fk4Dataset1","NIHdc.identifier": "https://www.gtexportal.org/home/","NIHdc.includedInDataCatalog": "ark:/99999/fk4GTEx","NIHdc.dateCreated": "1-01-18"}

        self.JSON = Dataset(ResponseText = self.JSONraw, Type = "JSON")
        self.ANVL = Dataset(ResponseText = self.ANVLraw, Type = "ANVL")

        self.PayloadJSON = PayloadFactory(ResponseText = self.JSONraw, Type = "JSON")
        self.PayloadANVL = PayloadFactory(ResponseText = self.ANVLraw, Type = "ANVL")

    def tearDown(self):
        pass

class DataDownloadTest(unittest.TestCase, BasicTests, FactoryTest):
    def setUp(self): 

        self.maxDiff = None

        self.JSONraw  = '{"@context" : "http://schema.org", "@id" : "ark:/99999/fk4Download1","identifier": "https://ezid.cdlib.org/id/ark:/99999/fk4Download1","version": "ark:/99999/fk4GTEx", "contentSize": "1-01-18", "fileFormat":".bam", "contentUrl": "http:example.org/", "includedInDataset": "ark:/99999/fk4Dataset1"}' 
        self.JSONDICT = {"@context": "http://schema.org","@id" : "ark:/99999/fk4Download1","identifier": "https://ezid.cdlib.org/id/ark:/99999/fk4Download1","version": "ark:/99999/fk4GTEx", "contentSize": "1-01-18", "fileFormat":".bam", "contentUrl": "http:example.org/","includedInDataset": "ark:/99999/fk4Dataset1"} 
        self.ANVLraw = "_status: reserved\n_profile: NIHdc\n_target: https://ezid.cdlib.org/id/ark:/99999/fk4Download1\nNIHdc.identifier: https://ezid.cdlib.org/id/ark:/99999/fk4Download1\nNIHdc.version: ark:/99999/fk4GTEx\nNIHdc.contentSize: 1-01-18\nNIHdc.fileFormat: .bam\nNIHdc.contentUrl: http:example.org/\nNIHdc.includedInDataset: ark:/99999/fk4Dataset1" 
        self.ANVLDICT = { "_status": "reserved", "_profile": "NIHdc","_target" : "https://ezid.cdlib.org/id/ark:/99999/fk4Download1","NIHdc.identifier": "https://ezid.cdlib.org/id/ark:/99999/fk4Download1","NIHdc.version": "ark:/99999/fk4GTEx","NIHdc.contentSize": "1-01-18","NIHdc.fileFormat":".bam", "NIHdc.contentUrl": "http:example.org/", "NIHdc.includedInDataset": "ark:/99999/fk4Dataset1"}

        self.JSON = DataDownload(ResponseText = self.JSONraw, Type = "JSON")
        self.ANVL = DataDownload(ResponseText = self.ANVLraw, Type = "ANVL")

        self.PayloadJSON = PayloadFactory(ResponseText = self.JSONraw, Type = "JSON")
        self.PayloadANVL = PayloadFactory(ResponseText = self.ANVLraw, Type = "ANVL")

    def tearDown(self):
        pass

    def test_noparent_anvl(self):

        BadJSON  = '{"@context" : "http://schema.org", "@id" : "ark:/99999/fk4Download1","identifier": "https://ezid.cdlib.org/id/ark:/99999/fk4Download1","version": "ark:/99999/fk4GTEx", "contentSize": "1-01-18", "fileFormat":".bam", "contentUrl": "http:example.org/", "includedInDataset": "ark:/99999/NOTREAL"}' 

        self.assertFalse(ValidateParent("".join([EZID, 'ark:/99999/NOTREAL'])) )
        ShouldFail = PayloadFactory(ResponseText = BadJSON, Type= "JSON")
        self.assertIsInstance(ShouldFail, Response)

    def test_noparent_json(self): 
        
        BadANVL = "_status: reserved\n_profile: NIHdc\n_target: https://ezid.cdlib.org/id/ark:/99999/fk4Download1\nNIHdc.identifier: https://ezid.cdlib.org/id/ark:/99999/fk4Download1\nNIHdc.version: ark:/99999/fk4GTEx\nNIHdc.contentSize: 1-01-18\nNIHdc.fileFormat: .bam\nNIHdc.contentUrl: http:example.org/\nNIHdc.includedInDataset: ark:/99999/NOTREAL" 

        self.assertFalse(ValidateParent("".join([EZID, 'ark:/99999/NOTREAL']) ))
        ShouldFail = PayloadFactory(ResponseText = BadANVL, Type= "ANVL")
        self.assertIsInstance(ShouldFail, Response)

if __name__=="__main__":
    EZID = "https://ezid.cdlib.org/id/"

    arkurl = "".join([EZID, "ark:/99999/fk4GTEx"])
    check = requests.get(url=arkurl)
    if check.status_code == 200:
        pass
    else:
        response = requests.put(url = arkurl, 
                data = "_status: reserved\n_profile: NIHdc\n_target: https://ezid.cdlib.org/id/ark:/99999/fk4GTEx\nNIHdc.identifier: https://www.gtexportal.org/home/\nNIHdc.name: GTEx Portal\nNIHdc.description: tissues and expression",
                auth = requests.auth.HTTPBasicAuth("apitest","apitest"))
        assert response.status_code == 201

    arkurl = "".join([EZID, "ark:/99999/fk4Dataset1"])
    check = requests.get(url=arkurl)
    if check.status_code == 200:
        pass
    else:
        response = requests.put(url = arkurl, 
                data = "_status: reserved\n_profile: NIHdc\nNIHdc.identifier: https://www.gtexportal.org/home/\nNIHdc.includedInDataCatalog: ark:/99999/fk4GTEx\nNIHdc.dateCreated: 1-01-18" ,
                auth = requests.auth.HTTPBasicAuth("apitest","apitest"))
        assert response.status_code == 201

    unittest.main() 

    arkurl = "".join([EZID, "ark:/99999/fk4Dataset1"])
    response = requests.delete( url = arkurl, auth = requests.auth.HTTPBasicAuth("apitest","apitest"))
    assert response.status_code == 200


    arkurl = "".join([EZID, "ark:/99999/fk4Gtex"])
    response = requests.delete( url = arkurl, auth = requests.auth.HTTPBasicAuth("apitest","apitest"))
    assert response.status_code == 200
