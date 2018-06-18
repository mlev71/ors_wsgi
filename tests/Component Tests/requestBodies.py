import re
from flask import Response as flaskResponse
import json


BadHeaders = Response(
            response = "Content Headers Incorrect, API only accepts mimetype application/json",
            status = 406,
            mimetype = 'text/plain'
        )

EmptyContent = Response(
            response = "Request Form Missing Necesary Details, need to submit data to make calls",
            status = 406,
            mimetype = 'text/plain'
        )

NotJSONresponse = Response(
                response = "Unsuported Media Type, data must be submitted as a JSON payload",
                status = 451,
                mimetype = 'text/plain'
                )

Lazy501 = Response(
        response = 'Funcionality Not Yet Implemented, Sorry -Max Levinson',
        status = 501,
        mimetype = 'text/plain'
        )


class Minid:
    def __init__(self, JSONinput):
        decodedDict = json.JSONDecoder.decode(JSONinput)
        self.Idenfitier = decodedDict['Idenfitier']
        if not decodedDict['Created']:
            # mint the time now in the correct format
            #self.Created = time.now or something
            pass
        else:
            self.Created = decodedDict['Created']
        
        if not decodedDict['Checksum']:
            # create a checksum
            #self.Checksum = checksumFunction(...)
            pass
        else: 
            self.Checksum = decodedDict['Checksum']

        self.Status = decodedDict['Status']
        self.Locations = decodedDict['Locations']
        self.Titles = decodedDict['Titles']

requiredKeys = ['target', 'identifier', 'created', 'checksum', 'status', 'locations', 'titles']

# OUGHT TO BE A WRAPPER IN THE FUTURE
def validateRequest(request):
    ''' 
    Pass the request object, and inspect
    If unsucsessfull return the appropriate error response
        - Content-Type return 406 not acceptable 
        - Empty-Body
        - Missing important object fields
    '''
    if request.headers['ContentType'] != 'application/json':
        return BadHeaders
    if not request.form:
        return EmptyContent
    else:
        decodedDict = json.JSONDecoder.decode(request.form)
        if all (reqKeys in decodedDict for reqKeys in requiredKeys): 

            #pop the target from JSON 
            target = '_target: ' + decodedDict.pop('target')

            internalMetadata = [ 
                    target,
                    '_profile: minid',
                    '_status: reserved',
                    '_export: no',
                    '_crossref: no'
                    ]
            minidMetadata = ['minid'.key + ': ' + value for key,value in decodedDict.items()]
            plaintextData = "\n".join(internalMetadata + minidMetadata)
            return plaintextData

        else:
            return EmptyContent



class Metadata(object):
    '''Consumes JSON and returns metadata must have a chosen profile'''
    def __init__(self,JSONinput):
        self.JSONinput = JSONinput 
        # make a text/file
        self.profile = None

    def convert(self, outputType):
        pass

class ANVL:
    '''Format for Metadata Dictionaries with One Element name/value pair'''
    def __init__(self, who, what, when):
        mdList = [str('who: '+ who), str('what: '+ what), str('when: '+ when)]
        self.anvl = '/n'.join([ele.encode('UTF-8') for ele in mdList])

class InternalMetadata:
    '''Format for Metadata used by EZID'''
    def __init__(self, propertyDict):
        pass

class DublinCore(object):
    '''Dublin Core Metadata Standard'''
    def __init__(self, propertyDict):
       pass

class DataCite(object):
    def __init__(self, propertyDict):
        pass

class ERC(object):
    def __init__(self, propertyDict):
        pass

def parseID(Idenfitier):
    '''Determine if Identifier is ARK, EZID, or UUID''' 
    if re.match("ark:.*", Identifier):
        return "ark"
    if re.match("doi:.*", Idenfitier):
        return "doi" 
    if re.match("uuid:.*", Idenfitier):
        return "uuid" 
    else:
        return "Unmatched Identifier"

def jsonToANVL(JSONinput):
    '''Takes in JSON input and returns ANVL key value pairs seperated by newlines '''
    decodedDict = json.JSONDecoder.decode(JSONinput)
    return "\n".join([key + ': ' + value for key,value in decodedDict.items()])
    

# 401 Unauthorized
EmptyAuth = flaskResponse(
        response = 'Missing Login information, cannot use MDS without authentication',
        status = 401,
        mimetype = 'text/plain'
        )

# 404 
NotFinished404 = flaskResponse(
        response = 'Funcionality Not Yet Implemented',
        status = 404,
        mimetype = 'text/plain'
        )


def buildResponse(ReqResponse, ContentType="text/plain"):
    '''Transfer requests response object into a flask Response object'''
    builtResponse = flaskResponse(
            status = ReqResponse.status_code,
            response = ReqResponse.content,
            mimetype = ContentType
            )
    return builtResponse
