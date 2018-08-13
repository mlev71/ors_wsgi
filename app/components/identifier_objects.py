import requests
import base64
import json
import re
import os
import jinja2

from flask import Response, render_template

import datetime
from dateutil import parser


jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('app','templates')
    )

from app.components.cel import delete_task
from app.components.ezid_anvl import *
from app.components.mds_xml import *



EZID = 'https://ezid.cdlib.org/id/'
EZID_USER = os.environ.get('EZID_USER')
EZID_PASSWORD = os.environ.get('EZID_PASSWORD')

DATACITE_USER = os.environ.get('DATACITE_USER')
DATACITE_PASSWORD = os.environ.get('DATACITE_PASSWORD')
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
    required_keys = set(['name','author', 'dateCreated']) 
    optional_keys = set(['@type', 'expires','includedInDataCatalog', 'contentUrl'])
    endpoint = "https://ezid.cdlib.org/id/"
    auth = (EZID_USER, EZID_PASSWORD)
    useless_keys = ['success',  '_ownergroup', '_target', '_profile',
            '_status', '_export', '_updated', '_owner', '_created', 'context', 'id']


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
                profile='doi'
            else: 
                doi_metadata = DoiANVL(anvl, self.guid)
                json_ld = doi_metadata.to_json_ld()


        elif profile == 'NIHdc':
            anvl = { key.replace('NIHdc.', ''): value for key,value in anvl.items() }
            anvl['@id'] = 'https://n2t.net/' + self.guid
            anvl['identifier'] = 'https://n2t.net/' + self.guid
            anvl['@context'] = 'https://schema.org'

            json_ld = unroll(anvl) 

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
 
        ezid_delete = requests.delete(
                auth = requests.auth.HTTPBasicAuth(self.auth[0], self.auth[1]),
                url="https://ezid.cdlib.org/id/"+self.guid,
                )


        if ezid_delete.status_code == 200: 
            return Response(
                    status = 200,
                    response = json.dumps({
                        '@id': self.guid,
                        'message': 'Successfully Deleted Identifier',
                        'code': 200,
                        'ezid_response': { 
                            'status': ezid_delete.status_code,
                            'message' :ezid_delete.content.decode('utf-8')
                            }
                        }),
                    mimetype='application/json')

        if ezid_delete.status_code == 401:
            return Response(
                    status = 401,
                    response = json.dumps({
                        '@id': self.guid,
                        'message': 'Unauthorized to Delete Identifier',
                        'code': 401,
                        'ezid_response': { 
                            'status': ezid_delete.status_code,
                            'message' :ezid_delete.content.decode('utf-8')
                            }
                        }),
                    mimetype='application/json')

        else:
            return Response(
                    status = 400,
                    response = json.dumps({
                        '@id': self.guid,
                        'message': 'Failed to Delete Identifier',
                        'code': 400,
                        'ezid_response': { 
                            'status': ezid_delete.status_code,
                            'message' :ezid_delete.content.decode('utf-8')
                            }
                        }),
                    mimetype='application/json')

    
    def post_api(self, status='reserved'):
        ''' Interface for minting ARK identifiers '''
        payload = profileFormat(flatten(self.data))        
       
        if self.data.get('@id') is None and self.data.get('identifier') is None:
            target = self.endpoint.replace('id/', 'shoulder/ark:/13030/d3')
            landing_page = 'https://ors.datacite.org/${identifier}'
    
            payload.update({
                    "_target": landing_page,
                    "_status": status,
                    "_profile": "NIHdc"
                        })
    
            anvl_payload = outputAnvl(payload)
    
            mint_response = requests.post(
                    auth = requests.auth.HTTPBasicAuth(self.auth[0], self.auth[1]),
                    url=target,
                    headers = {'Content-Type': 'text/plain; charset=UTF-8'},
                    data = anvl_payload
                    )

        else:
            target = "".join([self.endpoint, self.data.get('@id')]) 

            landing_page = self.data.get('url', 'https://ors.datacite.org/{}'.format(self.data.get('@id')) )
    
            payload.update({
                    "_target": landing_page,
                    "_status": status,
                    "_profile": "NIHdc"
                        })

            anvl_payload = outputAnvl(payload)

            mint_response = requests.put(
                auth = requests.auth.HTTPBasicAuth(self.auth[0], self.auth[1]),
                url=target,
                headers = {'Content-Type': 'text/plain; charset=UTF-8'},
                data = anvl_payload
                )


        ezid_response = mint_response.content.decode('utf-8')
        ezid_status = mint_response.status_code
        ezid_identifier = ezid_response.replace('success: ', '').replace('error: ', '')

        identifier = self.data.get('@id', ezid_identifier)


        if ezid_status == 200 or ezid_status == 201:
        
            response_message = {
                "@id": identifier,  
                "message": "Successfully minted identifier",
                "code": 201,
                "ezid_response": {
                        "status": ezid_status, 
                        "message": ezid_response
                        },
                    }

            if self.data.get('expires') is not None and status!="public":

                try:
                    expiration = self.data.pop('expires')  
                    expiration_eta = parser.parse(expiration)
                except:
                    response_message.update({
                        "expiration": 
                            {
                                'status': 400, 
                                'message': 'Failed to parse date {}'.format(expiration)
                                }
                        })


                task = delete_task.apply_async( 
                        (target, self.auth[0], self.auth[1]),
                        eta = parser.parse(expiration)
                        )
                
                response_message.update({
                    "expiration": {
                        'status': 200, 
                        'message': 'Identifier will be deleted',
                        }
                    })

            return Response(
                    status=201,
                    response=json.dumps(response_message),
                    mimetype='application/json'
                    )


        if mint_response.status_code == 401:
            return Response(
                    status = 401,
                    response = json.dumps({
                        '@id': identifier,
                        'message': 'Failed To Mint Identifier' + 
                        'ORS is not authorized on the prefix for identifer {}'.format(identifier),
                        'ezid_response': {
                            'code': ezid_status,
                            'message': ezid_response
                            }
                        }),
                    mimetype='application/json'
                    )


        else: 
            if ezid_response == "error: bad request - identifier already exists":
                successfully_updated = []
                failed_updated = []
                for field, value in payload.items(): 
                    try:
                        update_response = requests.post(
                                auth = requests.auth.HTTPBasicAuth(self.auth[0], self.auth[1]),
                                url = target,
                                data = '{}: {}'.format(field, value)
                                )
                        assert update_response.status_code == 200
                        successfully_updated.append(field)

                    except AssertionError:
                        failed_updated.append(field)

                if len(failed_updated) == 0:
                    response_message = {
                                '@id': identifier,
                                'code': 200,
                                'message': 'Succsessfully Updated all Identifier metadata {}'.format(identifier),
                                'updated_keys': successfully_updated,
                                }


                else:
                    response_message = {
                                '@id': identifier,
                                'code': 207,
                                'message': 'Failed to update Identifier metadata {}'.format(identifier),
                                'updated_keys': successfully_updated,
                                'failed_update': failed_updated
                                }


                if self.data.get('expires') is not None and status!="public":
                    expiration = self.data.pop('expires')  
                    try:
                        expiration_datetime = parser.parse(expiration)
                        exp = datetime.datetime.now() - expiration_datetime

                        task = delete_task.apply_async(
                                (target, self.auth[0], self.auth[1]),
                                eta = expiration_datetime
                                )

                        response_message.update(
                                {"expiration": 
                                    {
                                    'status': 200, 
                                    'message': 'Identifier will be deleted in {} seconds'.format(exp.seconds),
                                }
                                    })
                        
                    except:
                        response_message.update(
                                {"expiration": 
                                    {
                                        'status': 400, 
                                        'message': 'Failed to parse date {}'.format(expiration)
                                        }
                                    })







                return Response(    
                    status = response_message.get('code'),
                    response = json.dumps(response_message),
                    mimetype = 'application/json'
                        )


            else: 
                return Response(
                        status = 400,
                        response = json.dumps({
                            '@id': identifier,
                            'message': 'Identifier Not Sucsessfully Minted',
                            'ezid': {
                                    'status': ezid_status,
                                    'message': ezid_response 
                                    }
                                })
                        )




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
                'status': 400,
                'message': 'Object missing required keys',
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
