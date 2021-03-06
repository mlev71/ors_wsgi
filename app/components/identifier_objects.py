import requests
import base64
import json
import re
import os
import string
import random
import jinja2
import uuid

from jsonschema import validate, ValidationError

from flask import Response, render_template

import datetime
from dateutil import parser


jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('app','templates')
    )

from app.components.cel import  *
from app.components.ezid_anvl import *
from app.components.mds_xml import *

from app.components.models import *

ORS_URL = os.environ.get('PROXY_URL', 'https://localhost')


EZID = 'https://ezid.cdlib.org/id/'
EZID_USER = os.environ.get('EZID_USER')
EZID_PASSWORD = os.environ.get('EZID_PASSWORD')

DATACITE_USER = os.environ.get('DATACITE_USER')
DATACITE_PASSWORD = os.environ.get('DATACITE_PASSWORD')
DATACITE_URL = os.environ.get('DATACITE_URL')
DOI_PREFIX = '10.25489'


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
class Ark(object):
    endpoint = "https://ezid.cdlib.org/id/"
    auth = requests.auth.HTTPBasicAuth(EZID_USER, EZID_PASSWORD)
    useless_keys = ['success',  '_ownergroup', '_target', '_profile',
            '_status', '_export', '_updated', '_owner', '_created', 'context', 'id']


    def __init__(self, *args, **kwargs):
        self.guid = kwargs.get('guid')
        self.data = kwargs.get('data')
        self.status = kwargs.get('status')


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
                auth = self.auth,
                url="https://ezid.cdlib.org/id/"+self.guid,
                )

        # submit delete task to celery
        delete_ark.apply_async(kwargs={'guid': self.guid})


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


    def post_api(self, user):
        ''' Interface for minting ARK identifiers '''
        payload = profileFormat(flatten(self.data))

        # if the identifier is unspecified
        if self.data.get('@id') is None and self.data.get('identifier') is None:
            target = self.endpoint.replace('id/', 'shoulder/ark:/13030/d3')
            landing_page = 'https://ors.datacite.org/${identifier}'

            payload.update({
                    "_target": landing_page,
                    "_status": self.status,
                    "_profile": "NIHdc"
                        })

            anvl_payload = outputAnvl(payload)

            mint_response = requests.post(
                    auth = self.auth,
                    url=target,
                    headers = {'Content-Type': 'text/plain; charset=UTF-8'},
                    data = anvl_payload
                    )


        else:
            target = "".join([self.endpoint, self.data.get('@id'), '?update_if_exists=yes'])

            landing_page = self.data.get('url', 'https://ors.datacite.org/{}'.format(self.data.get('@id')) )

            payload.update({
                    "_target": landing_page,
                    "_status": self.status,
                    "_profile": "NIHdc"
                        })

            anvl_payload = outputAnvl(payload)

            mint_response = requests.put(
                auth = self.auth,
                url=target,
                headers = {'Content-Type': 'text/plain; charset=UTF-8'},
                data = anvl_payload
                )


        ezid_response = mint_response.content.decode('utf-8')
        ezid_status = mint_response.status_code
        ezid_identifier = ezid_response.replace('success: ', '').replace('error: ', '')

        identifier = self.data.get('@id', ezid_identifier)

        # create neo representation with task queue
        put_ark.apply_async(kwargs={
            'UserEmail': user.email,
            'guid': identifier,
            'status': self.status,
            'schemaJson': self.data
            })


        if ezid_status == 200 or ezid_status == 201:

            response_message = {
                "@id": identifier,
                "message": "Successfully minted identifier",
                "status": 201,
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


                delete_task.apply_async(
                        (target, EZID_USER, EZID_PASSWORD),
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



class Doi(object):
    endpoint = DATACITE_URL
    auth = requests.auth.HTTPBasicAuth(DATACITE_USER, DATACITE_PASSWORD)

    def __init__(self, *args, **kwargs):
        self.guid = kwargs.get('guid')
        self.data = kwargs.get('data')
        self.status = kwargs.get('status')

    def post_api(self, user):
        ''' Post valid Schema.org to Datacite MDS API
        '''

        if self.data.get('@id') is not None:
            doi = self.data.get('@id').replace('doi:/','').replace('https://doi.org/', '')
        else:
            # must randomly assign doi when posting in JSON-LD
            doi = '10.25489/'+''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.data['@id'] = doi

        response = {
            '@id': 'doi:/'+doi,
            'datacite': {},
        }


        # convert to XML
        payload = DataciteXML(self.data).convert()

        # register metadata- MUST HAPPEN FIRST
        create_metadata = requests.put(
                url = DATACITE_URL + "/metadata/" + doi,
                auth = self.auth,
                data = payload.encode('utf-8'),
                headers = {'Content-Type': 'application/xml;charset=utf-8'},
                )

        if create_metadata.status_code != 201:
            return Response(
                    status = 500,
                    response = json.dumps({
                        '@id': 'doi:/'+doi,
                        'status': 500,
                        'message': 'Unable to submit metadata',
                        'datacite': {
                            'status': create_metadata.status_code,
                            'message': create_metadata.content.decode('utf-8')
                            }

                        })

                    )

        # store record of status in neo4j
        put_doi.apply_async(kwargs = {
            'UserEmail': user.email,
            'guid': doi,
            'status': self.status,
            'schemaJson': self.data
        })


        response.get('datacite').update({
            'metadataRegistration': create_metadata.content.decode('utf-8')
            })

        if self.status!='draft':
            # reserve doi
            landing_page = self.data.get('url', 'https://ors.datacite.org/doi:/'+doi)

            reserve_doi = requests.put(
                url = DATACITE_URL + '/doi/' + doi,
                auth = self.auth,
                data = "doi="+doi+"\nurl="+landing_page,
                )


            response.get('datacite').update({
                'doiReservation': reserve_doi.content.decode('utf-8')
                })


        # register media
        contentUrl = self.data.get('contentUrl')
        fileFormat = self.data.get('fileFormat')
        if contentUrl is not None and fileFormat is not None:
            if isinstance(contentUrl, list):
                media = '\n'.join([fileFormat+'='+media_elem for media_elem in contentUrl])
                media_responses = []
                for media_elem in contentUrl:
                    media = fileFormat+'='+media_elem
                    media_request = requests.post(
                            url = DATACITE_URL + '/media/' + doi,
                            auth = self.auth,
                            data = media,
                            headers = {'Content-Type': 'text/plain'}
                            )

                    media_responses.append(media_request.content.decode('utf-8'))

                response.get('datacite').update({ 'mediaRegistration': media_responses })

            elif isinstance(contentUrl, str):
                media = fileFormat+'='+contentUrl
                single_media_request = requests.post(
                        url = DATACITE_URL + '/media/' + doi,
                        auth = self.auth,
                        data = media,
                        headers = {'Content-Type': 'text/plain'}
                        )


                response.update({
                            'mediaRegistration': single_media_request.content.decode('utf-8')
                            })


        return Response(
            status = 200,
            response = json.dumps(response),
            mimetype = 'application/json'
            )


    def fetch(self, content_type):
        datacite_request = requests.get(
                url = 'https://data.datacite.org/application/vnd.schemaorg.ld+json/'+ self.guid
                )

        if datacite_request.status_code == 404:
            # look in MDS to find if metadata has been recently submitted
            return self.fetch_mds(content_type)

        payload = json.loads(datacite_request.content.decode('utf-8'))


        # get content contentURL from the works API
        works_response = requests.get(url = 'https://api.datacite.org/works/'+ self.guid)

        works = json.loads(works_response.content.decode('utf-8'))
        media = works.get('data', {}).get('attributes').get('media')

        payload['contentUrl'] = [media_elem.get('url') for media_elem in media]
        payload['fileFormat'] = list(set([media_elem.get('media_type') for media_elem in media]))


        if content_type == 'text/html':
            template = jinja_env.get_template('Doi.html')
            return Response(status=200,
                    response = template.render(data = payload),
                    mimetype = 'text/html')
        else:
            return Response(status=200,
                    response = json.dumps(payload),
                    mimetype = 'application/ld+json'
                    )


    def fetch_mds(self, content_type):
        mds_get = requests.get(
                url = DATACITE_URL+'/metadata/'+ self.guid,
                auth = self.auth
                )

        media_get = requests.get(
                url = DATACITE_URL+'/media/'+ self.guid,
                auth = self.auth
                )

        doi_get = requests.get(
                url = DATACITE_URL+'/doi/'+ self.guid,
                auth = self.auth
                )

        if mds_get.status_code == 404:
            if content_type == 'text/html':
                template = jinja_env.get_template('DoiNotFound.html')
                return Response(status=404,
                        response = template.render(doi= 'http://doi.org/'+self.guid),
                        mimetype='text/html')
            else:
                return Response(status=404,
                        response = json.dumps({
                            '@id': self.guid,
                            'code': 404,
                            'url':'https://data.datacite.org/application/vnd.schemaorg.ld+json/'+ self.guid,
                            'error': 'Doi Was not Found'}),
                        mimetype='application/ld+json')

        else:
            xml = mds_get.content.decode('utf-8').replace('<?xml version="1.0" encoding="UTF-8"?>', '').replace('\n','')
            doi_metadata = DoiXML(xml)
            json_ld = doi_metadata.parse()

            # add url
            json_ld['url'] = doi_get.content.decode('utf-8')

            # add media query
            json_ld['fileFormat'] =list(set(el.split('=')[0] for el in  media_get.content.decode('utf-8').split('\n')))
            json_ld['contentUrl'] = list(set(el.split('=')[1] for el in  media_get.content.decode('utf-8').split('\n')))

            if content_type == 'text/html':
                template = jinja_env.get_template('Doi.html')
                return Response(status=200,
                        response = template.render(data = json_ld),
                        mimetype = 'text/html')
            else:
                return Response(
                        status= 200,
                        response = json.dumps(json_ld),
                        mimetype='application/ld+json'
                        )


    def delete_api(self):
        doi = self.guid

        delete_metadata = requests.delete(
                url = self.endpoint+'/metadata/'+doi,
                auth = self.auth
                )
        metadata_status = delete_metadata.status_code

        delete_doi.apply_async(
            kwargs = {
                'guid': doi
                })

        # Not in MDS Production Yet
        #delete_doi = requests.delete(
        #        url = self.endpoint+'/doi/'+doi,
        #        auth = self.auth
        #    )
        #doi_status = delete_doi.status_code

        response_dict = {
                '@id': self.guid,
                'metadataDeletion': {
                    'status': delete_metadata.status_code,
                    'message': delete_metadata.content.decode('utf-8')
                }
                }

                #'doiDeletion': {
                #    'status': delete_doi.status_code,
                #    'message': delete_doi.content.decode('utf-8'),
                #}
                #}

        #if metadata_status == 200 and doi_status == 204:
        #    full_status = 204
        #    response_dict['message'] = 'Metadata record and doi reservation deleted'
        #elif metadata_status == 200 or doi_status == 204:
        #    full_status = 207
        #    response_dict['message'] = 'Partial Success, doi may not be deleted if not minted with "draft" status'
        #else:
        #    full_status = 400
        #    response_dict['message'] = 'Error; Metadata record and doi reservation unable to be deleted'

        return Response(
            status = metadata_status,
            response = json.dumps(response_dict),
            mimetype = 'application/json'
            )


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


class Dataguid(object):
    auth = requests.auth.HTTPBasicAuth(
            os.environ.get('INDEXD_USER'),
            os.environ.get('INDEXD_PASSWORD')
            )
    indexd_url = os.environ.get('INDEXD_URL')


    def __init__(self, schema_json=None, dg_json=None, did=None):
        if schema_json is not None:
            self.schema_json = schema_json
            self.dg_json = None

        if dg_json is not None:
            self.dg_json = dg_json

        self.did = did


    def to_dataguid(self):
        ''' Convert schema.org json-ld to Dataguid metadata format
        '''
        self.checksums = list(filter(lambda x: isinstance(x, dict), self.schema_json.get('identifier')))

        self.dg_json = {
                'form': 'object',
                'hashes': {checksum.get('name'): checksum.get('value') for checksum in self.checksums},
                'urls': self.schema_json.get('contentUrl'),
                'file_name': self.schema_json.get('name'),
                #re.findall(r'\w*.\w*$', self.schema_json.get('contentUrl')[0])[0],
                'size': int(self.schema_json.get('contentSize')),

                # Metadata breaks posting to
                #'metadata': self.schema_json
                }

        if self.schema_json.get('dateCreated') is None:
            self.schema_json['dateCreated'] = str(datetime.datetime.now())

        if self.schema_json.get('url') is None:
            self.schema_json['url'] = ORS_URL+'dataguid:/{}'.format(self.schema_json.get('@id'))

        if self.schema_json.get('version') is not None:
            self.dg_json['version'] = self.schema_json.get('version')


    def to_schema(self):
        ''' Convert Dataguid metadata format to schema.org json-ld
        '''

        self.schema_json = {
                '@context': 'https://schema.org',
                '@id': self.dg_json.get('did'),
                '@type': 'Dataset',
                'identifier': [
                    self.dg_json.get('did'),
                    self.dg_json.get('baseid')
                    ],
                'name': self.dg_json.get('file_name'),
                'url': ORS_URL+'/dataguid:/{}'.format(self.dg_json.get('did')),
                'contentSize': self.dg_json.get('size'),
                'dateCreated': self.dg_json.get('created_date'),
                'contentUrl': self.dg_json.get('urls'),
                'version': self.dg_json.get('version')
                }

        [self.schema_json.get('identifier').append({'@type': 'PropertyValue', 'name': key, 'value': value}) \
                for key,value in self.dg_json.get('hashes').items()]


    def fetch_indexd(self, content_type, format_):
        ''' Return results from Indexd
            TODO Unittest
        '''
        get_indexd = requests.get(
                url = self.indexd_url+'index/'+self.did,
                headers={'content-type': 'application/json'}
                )

        if get_indexd.status_code == 404:
            response_message = {
                    "@id": self.did,
                    "status": 404,
                    "message": "No Identifier found for dataguid {}".format(self.did)
                }

            if content_type == 'text/html':
                template = jinja_env.get_template('DataguidError.html')
                return template.render(data=response_message)
            else:
                return Response(status = 404,
                        response= json.dumps(response_message),
                        mimetype='text/html'
                        )


        else:
            self.dg_json = json.loads(get_indexd.content.decode('utf-8'))

            if content_type == 'text/html':
                self.to_schema()
                template = jinja_env.get_template('Dataguid.html')
                return template.render(
                        data=self.schema_json,
                        checksums=list(filter(lambda x: isinstance(x, dict), self.schema_json.get('identifier')))
                        )

            else:
                if format_ == 'dg':
                    return Response(
                            status=200,
                            response=json.dumps(self.dg_json),
                            mimetype='application/json'
                            )

                else:
                    self.to_schema()
                    return Response(
                            status=200,
                            response=json.dumps(self.schema_json),
                            mimetype='application/ld+json'
                            )

    def post_indexd(self, user):
        ''' Post Dataguid to Indexd
            TODO Unittest
        '''

        post_dg = requests.post(
                url = self.indexd_url+ 'index/',
                data = json.dumps(self.dg_json),
                auth = self.auth,
                headers = {'content-type': 'application/json'}
                )

        if post_dg.status_code == 200:
            dg = json.loads(post_dg.content.decode('utf-8'))
            did = dg.get('did')

            # add task to celery to keep record of celery
            put_task = put_dataguid.delay(
                    UserEmail = user.email,
                    did = did,
                    baseId = dg.get('baseid'),
                    rev = dg.get('rev'),
                    schemaJson = self.schema_json
                    )

            return Response(
                    status=201,
                    response=post_dg.content,
                    mimetype='application/json'
                    )

        else:
            return Response(
                    status = 400,
                    response = json.dumps({
                        'status': 400,
                        'message': 'Failed to mint Identifier',
                        'indexd': post_dg.content.decode('utf-8')
                        })

                    )

    def update_indexd(self, user, rev):
        update_dg = requests.put(
            url = self.indexd_url+'index/'+self.did+'?rev='+rev,
            auth = self.auth,
            data = json.dumps({
                'acl': self.dg_json.get('acl', []),
                'file_name': self.dg_json.get('file_name'),
                'metadata': self.dg_json.get('metadata', {}),
                'urls': self.dg_json.get('urls'),
                'urls_metadata': self.dg_json.get('urls_metadata', {}),
                'version': self.dg_json.get('version'),
                }),
            headers = {'content-type':'application/json'}
        )

        dg = json.loads(update_dg.content.decode('utf-8'))
        did = re.sub(r'^\w*:', '', self.did)

        # add to put_task
        put_task = put_dataguid.delay(
                UserEmail = user.email,
                did = did,
                baseId = dg.get('baseid'),
                rev = dg.get('rev'),
                schemaJson = self.schema_json
                )

        return Response(
                status=201,
                response=update_dg.content,
                mimetype='application/json'
                )


    def delete_indexd(self, revision=None):
        ''' Delete Dataguid from Indexd
            TODO Unittest
        '''
        if revision is not None:
            delete_dg = requests.delete(
                    url = self.indexd_url+'index/'+self.did+'?rev='+revision,
                    auth = self.auth,
                    headers = {'content-type': 'application/json'}
                    )

            if delete_dg.status ==404:
                return Response(
                        status = 404,
                        response = json.dumps({
                            '@id': self.did,
                            'status': 404,
                            'message': 'Could not find identifier to be deleted'
                            })
                        )

            # submit delete task to celery
            delete_task = delete_dataguid.delay(
                    did = re.sub(r'^\w*:', '',self.did),
                    rev = revision
                    )


            return Response(
                    status = delete_dg.status_code,
                    response = json.dumps({
                        'status': delete_dg.status_code,
                        'message': 'Deleted Dataguid',
                        'did': self.did,
                        'rev': revision
                        }),


                    mimetype = 'application/json'
                    )

        else:
            get_versions = requests.get(
                    url = self.indexd_url+'index/'+self.did+'/versions',
                    auth = self.auth,
                    headers = {'content-type': 'application/json'}
                    )

            if get_versions.status_code !=200:
                return Response(
                        status = get_versions.status_code,
                        response = get_versions.content,
                        mimetype='application/json'
                        )

            versions = json.loads(get_versions.content.decode('utf-8'))

            revision_list = [ rev.get('rev') for rev in versions.values()]
            baseId = versions.get('0', {}).get('baseid')


            for rev in revision_list:
                    temp_rev = rev
                    delete_dg = requests.delete(
                            url = self.indexd_url+'index/'+self.did+'?rev='+rev,
                            auth = self.auth,
                            headers = {'content-type': 'application/json'}
                            )


                    # submit delete task to celery
                    delete_task = delete_dataguid.delay(
                            did = re.sub(r'^\w*:', '', self.did),
                            rev = rev
                            )

            return Response(
                    status=delete_dg.status_code,
                    response = json.dumps({
                        'status': delete_dg.status_code,
                        'message': 'Deleted Dataguid',
                        'did': self.did,
                        'baseId': baseId,
                        'rev': revision_list
                        })
                    )



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
