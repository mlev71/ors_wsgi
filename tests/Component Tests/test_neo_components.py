import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../components')))

import unittest
from neo_components import *
from neo4j.v1 import GraphDatabase

LOC = "bolt://:7687"
#LOC = "bolt://34.205.15.119:7687"
DRIVER = GraphDatabase.driver(LOC, auth = ("neo4j", "guidbroker"))

DATACATALOG = { "@context" : "http://schema.org", \
               "@id" : "ark:/99999/fk4GTExDC", \
               "@type": "DataCatalog", \
               "identifier": "ark:/99999/fk4GTExDC", \
               "name": "GTEx Portal"}  

DATASET = {"@context": "http://schema.org", \
           "@type": "Dataset", \
           "@id": "ark:/99999/fk4GTExDS", \
           "identifier": "ark:/99999/fk4GTExDS", \
           "includedInDataCatalog": "ark:/99999/fk4GTExDC", \
           "dateCreated": "01-29-2018"}



class BasicTests():
    def test_connected(self):
        with DRIVER.session() as session:
            with session.begin_transaction() as tx:
                result = tx.run("CREATE (n {name:'hello'}) "
                        "RETURN n ")
                self.assertDictEqual(result.single()[0].properties, {'name':'hello'})


    def test_insert(self):
        self.create()

        # assert that there is a minid created 
        with DRIVER.session() as session:
            with session.begin_transaction() as tx:
                count_result = tx.run(self.QueryCount)
        self.assertDictEqual(count_result.data()[0], {'count(n)': 1})

        
    def test_query(self):
        query_result = self.get()
        self.assertDictEqual(query_result.properties, self.StoredObj)


    def test_delete(self):
        self.delete()
        with DRIVER.session() as session:
            with session.begin_transaction() as tx:
                count_result = tx.run(self.QueryCount)
        self.assertDictEqual(count_result.data()[0], {'count(n)': 0})

class MinidTest(BasicTests, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.Obj = {"identifier": "ark:/99999/fk4r8776t", \
             "created": "2015-11-10 04:44:44.387671", \
             "creator": "0000-0003-2129-5269", \
             "checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f", \
             "checksumMethod": "sha1", \
             "status": "ACTIVE", \
             "locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"], \
             "titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"]}


        self.StoredObj = {"guid": "ark:/99999/fk4r8776t", \
             "created": "2015-11-10 04:44:44.387671", \
             "creator": "0000-0003-2129-5269", \
             "checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f", \
             "checksumMethod": "sha1", \
             "status": "ACTIVE", \
             "locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"], \
             "titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"]}


        self.create = lambda x: registerMinid(x.Obj, DRIVER)
        self.get = lambda x: getMinid(x.Obj, DRIVER)
        self.delete = lambda x: deleteMinid(x.Obj, DRIVER)

        self.QueryCount = " MATCH (n:minid) RETURN count(n) "

        with DRIVER.session() as session:
            with session.begin_transaction() as tx:
                tx.run(" MATCH (n:minid) "
                        "DETACH DELETE n ")
    
 
    @classmethod 
    def tearDownClass(self):
        '''
        Detach and Delete all nodes with the Minid Tag
        '''

        with DRIVER.session() as session:
            with session.begin_transaction() as tx:
                tx.run(" MATCH (n:minid) "
                        "DETACH DELETE n ")


class DataCatalogTest(BasicTests, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.Obj = { "@context" : "http://schema.org", \
                "@id" : "ark:/99999/fk4GTExDC", \
                "@type": "DataCatalog", \
                "identifier": "ark:/99999/fk4GTExDC", \
                "name": "GTEx Portal"}  

        self.StoredObj = { "guid" : "ark:/99999/fk4GTExDC", \
                "name": "GTEx Portal"}  

        self.create = lambda x: registerDataCatalog(x.Obj, DRIVER)
        self.get = lambda x: getDataCatalog(x.Obj, DRIVER)
        self.delete = lambda x: deleteDataCatalog(x.Obj, DRIVER)
        
        self.QueryCount = " MATCH (n:dataCatalog) RETURN count(n) "
        
    @classmethod
    def tearDownClass(self):
        pass

class DatasetTest(BasicTests, unittest.TestCase):
    @classmethod
    def setUpClass(self):

        # create DC in object
        registerDataCatalog(DATACATALOG, DRIVER)

        self.Obj = {"@context": "http://schema.org", \
                   "@type": "Dataset", \
                   "@id": "ark:/99999/fk4GTExDS", \
                   "identifier": "ark:/99999/fk4GTExDS", \
                   "includedInDataCatalog": "ark:/99999/fk4GTExDC", \
                   "dateCreated": "01-29-2018"}

        self.StoredObj = { "guid": "ark:/99999/fk4GTExDS", \
                   "dateCreated": "01-29-2018"}

        self.create = lambda x: registerDataset(x.Obj, DRIVER)
        self.get = lambda x: getDataset(x.Obj, DRIVER)
        self.delete = lambda x: deleteDataset(x.Obj, DRIVER)
 
        self.QueryCount = " MATCH (n:dataset) RETURN count(n) "

    @classmethod
    def tearDownClass(self):
        pass

    
    # need tests for relationships
    """def test_get_whole(self):
        with DRIVER.session() as session:
            with session.begin_transaction() as tx:
                query_result = tx.run("MATCH (p)-[:PROVIDER_OF]->(d:dataset) "
                                      "RETURN count(d) ")
        self.assertIsNotNone(query_result)
        self.assertGreater(query_result.data()[0]['count(d)'], 0)

    # can we get all attached nodes from a single query?
    def test_get_nodes(self):
        pass"""

class DataDownloadTest(BasicTests, unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with DRIVER.session() as sess:
            with sess.begin_transaction() as tx:
                tx.run("MATCH (n) DETACH DELETE n")


        registerDataCatalog(DATACATALOG, DRIVER)

        
        registerDataset(DATASET, DRIVER)

        self.Obj = {"@context": "http://schema.org", \
                        "@type": "DatasetDownload", \
                        "@id": "ark:/99999/fk4GTExDownload", \
                        "identifier": "ark:/99999/fk4GTExDownload", \
                        "includedInDataset": "ark:/99999/fk4GTExDS", \
                        "checksum": "madeup checksum1", \
                        "checksumMethod": "md5", \
                        "contentSize": "100 bytes", \
                        "fileFormat": ".bam", \
                        "contentUrl": "http://example.org"}    

        self.StoredObj = { "guid": "ark:/99999/fk4GTExDownload", \
                        "checksum": "madeup checksum1", \
                        "method": "md5", \
                        "contentSize": "100 bytes", \
                        "fileFormat": ".bam", \
                        "contentUrl": "http://example.org"}    

        self.create = lambda x: registerDataDownload(x.Obj, DRIVER)
        self.get = lambda x: getDataDownload(x.Obj, DRIVER)
        self.delete = lambda x: deleteDataDownload(x.Obj, DRIVER)
    
        self.QueryCount = " MATCH (n:download) RETURN count(n) "


    @classmethod
    def tearDownClass(self):
        pass

if __name__=="__main__":
    unittest.main()
