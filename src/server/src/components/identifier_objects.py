# Identifier Objects for Object Resource Service

import json, re
from flask import Response
import requests
from neo4j.v1 import GraphDatabase

from app.components.helper_functions import *
from app.components.neo_helpers import *
from app.components.cel import put_task, delete_task


from Crypto.Cipher import AES
from Crypto import Random
from os import urandom

# set up a global encryption object
key = urandom(16)
iv = Random.new().read(AES.block_size)
cipher = AES.new(key, AES.MODE_CFB, iv)


#authentication for objects
#EZID_USER = os.environ.get('EZID_USER')
#EZID_PASSWORD = os.environ.get('EZID_PASSWORD')
EZID_USER = 'apitest'
EZID_PASSWORD = 'apitest'

DATACITE_USER = os.environ.get('DATACITE_USER')
DATACITE_PASSWORD = os.environ.get('DATACITE_USER')



#########################################################
#                 Core Metadata Objects                 #
#########################################################

class CoreMetadata():    
    def __init__(self, *args, **kwargs):
        '''Create Core metadata Object       

        If minting will have arguments data and options

        Else will just pass guid, and attempt to delete self from api
        '''

        # initilize a connection to the cache
        self.neo_driver = NeoConn()

        # for minting
        self.data = kwargs.get('data')
        self.options = kwargs.get('options')

        self.ttl = None
        if self.options is not None:
            if self.options.get('ttl') is not None: 
                self.ttl = float(self.options.pop('ttl'))


        # for deleting
        self.guid = kwargs.get('guid')


    def mint(self):
        neo_async = self.postNeo()
        api_async = self.postAPI()
        return neo_async, api_async


    def postAPI(self):
        ''' Interface for minting all new identifiers 

        TODO should return some information about the del_task

        '''

        # make sure all required keys are present
        # assert set(self.data.keys()).issuperset(self.required_keys) 

        data = self.data

        # determine endpoint 
        target = "".join([self.endpoint, data.get('@id',None) ]) 


        # remove the cloud location keys if they are in the payload
        if data.get('contentUrl') is not None:
            data.pop('contentUrl')

        # format payload
        payload = profileFormat(flatten(self.data))
        payload.update(self.options)            

        # add put commmand to task queue
        submission_task= put_task.delay(target=target,payload=payload, user=self.auth[0], password=self.auth[1])

        # if the time to live is set, delete in that amount of time
        if self.ttl is not None:
            del_task = delete_task.apply_async(
                    (target, self.auth[0], self.auth[1]),
                    countdown =self.ttl 
                    )

        return submission_task


    def deleteAPI(self):
        ''' Add delete to task queue and return the asnyc result
        '''
        target = "".join([self.endpoint, self.guid ]) 
        del_task = delete_task.delay(target, self.auth[0], self.auth[1])
        return del_task

    def deleteCache(self):
        ''' Use connection to neo to delete own guid
        '''

        return self.neo_driver.deleteCache(self.guid)

    def getDownloads(self):
        ''' Decrypt the cloud bucket locations
        '''
        with self.neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                aws = tx.run(
                        "MATCH (node)-[:AWSdownload]->(aws) WHERE node.guid=$guid "
                        "RETURN properties(aws) ",
                        guid = self.guid
                        )
                aws_data = aws.data()

                gpc = tx.run(
                        "MATCH (node)-[:GPCdownload]->(gpc) WHERE node.guid=$guid "
                        "RETURN properties(gpc) ",
                        guid = self.guid
                        )
                gpc_data = gpc.data()

        aws_dict, gpc_dict = None

        if len(aws_data)!=0:
            aws_dict = aws_data[0].get('properties(aws)')
            aws_dict['url'] = cipher.decrypt(aws_dict['url'])

        if len(gpc_data)!=0:
            gpc_dict = gpc_data[0].get('properties(gpc)')
            aws_dict['url'] = cipher.decrypt(aws_dict['url'])
            
        return  {'aws': aws_dict, 'gpc': gpc_dict }
       


class DataCatalog(CoreMetadata):
    required_keys = set(['@id', '@type', 'name','url'])
    endpoint = "https://ezid.cdlib.org/id/"
    auth = (EZID_USER, EZID_PASSWORD)

    def postNeo(self):
        ''' Post to Neo database
        '''

        with self.neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                node = tx.run(
                        "MERGE (d:dataCatalog {guid: $guid, name: $name, url: $url, type: 'DataCatalog'} ) "
                        "RETURN properties(d)" ,
                       guid=self.data.get('@id', None),
                       name=self.data.get('name', None),
                       url=self.data.get('url', None)
                      )
                node_data = node.data()
                return node_data[0].get('properties(d)', None)


class Ark(CoreMetadata):
    required_keys = set(['@id', 'identifier', 'url', 'dateCreated', 'name','author','includedInDataCatalog','contentUrl'])
    optional_keys = set(['@type', 'expires'])
    endpoint = "https://ezid.cdlib.org/id/"
    auth = (EZID_USER, EZID_PASSWORD)
    
    def postNeo(self):
        ''' Post to Neo database
        '''

        # check identifier list for checksum info
        checksum_dict = {}

        for ident in self.data.get('identifier'):
            if isinstance(ident, dict): 
                checksum_dict['name'] = ident.get('name')
                checksum_dict['value'] = ident.get('value')


        with self.neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                # create node with properties 
                node = tx.run("MATCH (parent:dataCatalog) WHERE parent.guid=$parent "
                       "MERGE (node:Ark {guid: $guid, name: $name, author: $author, dateCreated: $dateCreated, url: $url, type: 'Dataset'}) "
                       "MERGE (node)-[parentRel:includedIn]->(parent) "
                       "RETURN properties(node)",
                       parent=self.data.get('includedInDataCatalog'),
                       guid=self.data.get('@id', None), 
                       name=self.data.get('name', None),
                       dateCreated = self.data.get('dateCreated', None),
                       author = self.data.get('author',None).get('name',None),
                       url=self.data.get('url',None),
                      ) 


                # if aws content link exists, add a download node and an edge
                if self.data.get('contentUrl', {}).get('aws') is not None:

                    # encrypt the aws location
                    encrypted_aws_loc = cipher.encrypt(
                            self.data.get('contentUrl').get('aws')
                            )

                    tx.run(
                           "MATCH (node:Ark) WHERE node.guid = $guid "
                           "MERGE (aws:AWSdownload {url: $awsUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                           "MERGE (node)-[awsRel:download]->(aws) ",
                           guid=self.data.get('@id'), 
                           awsUrl = encrypted_aws_loc,
                           checksumMethod = checksum_dict['name'],
                           checksum = checksum_dict['value']
                           )

                # if gpc content link exists, add a download node and an edge
                if self.data.get('contentUrl', {}).get('gpc') is not None:

                    # encrypt the gpc location 
                    encrypted_gpc_loc = cipher.encrypt(
                            self.data.get('contentUrl').get('gpc') 
                            )

                    tx.run(
                           "MATCH (node:Ark) WHERE node.guid = $guid "
                           "MERGE (gpc:GPCdownload {url: $gpcUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                           "MERGE (node)-[gpcRel:download]->(gpc) ",
                            guid=self.data.get('@id', None), 
                            gpcUrl = self.data.get('contentUrl').get('gpc'),
                            checksumMethod = checksum_dict['name'],
                            checksum = checksum_dict['value']
                            )
                

                node_data = node.data()
                if node_data != []:
                    return node_data[0].get('properties(node)', None)
                else:
                    return None

                
class Doi(CoreMetadata): 
    required_keys = set(['@id', '@type', 'identifier', 
                        'url', 'includedInDataCatalog', 'name', 'author',
                        'datePublished'])
    optional_keys = set(['dateCreated', 'additionalType', 'description', 
                        'keywords', 'license', 'version', 'citation', 'isBasedOn',
                        'predecessorOf', 'successorOf', 'hasPart', 'isPartOf', 'funder',
                        'contentSize', 'fileFormat', 'contentUrl'])
    endpoint = "https://ez.test.datacite.org/id/"
    auth = (DATACITE_USER, DATACITE_PASSWORD)

    
    def postNeo(self):
        ''' Post Doi to Neo database
        ''' 
        # unpack checksum information from identifier 
        if len([el for el in self.data.get('identifier') if isinstance(el, dict)])>0:
            checksum_dict = [el for el in self.data.get('identifier') if isinstance(el, dict)][0]

        content = self.data.get("contentUrl")

        with neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:

                # create node with required properties
                node = tx.run(
                        "MATCH (parent:dataCatalog) WHERE parent.guid=$parent "
                       "CREATE (node:Doi {guid: $guid, name: $name, author: $author, dateCreated: $dateCreated, url: $url, type: 'Dataset'}) "
                       "CREATE (node)-[parentRel:includedIn]->(parent) "
                       "RETURN properties(node)",
                       parent=self.data.get('includedInDataCatalog'),
                       guid=self.data.get('@id'), 
                       name=self.data.get('name'),
                       dateCreated = self.data.get('dateCreated', None),
                       author = self.data.get('author',None).get('name',None),
                       url=self.data.get('url',None),
                      )
                

                if self.data.get("contentUrl",{}).get("aws") is not None:

                    # encrypt the aws location
                    encrypted_aws_loc = cipher.encrypt(
                            self.data.get('contentUrl').get('aws')
                            )

                    tx.run("MATCH (node:Doi) WHERE node.guid = $guid "
                           "CREATE (aws:AWSdownload {url: $awsUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                           "CREATE (node)-[awsRel:download]->(aws) ",
                           guid=self.data.get('@id', None), 
                           awsUrl = encrypted_aws_loc,
                           checksumMethod = checksum_dict.get('name'),
                           checksum = checksum_dict.get('value')
                           )

                if self.data.get("contentUrl", {}).get("gpc") is not None:


                    # encrypt the aws location
                    encrypted_gpc_loc = cipher.encrypt(
                            self.data.get('contentUrl').get('gpc')
                            )


                    tx.run("MATCH (node:Doi) WHERE node.guid = $guid "
                           "CREATE (gpc:GPCdownload {url: $gpcUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                           "CREATE (node)-[gpcRel:download]->(gpc) ",
                           guid=self.data.get('@id', None), 
                           gpcUrl = encrypted_gpc_loc,
                           checksumMethod = checksum_dict.get('name'),
                           checksum = checksum_dict.get('value')
                           )

        node_data = node.single()

        if node_data is None:
            return node_data
        else:
            return node_data.value()

    def getNeo(self):
        ''' Decrypt the AWS location
        '''
                 
class CompactId(CoreMetadata):
    ''' Not Yet Implemented
    '''
    endpoint = "http://identifiers.org/"
    
    def postNeo(self):
        ''' Post to Neo database
        '''
        neo_driver = NeoConn()
        
        with neo_driver.driver.session() as session:
            session.write_transaction(
                tx.run("CREATE (d:dataCatalog {guid: $guid, name: $name, url: $url} )",
                       guid=self.data['@id'], 
                       name=self.data['name'],
                       url=self.data['url']
                      )
            )
            
            

def importDC(target):
    response = requests.get(target)
    if response.status_code == 200:
        obj = DataCatalog(ingestAnvl(str(response.content.decode('utf-8')) ))
        obj.postNeo()
        return True
    else:
        return False

def processAnvl(anvl):
    ''' Single process to format json-ld from ANVL - simplifies Get Path
    '''
    return formatJson(recursiveUnpack(removeProfileFormat(anvl)))
    
