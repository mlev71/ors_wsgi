# Identifier Objects for Object Resource Service
import json, re
from flask import Response
import requests
from neo4j.v1 import GraphDatabase

from components.helper_functions import *
from components.neo_helpers import *

class CoreMetadata():
    
    def __init__(self, data, options=None):
        ''' Core metadata Object       
        Read in Data
        Determine if any options are set
        Validate all necesary Keys are Present
        '''
        self.data = data
        self.options = options

        # make sure all required keys are present
        assert set(data.keys()).issuperset(self.required_keys)

 
    def postAPI(self, auth):
        """ Send a put request to the endpoint for the identifier
        """
        target = "".join([self.endpoint, self.data.get('@id',None) ])
        payload = profileFormat(recursiveFlatten(self.data))
        payload.update(self.options)            
        #return outputAnvl(self.data)
        response = requests.put(
                auth = auth,
                url=target,
                headers = {'Content-Type': 'text/plain; charset=UTF-8'},
                data = outputAnvl(payload)
            )

        return response
        
    def deleteAPI(self, auth):
        target = "".join([self.endpoint, self.data.get('@id',None) ])
        response = requests.delete(
            auth = auth,
            url=target
        )
        return response.content
        

class DataCatalog(CoreMetadata):
    required_keys = set(['@id', '@type', 'name','url'])
    endpoint = "https://ezid.cdlib.org/id/"

    def postNeo(self):
        ''' Post to Neo database
        '''
        neo_driver = NeoConn()

        with neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("MERGE (d:dataCatalog {guid: $guid, name: $name, url: $url, type: 'DataCatalog'} )",
                       guid=self.data.get('@id', None),
                       name=self.data.get('name', None),
                       url=self.data.get('url', None)
                      )


class Ark(CoreMetadata):
    required_keys = set(['@id', 'identifier', 'url', 'dateCreated', 'name','author','includedInDataCatalog','contentUrl'])
    optional_keys = set(['@type', 'expires'])
    endpoint = "https://ezid.cdlib.org/id/"

    
    def postNeo(self):
        ''' Post to Neo database
        '''
        neo_driver = NeoConn()
        
        
        # query for parent with guid
        #with neo_driver.driver.session() as session:
        #    with session.begin_transaction() as tx:
        #        node = tx.run("MATCH (node:dataCatalog) "
        #              "WHERE node.guid = $guid "
        #               "RETURN count(node)",
        #               guid = self.data.get('includedInDataCatalog'))
        #        count = node.single().data().get('count(node)')
        
        # if dataCatalogNot found attempt to import
        #if count>=1:
        #    target = self.endpoint + self.data.get('includedInDataCatalog')
        #    parent = importDC(target)
        #    if parent==False:
        #        raise InvalidParent(self.data.get('includedInDataCatalog'))
       
        # unpack checksum information from identifier 
        checksum_dict = [el for el in self.data.get('identifier') if isinstance(el, dict)][0]

        with neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                # create node with required properties
                # create downloads as 
                tx.run("MATCH (parent:dataCatalog) WHERE parent.guid=$parent "
                       "CREATE (node:Ark {guid: $guid, name: $name, author: $author, dateCreated: $dateCreated, url: $url, type: 'Dataset'}) "
                       "CREATE (node)-[parentRel:includedIn]->(parent) "
                       "CREATE (aws:AWSdownload {url: $awsUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                       "CREATE (node)-[awsRel:download]->(aws) "
                       "CREATE (gpc:GPCdownload {url: $gpcUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                       "CREATE (node)-[gpcRel:download]->(gpc) ",
                       parent=self.data.get('includedInDataCatalog'),
                       guid=self.data.get('@id', None), 
                       name=self.data.get('name', None),
                       dateCreated = self.data.get('dateCreated', None),
                       author = self.data.get('author',None).get('name',None),
                       url=self.data.get('url',None),
                       awsUrl = self.data.get('contentUrl').get('aws'),
                       gpcUrl = self.data.get('contentUrl').get('gpc'),
                       checksumMethod = checksum_dict['name'],
                       checksum = checksum_dict['value']
                      )
                
                
                
class Doi(CoreMetadata):
    required_keys = set(['@id', '@type', 'identifier', 
                        'url', 'includedInDataCatalog', 'name', 'author',
                        'datePublished', 'contentUrl'])
    optional_keys = set(['dateCreated', 'additionalType', 'description', 
                        'keywords', 'license', 'version', 'citation', 'isBasedOn',
                        'predecessorOf', 'successorOf', 'hasPart', 'isPartOf', 'funder',
                        'contentSize', 'fileFormat'])
    
    def postNeo(self):
        ''' Post Doi to Neo database
        '''
        neo_driver = NeoConn()
        
        
        # query for parent with guid
        with neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                node = tx.run("MATCH (node:dataCatalog) "
                      "WHERE node.guid = $guid "
                       "RETURN count(node)",
                       guid = self.data.get('includedInDataCatalog'))
                count = node.single().data().get('count(node)')
        
        # if dataCatalogNot found attempt to import
        if count>=1:
            parent = importDC(self.data.get('includedInDataCatalog'))
            if parent is None:
                raise InvalidParent(self.data.get('includedInDataCatalog'))


        # unpack checksum information from identifier 
        checksum_dict = [el for el in self.data.get('identifier') if isinstance(el, dict)].get(0)

        with neo_driver.driver.session() as session:
            with session.begin_transaction() as tx:
                # create node with required properties
                # create downloads as 
                tx.run("MATCH (parent:dataCatalog) WHERE parent.guid=$parent "
                       "CREATE (node:Ark {guid: $guid, name: $name, author: $author, dateCreated: $dateCreated, url: $url, type: 'Dataset'}) "
                       "CREATE (node)-[parentRel:includedIn]->(parent) "
                       "CREATE (aws:AWSdownload {url: $awsUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                       "CREATE (node)-[awsRel:download]->(aws) "
                       "CREATE (gpc:GPCdownload {url: $gpcUrl, checksum: $checksum, checksumMethod: $checksumMethod}) "
                       "CREATE (node)-[gpcRel:download]->(gpc) ",
                       parent=self.data.get('includedInDataCatalog'),
                       guid=self.data.get('@id', None), 
                       name=self.data.get('name', None),
                       dateCreated = self.data.get('dateCreated', None),
                       author = self.data.get('author',None).get('name',None),
                       url=self.data.get('url',None),
                       awsUrl = self.data.get('contentUrl').get('aws'),
                       gpcUrl = self.data.get('contentUrl').get('gpc'),
                       checksumMethod = checksum_dict.get('name'),
                       checksum = checksum_dict.get('value')
                      )
                
                 
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
    
