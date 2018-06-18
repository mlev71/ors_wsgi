import sys, os
sys.path.insert(0, '../app/components')
from payload_handler import *
from commonTestObjects import *

import unittest
import json


NEO4J_ENABLED = False

# Test for Each object with a static object example


class PayloadTests():
    """ Testing Suite for Payload Handler 
    
    Every Object follows the same flow and maintained with the same structure
    """
    def test_json_digest(self):
        self.payloadObj = JSONfactory(self.JSON)
        self.assertIsNotNone(self.payloadObj)
        self.assertIsNotNone(self.payloadObj.JSONdict)
        self.assertIsInstance(self.payloadObj, self.ObjType)


    def test_anvl_conversion_equiv(self):
        """ Convert to ANVL and back and forth
        """
        self.payloadObj = JSONfactory(self.JSON)
        self.payloadObj.JSONtoANVL()
        self.assertIsNotNone(self.payloadObj.ANVLdict)


class MinidTest(unittest.TestCase, PayloadTests):
    @classmethod
    def setUpClass(self):
        self.JSON = json.dumps(minidJSON)        
        self.ObjType = Minid

class DCTest(unittest.TestCase, PayloadTests): 
    @classmethod
    def setUpClass(self):
        self.JSON = json.dumps(dcJSON)
        self.ObjType = DataCatalog

class DSTest(unittest.TestCase, PayloadTests):
    @classmethod
    def setUpClass(self):
        self.JSON = json.dumps(dsJSON)
        self.ObjType = Dataset

class DDTest(unittest.TestCase, PayloadTests):
    @classmethod
    def setUpClass(self):
        self.JSON = json.dumps(ddJSON)
        self.ObjType = DataDownload

if __name__=="__main__":
    unittest.main()
