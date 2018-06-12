import json
import os
import re
from neo4j.v1 import GraphDatabase
from flask import render_template, Response

###################
# GLOBAL CONSTANTS#
###################
PROXY = os.environ['PROXY_URL']


##############################
# Factory Pattern for Objects#
##############################


def JSONfactory(Response, Neo_Driver=None):
    """ Mints Core Metadata Objects and formats them for submission to APIs

    """
    jsonDict = Response 
    KEYS = set([keys for keys in jsonDict.keys()])

    if DATA_DOWNLOAD_KEYS_JSON.issuperset(KEYS):
        dload = DataDownload(jsonDict, "JSON")
        if Neo_Driver is not None:
            if dload.ValidateParent(Neo_Driver):
                dload.RegisterNeo(Neo_Driver)
                return dload
            else:
                # attempt to import parent

                raise InvalidParent(jsonDict['includedInDataset'])
        else:
            return dload

    if DATASET_KEYS_JSON.issuperset(KEYS):
        dset = Dataset(jsonDict, "JSON")
        if Neo_Driver is not None:
            if dset.ValidateParent(Neo_Driver): 
                dset.RegisterNeo(Neo_Driver)
                return dset
            else:
                # attempt to import parent

                raise InvalidParent(jsonDict['includedInDataCatalog'])
        else:
            return dset

    if DATA_CATALOG_KEYS_JSON.issuperset(KEYS):
        dcatalog = DataCatalog(jsonDict, "JSON")
        if Neo_Driver is not None:
            dcatalog.RegisterNeo(Neo_Driver)
            return dcatalog
        else:
            return dcatalog

    if MINID_KEYS_JSON.issuperset(KEYS):
        mid = Minid(jsonDict, "JSON")
        if Neo_Driver is not None:
            mid.RegisterNeo(Neo_Driver)
            return mid
        else:
            return mid

    else:
        raise NotCoreObject(KEYS)

def ANVLfactory(Response, Neo_Driver=None): 
    anvlDict = digestANVL(Response) 
    KEYS = set([keys for keys in anvlDict.keys()])
   
    if  KEYS.issuperset(DATA_DOWNLOAD_KEYS_ANVL): 
        return DataDownload(anvlDict, "ANVL")

    if KEYS.issuperset(DATASET_KEYS_ANVL):
        return Dataset(anvlDict, "ANVL")

    if KEYS.issuperset(DATA_CATALOG_KEYS_ANVL):
        return DataCatalog(anvlDict, "ANVL")

    if KEYS.issuperset(MINID_KEYS_ANVL):
        return Minid(anvlDict, "ANVL")

    else:
         raise NotCoreObject(KEYS)

def PayloadFactory(Response, Type, Neo_Driver=None):
    ''' Factory Pattern, returns the appropriate object
    '''

    # ANVL is from EZ api to Client
    if Type=="ANVL":
        return ANVLfactory(Response, Neo_Driver)

    # JSON is from Client to EZ API
    if Type=="JSON":
        return JSONfactory(Response, Neo_Driver)



##################################################
#                    Response Bodies             #
##################################################
# need to comment out the use of proxy until DNS set up
#PROXY = "https://ezid.cdlib.org/id/"

class BodyResponse(object):
    def __init__(self, Response, Type):
        assert Type == "ANVL" or Type == "JSON"
        self.ANVLdict = None
        self.JSONdict = None

        if Type == "ANVL":
            self.ANVLdict = Response
            self.ANVLtoJSON() # convert to JSON

        if Type == "JSON":
            self.JSONdict = Response
            self.JSONtoANVL() # convert to ANVL


    def returnANVL(self):
        """
            Return the ANVL text

        """
        if self.ANVLdict is None:
            self.JSONtoANVL()
        return "\n".join("%s: %s" % (escape(name), escape(value)) for \
                name, value in self.ANVLdict.items()).encode("UTF-8") 


    def returnJSON(self):
        """
            Return the json payload encoded as json
        """
        if self.JSONdict is None:
            self.ANVLtoJSON()
        return json.dumps(self.JSONdict)





# minid keys
MINID_KEYS_ANVL = set(['_target','minid.created','minid.creator',
    'minid.checksum','minid.checksumMethod', 'minid.status', 
    'minid.locations', 'minid.titles']) 
MINID_KEYS_JSON = set(['identifier', 'created', 'creator', 'checksum',
    'checksumMethod','status','locations', 'titles'])

class Minid(BodyResponse):

    def ANVLtoJSON(self):
        ''' 
            Convert the ANVLdict to the JSONdict 
                Describing the Mapping
                _target         ->      identifier
                minid.created   ->      created
                minid.creator   ->      creator
                minid.checksum  ->      checksum
                minid.checksumMethod -> checksumMethod
                minid.status    ->      status
                minid.locations ->      locations
                minid.titles    ->      titles
        '''
        self.JSONdict = {}
        # changing to EZID default target for now
        self.JSONdict['identifier'] = self.ANVLdict['_target'].replace(EZID,"")
        self.JSONdict['created'] = self.ANVLdict['minid.created']
        self.JSONdict['creator'] = self.ANVLdict['minid.creator']
        self.JSONdict['checksum'] = self.ANVLdict['minid.checksum']
        self.JSONdict['checksumMethod'] = self.ANVLdict['minid.checksumMethod']
        self.JSONdict['status'] = self.ANVLdict['minid.status']
        self.JSONdict['locations'] = list(self.ANVLdict['minid.locations'].split(";"))
        self.JSONdict['titles'] = list(self.ANVLdict['minid.titles'].split(";"))

    def JSONtoANVL(self):
        ''' 
            Conver the ANVLdict to the JSONdict 
                Setting EZID metadata
                    _profile = minid
                    _status  = reserved
                Describing the Mapping
                    created         -> minid.created
                    creator         -> minid.creator
                    checksum        -> minid.checksum
                    checksumMethod  -> minid.checksumMethod
                    status          -> minid.status
                    locations       -> minid.locations
                    titles          -> minid.titles
        
        # ommiting target and letting EZID set default targets
        #self.ANVLdict['_target'] = "".join([PROXY, self.JSONdict['identifier']])
        
        '''
        self.ANVLdict = {}
        self.ANVLdict['_profile'] = 'minid'
        self.ANVLdict['_status'] = 'reserved'
        self.ANVLdict["minid.identifier"] = self.JSONdict["identifier"]
        self.ANVLdict['minid.created'] = self.JSONdict['created']
        self.ANVLdict['minid.creator'] = self.JSONdict['creator']
        self.ANVLdict['minid.checksum'] = self.JSONdict['checksum']
        self.ANVLdict['minid.checksumMethod'] = self.JSONdict['checksumMethod']
        self.ANVLdict['minid.status'] = self.JSONdict['status']
        self.ANVLdict['minid.locations'] = ";".join(self.JSONdict['locations'])
        self.ANVLdict['minid.titles'] = ";".join(self.JSONdict['titles'])
        self.GUID = self.JSONdict['identifier']

    def RegisterNeo(self, driver):
        '''
            Store the Minid in Neo4j
        '''
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("CREATE (ID:minid) " 
                       "SET ID.guid = $ark "
                       "SET ID.created = $created "
                       "SET ID.creator = $creator "
                       "SET ID.checksum = $checksum "
                       "SET ID.checksumMethod = $checksumMethod "
                       "SET ID.status = $status "
                       "SET ID.locations = $locations "
                       "SET ID.titles = $titles ",
                       ark = self.JSONdict['identifier'],
                       created = self.JSONdict['created'],
                       creator = self.JSONdict['creator'],
                       checksum = self.JSONdict['checksum'],
                       checksumMethod = self.JSONdict['checksumMethod'],
                       status =self.JSONdict['status'],
                       locations = self.JSONdict['locations'],
                       titles = "; ".join(self.JSONdict['titles']))
        
    def ValidateParent(self, driver):
        """
            Minid's dont yet have associations all are valid
        """
        return True

    def RenderLandingPage(self): 
        """ Render the Minid object with the minid template
       
            Currently only uses identifier level metadata in the landing page
        """
        if not (self.JSONdict):
            self.ANVLtoJSON()
        return render_template('minid.html', Payload=self.JSONdict)


# dataCatalog keys
DATA_CATALOG_KEYS_ANVL = set(['_target', 'NIHdc.identifier', 'NIHdc.name', 'NIHdc.url'])
DATA_CATALOG_KEYS_JSON = set(['@context', '@id', '@type', 'identifier', 'name', 'url'])

class DataCatalog(BodyResponse):
    context = json.dumps({ "@context": {
            "name": "http://schema.org/name",
            "identifier": {
                "@id": "http://schema.org/identifier",
                "@type": "@id"
                },
            "url": {
                "@id": "http://schema.org/url",
                "@type": "@id"
                }
            }
        })

    def JSONtoANVL(self):
        ''' Format DataCatalog for submission to APIs
        '''
        self.ANVLdict = {}
        self.ANVLdict['_profile'] = 'NIHdc'
        self.ANVLdict['_status'] = 'reserved'
        self.ANVLdict['_target'] = "".join([PROXY, self.JSONdict['@id']])
        self.ANVLdict['NIHdc.identifier'] = self.JSONdict['identifier']
        self.ANVLdict['NIHdc.name'] = self.JSONdict['name']
        self.ANVLdict['NIHdc.url'] = self.JSONdict['url']

        # store the GUID for determining target
        self.GUID = self.JSONdict['@id']

    def ANVLtoJSON(self):
        self.JSONdict = {} 
        self.JSONdict['@context'] = 'http://schema.org'
        self.JSONdict['@type'] = "DataCatalog"
        self.JSONdict['@id'] = self.ANVLdict['_target'].replace(PROXY, "")
        self.JSONdict['identifier'] = self.ANVLdict['NIHdc.identifier']
        self.JSONdict['name'] = self.ANVLdict['NIHdc.name']
        self.JSONdict['url'] = self.ANVLdict['NIHdc.url']

    def RegisterNeo(self, driver):
        '''
            Store the DataCatalog in Neo4j
        '''
        with driver.session() as session:
            with session.begin_transaction() as tx:
                result = tx.run("MERGE (n:dataCatalog {guid: $guid, name: $name}) ",
                       guid = self.JSONdict['@id'],
                       name = self.JSONdict['name'])

    def ValidateParent(self, driver):
        '''
            DataCatalog doesn't yet have a parent object
        '''
        return True

    def RenderLandingPage(self):
        """ Render the Landing Page  using the DataCatalog
        """
        if not (self.JSONdict):
            self.ANVLtoJSON()
        return render_template('datacatalog.html', Payload=self.JSONdict)

# dataset keys
DATASET_KEYS_ANVL = set(['_target', 'NIHdc.identifier', 'NIHdc.includedInDataCatalog','NIHdc.dateCreated'])
DATASET_KEYS_JSON = set(['@context', '@type', '@id', 'identifier', 'includedInDataCatalog', 'dateCreated'])

# Keys DOI
required_keys_doi = set(['@id', '@type', 'identifier', 'url', 'includedInDataCatalog', 'name', 'author', 'datePublished'])
optional_keys_doi = set(['dateCreated', 'additionalType', 'description', 'keywords', 'license', 'version', 'citation',
    'isBasedOn', 'isPredecessor', 'isSuccessor', 'hasPart', 'isPartOf', 'funder', 'contentSize', 'fileFormat', 'contentUrl'])

# Compact Identifiers

# ARKS

class Dataset(BodyResponse):
    context = json.dumps({})

    def JSONtoANVL(self):
        self.ANVLdict = {}
        self.ANVLdict['_profile'] = 'NIHdc'
        self.ANVLdict['_status'] = 'reserved'
        self.ANVLdict['_target'] = "".join([PROXY, self.JSONdict['@id']])
        self.ANVLdict['NIHdc.identifier'] = self.JSONdict['identifier']
        self.ANVLdict['NIHdc.includedInDataCatalog'] = self.JSONdict['includedInDataCatalog']
        self.ANVLdict['NIHdc.dateCreated'] = self.JSONdict['dateCreated']
        self.GUID = self.JSONdict['@id']

    def ANVLtoJSON(self):
        self.JSONdict = {} 
        self.JSONdict['@context'] = 'http://schema.org'
        self.JSONdict['@id'] = self.ANVLdict['_target'].replace(PROXY, "")
        self.JSONdict['@id'] = self.ANVLdict['_target']
        self.JSONdict['@type'] = "Dataset"
        self.JSONdict['identifier'] = self.ANVLdict['NIHdc.identifier']
        self.JSONdict['includedInDataCatalog'] = self.ANVLdict['NIHdc.includedInDataCatalog']
        self.JSONdict['dateCreated'] = self.ANVLdict['NIHdc.dateCreated']

    def RegisterNeo(self, driver):
        '''
            Store the DataCatalog in Neo4j
        '''
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("CREATE (d:dataset {guid: $guid, dateCreated: $created}) "
                        "WITH d "
                        "MATCH (p:dataCatalog) "
                        "WHERE p.guid = $catalog "
                        "CREATE (p)-[:PROVIDER_OF]->(d) "
                        "RETURN d ",
                        guid = self.JSONdict['@id'],
                        catalog = self.JSONdict['includedInDataCatalog'],
                        created = self.JSONdict['dateCreated'])
    
    def ValidateParent(self, driver):
        '''
            Query Neo looking for a valid parent object -> return boolean
        ''' 
        with driver.session() as session:
            with session.begin_transaction() as tx:
                result = tx.run( "MATCH (p:dataset) "
                        "WHERE p.guid = $parent "
                        "RETURN count(p)",
                        parent = self.JSONdict['includedInDataCatalog'])

        count = result.single()[0] 
        if count >= 1:
            return True
        else:
            return False

    def RenderLandingPage(self):
        if not (self.JSONdict):
            self.ANVLtoJSON()
        return render_template('dataset.html', Payload=self.JSONdict)

# dataDownload keys
DATA_DOWNLOAD_KEYS_ANVL = set(['_target', 'NIHdc.identifier', 'NIHdc.version', 
    'NIHdc.includedInDataset', 'NIHdc.contentSize', 'NIHdc.fileFormat', 
    'NIHdc.contentUrl', 'NIHdc.checksum', 'NIHdc.checksumMethod', 'NIHdc.filename'])


DATA_DOWNLOAD_KEYS_JSON = set(['@context', '@id', '@type', 'identifier', 'version', 
    'includedInDataset', 'contentSize', 'fileFormat', 'contentUrl', 
    'checksum', 'checksumMethod', 'filename'])

class DataDownload(BodyResponse):

    def JSONtoANVL(self):
        self.ANVLdict = {}
        self.ANVLdict['_profile'] = 'NIHdc'
        self.ANVLdict['_status'] = 'reserved'
        #self.ANVLdict['_target'] = "".join([PROXY, self.JSONdict['@id']])
        self.ANVLdict['NIHdc.identifier'] = self.JSONdict['identifier']
        self.ANVLdict['NIHdc.includedInDataset'] = self.JSONdict['includedInDataset']
        self.ANVLdict['NIHdc.version'] = self.JSONdict['version']
        self.ANVLdict['NIHdc.contentSize'] = self.JSONdict['contentSize']
        self.ANVLdict['NIHdc.fileFormat'] = self.JSONdict['fileFormat']
        self.ANVLdict['NIHdc.contentUrl'] = self.JSONdict['contentUrl']
        self.ANVLdict['NIHdc.checksum'] = self.JSONdict['checksum']
        self.ANVLdict['NIHdc.checksumMethod'] = self.JSONdict['checksumMethod']
        self.ANVLdict['NIHdc.filename'] = self.JSONdict['filename']
        self.GUID = self.JSONdict['@id']

    def ANVLtoJSON(self):
        self.JSONdict = {}   
        self.JSONdict['@context'] = 'http://schema.org'
        #self.JSONdict['@id'] = self.ANVLdict['_target'].replace(PROXY, "")
        self.JSONdict['@id'] = self.ANVLdict['_target'].replace(EZID, "")
        self.JSONdict['@type'] = "DatasetDownload"
        self.JSONdict['identifier'] = self.ANVLdict['NIHdc.identifier'] 
        self.JSONdict['includedInDataset'] = self.ANVLdict['NIHdc.includedInDataset'] 
        self.JSONdict['version'] = self.ANVLdict['NIHdc.version']
        self.JSONdict['contentSize'] = self.ANVLdict['NIHdc.contentSize'] 
        self.JSONdict['fileFormat'] = self.ANVLdict['NIHdc.fileFormat']
        self.JSONdict['contentUrl'] = self.ANVLdict['NIHdc.contentUrl']
        self.JSONdict['checksum'] = self.ANVLdict['NIHdc.checksum'] 
        self.JSONdict['checksumMethod'] = self.ANVLdict['NIHdc.checksumMethod'] 
        self.JSONdict['filename'] = self.ANVLdict['NIHdc.filename']
 
    def RegisterNeo(self, driver):
        '''
            Store the dataDownload in Neo4j
        '''
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("CREATE (d:download {guid: $guid, checksum: $checksum, method: $method, contentSize: $size, fileFormat: $fileFormat, contentUrl: $contentUrl, filename: $filename}) "
                                "WITH d "
                                "MATCH (s:dataset) "
                                "WHERE s.guid = $dataset "
                                "CREATE (s)-[:DOWNLOAD]->(d) "
                                "RETURN d ",
                                guid = self.JSONdict['@id'],
                                checksum = self.JSONdict['checksum'],
                                method = self.JSONdict['checksumMethod'],
                                size = self.JSONdict['contentSize'],
                                fileFormat = self.JSONdict['fileFormat'],
                                contentUrl = self.JSONdict['contentUrl'],
                                dataset = self.JSONdict['includedInDataset'],
                                filename = self.JSONdict['filename'])
    
    def ValidateParent(self, driver):
        '''
            Query Neo looking for a valid parent object -> return boolean
        '''
        with driver.session() as session:
            with session.begin_transaction() as tx:
                result = tx.run( "MATCH (p:dataset) "
                        "WHERE p.guid = $parent "
                        "RETURN count(p)",
                        parent = self.JSONdict['includedInDataset'])
        count = result.single()[0]
        if count >= 1:
            return True
        else:
            return False

    def RenderLandingPage(self):
        """
            Render the landing page for the DataDownload Object 
        """
        if not (self.JSONdict):
            self.ANVLtoJSON()
        return render_template('datadownload.html', Payload=self.JSONdict)



def deleteGUID(ID, driver):
    ''' Detach and Delete node from neo4j cache
        To do: Return Data from Node parsed into a dictionary
    '''
    with driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run("MATCH (d) "
                    "WHERE d.guid = $guid "
                    "DETACH DELETE d ",
                    guid = ID)

def escape (s):
    " Properly Format Every Line of ANVL format for parsing "
    return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)

def digestANVL(response_text):
    ANVLdict = {}
    if isinstance(response_text, bytes):
        tempANVL = response_text.decode('UTF-8')
    else:
        tempANVL = response_text
        
    for element in tempANVL.split("\n"):
        SplitUp = element.split(": ", 1)
        if len(SplitUp)>1:
            ANVLdict[SplitUp[0]] = SplitUp[1]
    return ANVLdict


########################################## 
#    Custom Exceptions with Responses    # 
##########################################

class NotCoreObject(Exception):
    """ Error Raised if a Key's Provided are Insufficient for Core Metadata Objects

    """
    def __init__(self, Keys):
        """ Format Message on Init, and serve Error as a Flask Response in json"""
        keyString = " ".join([ "[" , ",".join(list(Keys)) , "]"])
        self.message = {"Keys": keyString, "message": "Object Keys do not match any core metadata standards"}

    def output(self):
        return Response(
                status = 400,
                response = json.dumps(self.message),
                mimetype= 'application/json'
                )



class UnsupportedGuid(Exception):
    """ 
    """
    def __init__(self, Guid):
        self.message = {"Guid": str(Guid), "message": "Guid is neither an Ark nor a DOI"}

    def output(self):
        return Response(
                status = 400,
                response = json.dumps(self.message),
                mimetype = 'application/json'
                )

class InvalidParent(Exception):
    """ Error: Object has no Parent object in the noe cache

    """

    def __init__(self, Parent):
        self.message = {"Guid": str(Parent), "message": "No Record of the parent in the cache, cannot mint dependant object until parent exists"}

    def output(self):
        return Response(
                status = 404,
                response = json.dumps(self.message),
                mimetype = 'application/json'
                )


def detTarget(ID):
    """ Send the proposed ID to the proper address
        ID matches an ARK return EZID address
        ID matches a DOI return Datacite address
    """
    if re.match("ark:/", ID):
        return "https://ezid.cdlib.org/id/" + ID
    if re.match("doi:", ID):
        return "https://ez.datacite.org/id/" + ID
    else:
        raise UnsupportedGuid(ID)

