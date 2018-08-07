# Identifier Objects for Object Resource Service

import base64
import json, re
from flask import Response, render_template
import requests
from neo4j.v1 import GraphDatabase

import jinja2

jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('app','templates')
    )

from app.components.ezid_anvl import *
from app.components.neo_helpers import *
from app.components.cel import put_task, delete_task
from app.components.mds_xml import *


from Crypto.Cipher import AES
from Crypto import Random
from os import urandom


key = b'\xc5\x89\x01)\xecC\xe2\x00L\xd3\xc2\x82+\xec\xb1r'
iv = b'\x1a\xe6\xd6\x95\xf0e\x10eb$\x81\xad\x8c\xd7;\xf1'
cipher = AES.new(key, AES.MODE_CFB, iv)

EZID = 'https://ezid.cdlib.org/id/'
EZID_USER = os.environ.get('EZID_USER')
EZID_PASSWORD = os.environ.get('EZID_PASSWORD')

DATACITE_USER = os.environ.get('DATACITE_USER', 'cdl_dcppc')
DATACITE_PASSWORD = os.environ.get('DATACITE_PASSWORD', 'ezid2018')
DATACITE_URL = os.environ.get('DATACITE_URL', 'https://mds.test.datacite.org')


# file extension to mimetype conversions
mimetype = {
    ".tar": "application/x-tar", 
    ".zip": "application/zip",
    ".sh": "application/x-sh",
    ".rft": "application/rtf",
    ".rar": "application/x-rar-compressed",
    ".jar": "application/java-archive",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".bin": "application/octet-stream",
    ".bz": "application/x-bzip",
    ".bz2": "application/x-bzip2",
    ".gtar": "application/x-gtar",
    ".tgz": "application/x-gtar",
}


#########################################################
#                 Core Metadata Objects                 #
#########################################################


class CoreMetadata(object):    
    def __init__(self, *args, **kwargs):
        '''Create Core metadata Object       

        If minting will have arguments data and options

        Else will just pass guid, and attempt to delete self from api
        '''

        
        self.guid = kwargs.get('guid')

        self.data = kwargs.get('data')
        self.status = kwargs.get('status')

        if self.status is not None:
            assert self.status == 'reserved' or self.status == 'public'


        if self.data is not None:
            if not set(self.required_keys).issubset(set(self.data.keys())):
                raise MissingKeys(self.data.keys(), self.required_keys)
 


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
    optional_keys = set(['@type', 'expires','includedInDataCatalog', 'contentUrl'])
    endpoint = "https://ezid.cdlib.org/id/"
    auth = (EZID_USER, EZID_PASSWORD)
    useless_keys = ['success',  '_ownergroup', '_target', #'_profile',
            '_status', '_export', '_updated', '_owner', '_created']


    def fetch(self):
        endpoint = "https://ezid.cdlib.org/id/"+self.guid
        api_response = requests.get(url = endpoint)

        try: 
            assert api_response.status_code == 200
            assert api_response.content is not None

        except:
           raise Identifier404(self.guid, api_response, EZID+self.guid)    

        self.anvl = ingestAnvl(api_response.content.decode('utf-8'))

    def to_json_ld(self):
        ''' Parse ANVL and return in JSON-LD
        '''
        anvl = self.anvl

        profile = anvl.get('_profile')

        if profile == 'erc':
            json_ld = {
                    '@id': 'http://n2t.net/'+self.guid,
                    'identifier': 'http://n2t.net/'+self.guid,
                    '@context': 'https://schema.org',
                    'url': anvl.get('_target')
                    }


            if anvl.get('erc') is None:
                # Trim off 'erc.' prefix from all keys
                erc_dict = { key.replace('erc.',''): val for key,val in anvl.items() if 'erc.' in key}

            else:
                # Split compressed element into a dictionary
                erc_lines = anvl.get('erc').split('%0A')
                erc_dict ={key: val for key,val in (line.split(': ',1) for line in erc_lines)}


            # Label ERC Metadata in JSON-LD with IRIs 
            erc_iri = {'who':'h11', 'what':'h12', 'when':'h13', 'where':'h14', 'how': 'h14'}
            for key, value in erc_dict.items():
                if key in erc_iri.keys():
                    json_ld.update({ key : {
                                '@type': 'http://n2t.info/ark:/99152/'+ erc_iri.get(key),
                                '@value': value
                                }
                            })


        elif profile == 'dc':
            json_ld = { re.sub('dc.', '', key): value for key, value in anvl.items() if 'dc.' in key}
            json_ld['@type'] = anvl.get('dc.type')
            json_ld['@context'] = 'http://purl.org/dc/elements/1.1/' 
            json_ld['@id'] = 'https://n2t.net/'+self.guid 
            json_ld['identifier'] = 'https://n2t.net/'+self.guid 
            profile = 'dc'

        elif profile == 'datacite':
            if anvl.get('datacite') is not None:
                xml = anvl.get('datacite').replace('<?xml version="1.0"?>%0A', '')
                doi_metadata = DoiXML(xml)
                json_ld = doi_metadata.parse()
                profile = 'NIHdc'
            else: 
                doi_metadata = DoiANVL(anvl, self.guid)
                json_ld = doi_metadata.to_json_ld()
                profile = 'datacite'


        elif profile == 'NIHdc':
            anvl = { key.replace('NIHdc.', ''): value for key,value in anvl.items() }
            anvl['@id'] = 'https://n2t.net/' + self.guid
            anvl['identifier'] = 'https://n2t.net/' + self.guid
            anvl['@context'] = 'https://schema.org'

            json_ld = unroll(anvl) 
            json_ld.pop('id')
            json_ld.pop('context')

        else:
            # If Profile is Unknown raise an Exception
            raise UnknownProfile400(self, anvl.get('_profile'))

        # remove useless keys from 

        json_ld['url'] = anvl.get('_target')
        for key in self.useless_keys:
            if key in json_ld.keys():
                json_ld.pop(key)
        

        return json_ld, profile


    def delete_api(self):
        ''' Delete Ark from EZID 
        '''
        delete_ark= requests.delete(
                auth = requests.auth.HTTPBasicAuth(auth),
                url="https://ezid.cdlib.org/id/"+self.guid
                )
        return delete_ark
    

    def post_api(self, status):
        ''' Interface for minting all new identifiers 
        '''
        # determine endpoint 
        target = "".join([self.endpoint, self.data.get('@id',None) ]) 
 
        # format payload
        payload = profileFormat(flatten(self.data))        

        payload.update({
                "_target": self.data.get('url'),
                "_status": status,
                "_profile": "NIHdc"
                    })
        
        
        # add put commmand to task queue
        assert self.auth[0] is not None
        assert self.auth[1] is not None
        submission_task= put_task.delay(target=target,payload=payload, user=self.auth[0], password=self.auth[1])

        # make sure the response message is succusfull
        submission_task.get()
        api_response = submission_task.result
        response_message = {
            "ezid": {"status": api_response.get('status_code'), "messsage": api_response.get('content')},
            }


        # check if payload has expiration specification
        if self.data.get('expires') is not None:
            # TODO format from datetime to seconds
            expiration_date = self.data.pop('expires')  
            del_task = delete_task.apply_async(
                    (target, self.auth[0], self.auth[1]),
                    countdown = float(self.options.get('ttl') )
                    )
            response_message.update({"expires_in": expiration})

        return response_message 



class Doi(CoreMetadata): 
    required_keys = set(['@id', '@type', 'identifier', 'url', 'name', 'author','datePublished'])
    optional_keys = set(['includedInDataCatalog', 'dateCreated', 'additionalType', 'description', 
                        'keywords', 'license', 'version', 'citation', 'isBasedOn',
                        'predecessorOf', 'successorOf', 'hasPart', 'isPartOf', 'funder',
                        'contentSize', 'fileFormat', 'contentUrl'])
    endpoint = DATACITE_URL 
    auth = (DATACITE_USER, DATACITE_PASSWORD)

    def post_api(self):
        ''' Submit XML payload to Datacite
        '''
        basic_auth = requests.auth.HTTPBasicAuth(self.auth)
        response = {}

        # register metadata
        create_metadata = requests.post(
                url = DATACITE_URL + "/metadata/" ,
                auth = basic_auth,
                data = xml_payload,
                headers = {'Content-Type':'application/xml;charset=UTF-8'},
                )

        response.update({
            'metadataRegistration': create_metadata.content.decode('utf-8')
            })

        assert create_metadata.status_code == 201

        # reserve doi
        reserve_doi = requests.put(
                url = DATACITE_URL + '/doi/' +doi,
                auth = basic_auth,
                data = "doi="+self.data.get('@id')+"\nurl="+self.data.get('url'),
                )

        assert create_metadata.status_code == 201

        response.update({
            'doiReservation': reserve_doi.content.decode('utf-8')
            })

        xml_payload = convertDoiToXml(self.data)

        # register media
        contentUrl = self.data.get('contentUrl')
        fileFormat = self.data.get('fileFormat')
        if contentUrl is not None and fileFormat is not None:
            if isintance(contentUrl, list):
                media = '\n'.join([fileFormat+'='+media_elem for media_elem in contentUrl])
                media_responses = []
                for media_elem in contentUrl:
                    media = fileFormat+'='+media_elem
                    media_request = requests.post(
                            url = DATACITE_URL + '/media/' + doi,
                            auth = basic_auth,
                            data = media,
                            headers = {'Content-Type': 'text/plain'}
                            )

                    media_responses.append(media_request.content.decode('utf-8'))

                response.update({ 'mediaRegistration': media_responses })

            elif isinstance(contentUrl, str):
                media = fileFormat+'='+contentUrl
                single_media_request = requests.post(
                        url = DATACITE_URL + '/media/' + doi,
                        auth = basic_auth,
                        data = media,
                        headers = {'Content-Type': 'text/plain'}
                        )


                response.update({
                            'mediaRegistration': single_media_request.content.decode('utf-8')
                            })

        return response

 
    def fetch(self):
        works_response = requests.get(url = 'https://api.datacite.org/works/'+self.guid)

        try:
            assert works_response.status_code == 200
        except AssertionError:
            raise NotADataciteDOI(self.guid)
            
        try:
            payload = works_response.content.decode('utf-8')
            works = json.loads(payload).get('data', {}).get('attributes', {})
            assert works is not None
            assert works.get('xml') is not None
        except AssertionError:
            raise IncompletePayload(self.guid, payload)
        
        self.response = DoiResponse(works)
        try:

            json_ld = self.response.parse()
        except:
            raise InvalidPayload(self.guid, works)
        
        return json_ld


    def delete_api(self): 
        doi = self.guid

        delete_response = requests.delete(
                url = self.endpoint+'/metadata/'+doi,
                auth = requests.auth.HTTPBasicAuth(self.auth[0], self.auth[1])
                )        
        
        response_dict = {
                'status_code': delete_response.status_code,
                'content': delete_response.content.decode('utf-8')
                }
        return response_dict



class Minid(object):
    def __init__(self, guid):
        self.ark = re.sub('minid:', 'ark:/57799/', guid)
        self.anvl = None
        self.json_ld = None
         
        try:
            assert 'ark:/57799/' in self.ark
        except AssertionError:
            raise OutOfPath400(self)

    def fetch(self): 
        ezid_response = requests.get(
            url = EZID+self.ark
        )

        try:
            assert ezid_response.status_code != 404
            assert ezid_response.status_code == 200
            assert ezid_response.content is not None
        except AssertionError:
            raise Identifier404(self.ark, ezid_response, EZID+self.ark)    


        anvl = ezid_response.content.decode('utf-8') 
        self.anvl = ingestAnvl(anvl)

        minid_response = requests.get(
            url = self.anvl.get('_target'), 
            headers = {'Accept': 'application/json'}
        )
        
        try:
            assert minid_response.status_code == 200
            # assert the content is not an error message
        except AssertionError:
            raise Identifier404(self.ark, minid_response, self.anvl.get('_target'))

        self.minid_json = json.loads(minid_response.content.decode('utf-8'))


         
    def to_json_ld(self): 
        minid_json = self.minid_json
        json_ld = {}
    
        # @id and identifier
        full_id ='https://n2t.net/'+minid_json.get('identifier')
        json_ld['@id'] = 'https://n2t.net/'+minid_json.get('identifier')
        json_ld['identifier'] = [full_id]
    
        # name
        titles = minid_json.get("titles")
        if titles is not None:
            if isinstance(titles,list) and len(titles)>0:
                json_ld['name'] = titles[0].get('title')
            if isinstance(titles, str):
                json_ld['name'] = titles
    
        # add checksum 
        json_ld['identifier'].append({'@type': 'PropertyValue', 
             'name': minid_json.get('checksum_function'), 
             'value': minid_json.get('checksum')})
    
        # url
        json_ld['url'] = self.anvl.get('_target')
    
        # contentUrl
        json_ld['contentUrl'] = [link.get('link') for link in minid_json.get('locations')]
    
        # date created
        json_ld['dateCreated'] = minid_json.get('created')
    
        # author
        json_ld['author'] = minid_json.get('creator')
    
        self.json_ld = json_ld
     
        return json_ld

   
#####################
# Custom Exceptions #
#####################
class NotADataciteDOI(Exception):
    def __init__(self, doi):
        self.doi
        
    def output(self):
        message = {
            'doi': 'http://doi.org/'+ self.doi,
            'error': 'http://doi.org/'+self.doi+' is not a Datacite Doi'
        }
        return Response(status=404, response= json.dumps(message))
    
class IncompletePayload(Exception):
    def __init__(self, doi, payload):
        self.doi = doi
        self.payload = payload
    
    def output(self):
        message = {
            'doi': 'http://doi.org/'+self.doi,
            'error': 'Payload is missing required metadata',
            'payload': payload
        }
        
        return Response(status=400, response= json.dumps(message))
    
    
class InvalidPayload(Exception):
    def __init__(self, doi, payload):
        self.payload = payload
        self.doi = doi
        
    def output(self):
        message = {
            'doi': 'http://doi.org'+self.doi,
            'error': 'Payload could not be parsed, invalid xml',
            'payload': self.payload
        }
        return Response(status=400, response= json.dumps(message))

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
        


class Identifier404(BaseException):
    """Identifier was not returned"""
    def __init__(self, guid, api_response, target):
        self.response_message = {
                '@id': guid,
                'url': target,
                'apiResponse': api_response.content.decode('utf-8'),
                'errorMessage': 'Identifier metadata was not found',
                'errorCode': 404
                }


    def json_response(self):
       return  Response(
               status = 404,
               response = json.dumps(self.response_message),
               mimetype = 'application/json' 
               )

    def html_response(self):
        template = jinja_env.get_template('IdentifierError.html')
        return template.render(data = self.response_message)


class OutOfPath400(BaseException):
    """Minid is not within the official Minid Path 
    """
    def __init__(self, minid):
        self.response_message = {
                '@id': minid.ark,
                'url': EZID+minid.ark,
                'error': 'Minid Identifier does not have requied prefix ark:/57799/ or the alias minid:',
                'errorCode': 400
                }
        

    def json_response(self):
       return  Response(
               status = 400,
               response = json.dumps(self.response_message),
               mimetype = 'application/json' 
               )

    def html_response(self):
        template = jinja_env.get_template('IdentifierError.html')
        return template.render(data = self.response_message)
 
class UnknownProfile400(BaseException):
    """Ark is not within the official Minid Path 
    """
    def __init__(self, Ark, profile):
        self.response_message = {
                '@id': Ark.guid,
                'url': EZID+Ark.guid,
                'errorMessage': 'Ark has profile: {}, which cannot currently be mapped to json-ld'.format(profile),
                'errorCode': 400,
                'anvl': Ark.anvl
                }
        

    def json_response(self):
       return  Response(
               status = 400,
               response = json.dumps(self.response_message),
               mimetype = 'application/json' 
               )

    def html_response(self):
        template = jinja_env.get_template('IdentifierError.html')
        return template.render(data = self.response_message)

