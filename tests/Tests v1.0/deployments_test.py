import argparse
import requests
import json
import unittest

from commonTestObjects import *

import boto3

AWS = False
######################################
# Grab the Public Ip of the WSGI Task#
######################################
if AWS==True:
    ecs = boto3.client('ecs')
    ec2 = boto3.resource('ec2')

    testCluster = 'arn:aws:ecs:us-east-1:280922329489:cluster/ORS_Test'
    # grab the tasks for the wsg_service 
    taskMetadata = ecs.list_tasks(
        cluster = testCluster,
        serviceName = 'wsgi_service'
    )

    # grab the descriptions for the appropraite task
    taskDesc = ecs.describe_tasks(
        cluster = testCluster,
        tasks = [taskMetadata['taskArns'][0]]
    )

    # grab the Network Interface attatched to the task
    networkInterfaceId = [element['value'] for element in taskDesc['tasks'][0]['attachments'][0]['details'] if element['name'] == "networkInterfaceId"]
    networkInterface = ec2.NetworkInterface(networkInterfaceId[0])

    # load all attributes and get the public ip
    networkInterface.load()
    pubIp = networkInterface.association_attribute['PublicIp']

else:
    pubIp = "ors.test.datacite.org"

assert pubIp is not None

# Format Address
ADDR = "http://"+pubIp

print(ADDR)

###################
# Build Test Suite#
###################

BasicAuth = requests.auth.HTTPBasicAuth('apitest', 'apitest')
JSONheaders = {'Accept': 'application/json'}
HTMLheaders = {'Accept': 'text/html'}

class BasicTests():
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_flask_app_running(self):
        response = requests.get(self.getURL)
        self.assertIsNotNone(response)
        self.assertNotIn(response.status_code, [404, 400, 500])
        self.assertNotEqual(response.content, b'error: bad request - no such identifier')

    def test_get_accept_json(self):
        response = requests.get(self.getURL, headers=JSONheaders)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.content)
        self.assertEqual(response.status_code, requests.codes.ok)
        #self.assertEqual(response.json(), self.JSON)
        self.assertEqual(response.headers['content-type'], 'application/ld+json; profile="http://schema.org"')

    def test_get_accept_html(self):
        response = requests.get(self.getURL, headers=HTMLheaders)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.content)
        self.assertEqual(response.status_code, requests.codes.ok)
        self.assertEqual(response.headers['content-type'], 'text/html; charset=utf-8')

    def test_get_accept_blank(self):
        response = requests.get(self.getURL)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.content)
        self.assertEqual(response.status_code, requests.codes.ok)
        self.assertEqual(response.headers['content-type'], 'text/html; charset=utf-8')


class MinidTest(unittest.TestCase, BasicTests):
    @classmethod
    def setUpClass(self):
        self.JSON = minidJSON
        self.putURL = ADDR + '/mint'
        self.getURL = ADDR + '/ark:/99999/fk4r8776t'
        exists = requests.get(self.getURL)
        if exists.status_code != 200:
            response = requests.put(self.putURL, auth=BasicAuth, data=json.dumps(self.JSON))         
            assert response.status_code == 201
            
    @classmethod
    def tearDownClass(self):
        response = requests.delete(self.getURL, auth=BasicAuth)
        assert response.status_code == 200


class DataCatalogTest(unittest.TestCase, BasicTests):    

    @classmethod
    def setUpClass(self):
        self.JSON = dcJSON      
        self.putURL = ADDR + '/mint'
        self.getURL = ADDR + '/ark:/99999/fk4DataCatalogTestDC'
        exists = requests.get(self.getURL)
        if exists.status_code == 404:
            response = requests.put(self.putURL, auth=BasicAuth, data=json.dumps(self.JSON))
            try:
                assert response.status_code == 201 
            except AssertionError:
                print(response.status_code)
                print(response.content)

    @classmethod
    def tearDownClass(self):
        response = requests.delete(self.getURL, auth=BasicAuth)
        assert response.status_code == 200 

class DatasetTest(unittest.TestCase, BasicTests):

    @classmethod
    def setUpClass(self):
        self.ParentJSON = { 
                "@context" : "http://schema.org", 
                "@id" : "ark:/99999/fk4DatasetTestDC", 
                "@type": "DataCatalog", 
                "identifier": "ark:/99999/fk4DatasetTestDC", 
                "name": "GTEx Portal"}
        self.JSON = {
                "@context": "http://schema.org",
                "@type": "Dataset",
                "@id": "ark:/99999/fk4DatasetTestDS", 
                "identifier": "ark:/99999/fk4DatasetTestDS", 
                "includedInDataCatalog": "ark:/99999/fk4DatasetTestDC", 
                "dateCreated": "01-29-2018"}

        self.putURL = ADDR + '/mint'
        self.getURL = ADDR + '/ark:/99999/fk4DatasetTestDS'
        self.getParent = ADDR + '/ark:/99999/fk4DatasetTestDC'
        exists = requests.get(self.getURL)
        parent_exists = requests.get(self.getParent)

        if parent_exists.status_code == 404:
            parent = requests.put(self.putURL, auth=BasicAuth, data=json.dumps(self.ParentJSON))
            try:
                assert parent.status_code == 201
            except AssertionError:
                print(parent.status_code)
                print(parent.content)

        if exists.status_code == 404:
            response = requests.put(self.putURL, auth=BasicAuth, data=json.dumps(self.JSON))
            try:
                assert response.status_code == 201
            except AssertionError:
                print(response.status_code)
                print(response.content)

    @classmethod
    def tearDownClass(self):
        response = requests.delete(self.getURL, auth=BasicAuth)
        parent_response = requests.delete(self.getParent, auth=BasicAuth)
        assert response.status_code == 200
        assert parent_response.status_code == 200
    

class DataDownloadTest(unittest.TestCase, BasicTests):
    @classmethod
    def setUpClass(self):
        self.GrandparentJSON = {
                "@context" : "http://schema.org", 
                "@id" : "ark:/99999/fk4DownloadTestDC", 
                "@type": "DataCatalog", 
                "identifier": "https://www.gtexportal.org/home/", 
                "name": "GTEx Portal"}  
        self.ParentJSON = {
                "@context": "http://schema.org",
                "@type": "Dataset",
                "@id": "ark:/99999/fk4DownloadTestDS", 
                "identifier": "ark:/99999/fk4DownloadTestDS", 
                "includedInDataCatalog": "ark:/99999/fk4DownloadTestDC", 
                "dateCreated": "01-29-2018"}
        self.JSON = {
                "@context": "http://schema.org",
                "@type": "DatasetDownload" , 
                "@id": "ark:/99999/fk4DownloadTestDD",
                "identifier": "ark:/99999/fk4DownloadTestDD", 
                "version": "1.0.0", 
                "includedInDataset": "ark:/99999/fk4DownloadTestDS", 
                "contentSize": "100 bytes", 
                "fileFormat": ".bam",
                "contentUrl": "http://example.org",
                "checksum": "madeupchecksum123",
                "checksumMethod": "md5",
                "filename": "hello.txt"
                }
 
        self.putURL = ADDR + '/mint' 
        self.getURL = ADDR + '/ark:/99999/fk4DownloadTestDD'
        self.getParent = ADDR + '/ark:/99999/fk4DownloadTestDS' 
        self.getGrandparent = ADDR + '/ark:/99999/fk4DownloadTestDC' 

        grandparent_exists = requests.get(self.getGrandparent)
        if grandparent_exists.status_code == 404:
            put_grandparent = requests.put(self.putURL, auth=BasicAuth, data = json.dumps(self.GrandparentJSON))
            try:
                assert put_grandparent.status_code == 201
            except AssertionError:
                print(put_grandparent.status_code)
                print(put_grandparent.content)
                raise AssertionError

        parent_exists = requests.get(self.getParent)
        if parent_exists.status_code == 404:
            put_parent = requests.put(self.putURL, auth=BasicAuth, data = json.dumps(self.ParentJSON))
            try:
                assert put_parent.status_code == 201
            except AssertionError:
                print(put_parent.status_code)
                print(put_parent.content)
                raise AssertionError

        exists = requests.get(self.getURL) 
        if exists.status_code == 404:
            put_dd = requests.put(self.putURL, auth=BasicAuth, data = json.dumps(self.JSON))
            try:
                assert put_dd.status_code == 201
            except AssertionError:
                print(put_dd.status_code)
                print(put_dd.content)
                raise AssertionError

    @classmethod
    def tearDownClass(self):
        remove_dd = requests.delete(self.getURL, auth=BasicAuth)
        remove_parent = requests.delete(self.getParent, auth=BasicAuth)
        remove_grandparent = requests.delete(self.getGrandparent, auth=BasicAuth)
        assert remove_dd.status_code == 200 
        assert remove_parent.status_code == 200 
        assert remove_grandparent.status_code == 200 




if __name__=="__main__":
    unittest.main()
