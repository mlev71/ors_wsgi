# Identifier Objects for Object Resource Service

import json, re
from flask import Response
import requests
from neo4j.v1 import GraphDatabase

from app.components.helper_functions import *
from app.components.neo_helpers import *
from app.components.cel import put_task, delete_task
from app.components.mds_xml import *


from Crypto.Cipher import AES
from Crypto import Random
from os import urandom


key = b'\xc5\x89\x01)\xecC\xe2\x00L\xd3\xc2\x82+\xec\xb1r'
iv = b'\x1a\xe6\xd6\x95\xf0e\x10eb$\x81\xad\x8c\xd7;\xf1'
cipher = AES.new(key, AES.MODE_CFB, iv)


#authentication for objects
#EZID_USER = os.environ.get('EZID_USER')
#EZID_PASSWORD = os.environ.get('EZID_PASSWORD')
EZID_USER = 'apitest'
EZID_PASSWORD = 'apitest'

#DATACITE_USER = os.environ.get('DATACITE_USER')
#DATACITE_PASSWORD = os.environ.get('DATACITE_USER')
DATACITE_USER = 'DATACITE.DCPPC'
DATACITE_PASSWORD = 'Player&Chemo+segment'


#########################################################
#                 Core Metadata Objects                 #
#########################################################

class CoreMetadata():    
    def __init__(self, *args, **kwargs):
        '''Create Core metadata Object       

        If minting will have arguments data and options

        Else will just pass guid, and attempt to delete self from api
        '''


        # for minting
        self.data = kwargs.get('data')
        self.options = kwargs.get('options')

        
        if self.data is not None:
            # if keys are missing raise exception
            if not set(self.required_keys).issubset(set(self.data.keys())):
                raise MissingKeys(self.data.keys(), self.required_keys)

        # for deleting
        self.guid = kwargs.get('guid')


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
       

class Ark(CoreMetadata):
    required_keys = set(['@id', 'identifier', 'url', 'name','author', 'dateCreated'])
    # removed 'includedInDataCatalog', dateCreated, 'contentUrl'
    optional_keys = set(['@type', 'expires'])
    endpoint = "https://ezid.cdlib.org/id/"
    auth = (EZID_USER, EZID_PASSWORD)

    def getAPI(self):
        endpoint = "https://ezid.cdlib.org/id/"+self.guid
        api_response = requests.get(url = endpoint)

        if api_response.status_code == 404:
            return Response(
                    status = 404, 
                    response = json.dumps({"guid": GUID, "message": "No record of Identifier"})
                    )

        # processing anvl
        self.data = convertArkToJson(api_response.content.decode('utf-8'))
        return self.data


    def deleteAPI(self):
        endpoint = "https://ezid.cdlib.org/id/"+self.guid 
        delete_ark = delete_task.delay(endpoint, self.auth[0], self.auth[1])
        return delete_ark
    
    def importAPI(self):
        pass

    def postAPI(self):
        ''' Interface for minting all new identifiers 
        '''

        # determine endpoint 
        target = "".join([self.endpoint, self.data.get('@id',None) ]) 


        # remove the cloud location keys if they are in the payload
        #if data.get('contentUrl') is not None:
            # encrypt cloud locations
            #data.pop('contentUrl')

        # format payload
        payload = profileFormat(flatten(self.data))
        payload.update(self.options)            


        # add put commmand to task queue
        submission_task= put_task.delay(target=target,payload=payload, user=self.auth[0], password=self.auth[1])

        # if the time to live is set, delete in that amount of time
        if self.options.get('ttl') is not None:
            del_task = delete_task.apply_async(
                    (target, self.auth[0], self.auth[1]),
                    countdown = float(self.options.get('ttl') )
                    )

        return submission_task


    def postNeo(self):
        ''' Post to Neo database
        '''

        response = {}


        ark_guid = self.data.get('@id')
        ark_type = self.data.get('@type')
        author = self.data.get('author')
        funder = self.data.get('funder')

        if ark_type == "Dataset":
            content = self.data.get('contentUrl', 'None')        
            file_format = self.data.get('fileFormat', 'None') 

        # post the Ark as a node
        ark_task = postNeoArk.delay(self.data)
        ark_task.get()

        response.update({
            'ark': ark_task.result
            })

        # add authors
        if isinstance(author,dict):
            author_task = postNeoAuthor.delay(author, ark_guid)
            author_task.get()
            response.update({
                'author': author_task.result
                })

        if isinstance(author,list):
            author_task = [postNeoAuthor.delay(auth, ark_guid) for auth in author]
            [task.get() for task in author_task]
            response.update({
                'author': [task.result for task in author_task]
                })


        # add funders
        if isinstance(funder,dict):
            funder_task = postNeoFunder.delay(funder, ark_guid)
            funder_task.get()

            response.update({
                'author': funer_task.result
                })


        if isinstance(funder, list):
            funder_task =[postNeoFunder.delay(funder_elem,ark_guid) for funder_elem in funder] 

            response.update({
                'funder': [task.result for task in funder_task]
                })
       
        # if its a dataset add all downloads and checksums
        if ark_type == "Dataset":
            checksum_list = list(filter(lambda x: isinstance(x,dict), self.data.get('identifier'))) 

            aws_location = list(filter(lambda x: re.match('aws', x), content))
            gpc_location = list(filter(lambda x: re.match('gpc', x), content))

            if len(aws_location) != 0:
                aws_download_task = postDownload.delay(aws_location[0], checksum_list, file_format, ark_guid, 'aws')
                aws_download_task.get()
                response.update({
                    'aws_location': aws_download_task.result
                    })
                

            if len( gpc_location) != 0:
                aws_download_task = postDownload.delay(aws_location[0], checksum_list, file_format, ark_guid, 'gpc')
                aws_download_task.get()
                response.update({
                    'gpc_location': gpc_download_task.result
                    })

        return response

    def getNeo(self):
        ''' Get all the data about the ark from neo4j
        '''
        pass
  
class Doi(CoreMetadata): 
    # included in data catalog changed to optional
    required_keys = set(['@id', '@type', 'identifier', 
                        'url', 'name', 'author',
                        'datePublished'])
    optional_keys = set(['includedInDataCatalog', 'dateCreated', 'additionalType', 'description', 
                        'keywords', 'license', 'version', 'citation', 'isBasedOn',
                        'predecessorOf', 'successorOf', 'hasPart', 'isPartOf', 'funder',
                        'contentSize', 'fileFormat', 'contentUrl'])
    endpoint = "https://mds.test.datacite.org/"
    auth = (DATACITE_USER, DATACITE_PASSWORD)

    def renderTemplate(self):
        
        # unpack self.data
        # required keys
        required_keys = {key: value for key,value in self.data.items() if key in required_keys}

        # optional keys 


    def getAPI(self):
        ''' Retrieve metadata from Datacite and convert into json-ld
        '''

        api_response = requests.get(
                url = self.endpoint+'metadata/'+self.guid,
                auth = requests.auth.HTTPBasicAuth(self.auth[0], self.auth[1])
                )

        if api_response.status_code == 404:
            return {"status":404, "message": "No record of Identifier"}


        self.data = convertDoiToJson(api_response.content.decode('utf-8'))

        return self.data
        

    def postAPI(self):
        ''' Format metadata into XML and issue commands to task queue to reserve in Datacite
        '''

        doi = self.data.get('@id')
        landing_page = self.options.get('_target')

        #convert data to xml
        xml_payload = convertDoiToXml(self.data)

    
        # register metadata in the task queue
        metadata_task = register_metadata.delay( 
                payload = xml_payload,
                user = self.auth[0],
                password = self.auth[1]
                )
                

        # reserve the doi
        doi_task = reserve_doi.delay(
                doi = doi,
                landing_page = landing_page,
                user = self.auth[0],
                password = self.auth[1]
                )


        metadata_task.get()
        doi_task.get()

        full_response = {
                'metadata_registration': metadata_task.result,
                'doi_reservation': doi_task.result
                }

        return full_response
 

    def importAPI(self):
        api_response = self.getAPI()
        self.data=api_response

        obj.postNeo()

        response_message = {"cache": {"imported": GUID} }

        return Response(
                status = 201,
                response = json.dumps(response_message),
                mimetype= 'application/json'
                )


    def deleteAPI(self): 
        doi = self.guid

        delete_response = requests.delete(
                url = self.endpoint+'metadata/'+doi,
                auth = self.auth
                )        
        response_dict = {
                'status_code': delete_response.status_code,
                'content': delete_response.content.decode('utf-8')
                }
        return response_dict


    def postNeo(self):
        ''' Post Doi to Neo database  
        ''' 
        
        doi_guid = self.data.get('@id')
        doi_type = self.data.get('@type')
        author = self.data.get('author')
        funder = self.data.get('funder')

        if doi_type == "Dataset":
            content = self.data.get('contentUrl')        
            file_format = self.data.get('fileFormat') 

        # post the Doi as a node
        doi_task = postNeoDoi.delay(self.data)
        assert doi_task.state != 'FAILURE'

        # add authors
        if isinstance(author,dict):
            author_task = postNeoAuthor.delay(author, doi_guid)
            assert author_task.state != 'FAILURE'

        if isinstance(author,list):
            author_task = [postNeoAuthor.delay(auth, doi_gid) for auth in author]
            assert author_task.state != 'FAILURE'


        # add funders
        if isinstance(funder,dict):
            funder_task = postNeoFunder.delay(funder, doi_guid)
            assert funder_task.state != 'FAILURE'

        if isinstance(funder, list):
            funder_task =[postNeoFunder.delay(funder_elem,doi_guid) for funder_elem in funder] 
            assert funder_task.state != 'FAILURE'


        # if its a dataset add all downloads and checksums
        if doi_type == "Dataset":
            checksum_list = list(filter(lambda x: isinstance(x,dict), self.data.get('identifier'))) 

            aws_location = list(filter(lambda x: re.match('aws', x), content))
            gpc_location = list(filter(lambda x: re.match('gpc', x), content))

            if len(aws_location) != 0:
                aws_download_task = postDownload.delay(aws_location[0], checksum_list, file_format, doi_guid, 'aws')
                aws_download_task.get()
                assert aws_download_task.state != 'FAILURE'
                

            if len( gpc_location) != 0:
                gpc_download_task = postDownload.delay(gpc_location[0], checksum_list, file_format, doi_guid, 'gpc')
                assert gpc_download_task.state != 'FAILURE'


    def getNeo(self):
        ''' Query the Neo Cache

        '''
        pass

 
   
#####################
# Custom Exceptions #
#####################

class MissingKeys(Exception):
    ''' Exception to raise when keys are missing
    '''

    def __init__(self, supplied_keys, required_keys): 
        missing_keys = list(set(required_keys).difference(set(supplied_keys)))
        self.message = {
                'error_message': 'Object missing required keys',
                'missing_keys': missing_keys
                }

    def output(self):
        return Response(
                status = 400,
                response = json.dumps(self.message),
                mimetype = 'application/json'
                )
            

def convertArkToJson(anvl):
    ''' Single process to format json-ld from ANVL - simplifies Get Path
    '''
    # turn anvl text into a dictionary
    anvl_dict = ingestAnvl(anvl)

    # remove all the NIHdc. prefixes from tags and 
    formatted = removeProfileFormat(anvl_dict)

    # recursivly unpack keys into object 
    unpacked = unroll(formatted)

    # format the json-ld keys and return
    return formatJson(unpacked) 
