from lxml import objectify, etree
import re
import base64

##############
# CONSTANTS  #
##############

nameType_xml = {
    'Organization': 'Organizational',
    'Person': 'Personal'
}
nameType_json = {
    'Organizational': 'Organization',
    'Person': 'Personal'
}

xml_header = '<?xml version="1.0" encoding="UTF-8"?>'
properResourceTag ='<resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">'



##########################
#   Convert To XML       #
##########################

def convertDoiToXml(doi):
    xml_string = outputDataciteXML(doi).decode('utf-8')
    datacite_xml  = xml_header + xml_string.replace('<resource>', properResourceTag)
    return datacite_xml


def outputDataciteXML(doi_json):
    ''' Convert schema.org json-ld to to XML string
    '''
    E = objectify.ElementMaker(
        annotate=False
    )

    resource = E.resource(
        E.publicationYear(doi_json.get('datePublished'))
    )

    if doi_json.get('@id') is not None:
        identifier = etree.SubElement(resource, "identifier", identifierType="DOI")._setText(doi_json.get('@id').replace('doi:/',''))

    resourceType = etree.SubElement(resource, "resourceType", resourceTypeGeneral='Dataset')._setText("CreativeWork")


    # add titles
    titles = etree.SubElement(resource, "titles")
    etree.SubElement(titles, "title")._setText(doi_json.get('name'))


    # get the author
    auth = doi_json.get('author')
    if auth is not None:
        parseAuthors(auth, resource)


    # add a single description of type abstract
    desc = doi_json.get('description')
    descriptions = etree.SubElement(resource, "descriptions")
    if desc is not None:
        etree.SubElement(descriptions, "description", descriptionType="Abstract")._setText(desc)

    # add related Ids
    relatedIds = {
            'HasPart': doi_json.get('hasPart'),
            'IsPartOf': doi_json.get('isPartOf'),
            'IsDerivedFrom': doi_json.get('isBasedOn'),
            'PredecessorOf': doi_json.get('predeccessorOf'),
            'SuccessorOf': doi_json.get('successorOf'),
            'includedInDataCatalog': doi_json.get('includedInDataCatalog')
            }

    if not all([id_ is None for id_ in relatedIds.values()]):
        related_identifiers = etree.SubElement(resource, "relatedIdentifiers")

        dc = doi_json.get('includedInDataCatalog')
        if dc is not None:
            if isinstance(dc, str):
                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                    relationType="IsPartOf")._setText(dc)

            if isinstance(dc, dict):
                # get identifier of includedInDataCatalog
                dc_id = dc.get('@id')
                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                    relationType="IsPartOf")._setText(dc_id)
                # add datacatalog name to descriptions
                dc_name = dc.get('name')
                etree.SubElement(descriptions, "description", descriptionType="SeriesInformation")._setText(dc_name)

        for key, value in relatedIds.items():
            if key!='includedInDataCatalog':
                parseRelatedIds(related_identifiers, key, value)
            else:
                continue

    # Version
    version = doi_json.get('version')
    if version is not None:
        etree.SubElement(resource, "version")._setText(version)



    # keywords
    subject_list = doi_json.get('keywords')
    if subject_list is not None:
        subjects = etree.SubElement(resource, "subjects")
        parseKeywords(subject_list, subjects)

    # funding
    funder = doi_json.get('funder')
    if funder is not None:
        parseFunder(funder, resource)

    return etree.tostring(resource)


def parseRelatedIds(related_identifiers, key, value):
    if value is not None:
        if isinstance(value, str):

            if re.match(r'doi', value):
                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="DOI",
                                    relationType=key)._setText(value)
            else:
                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                    relationType=key)._setText(value)

        if isinstance(value, dict):
            if re.match(r'doi', value.get('@id')):
                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="DOI",
                                    relationType=key)._setText(value.get('@id'))

            else:
                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                relationType=key)._setText(value.get('@id'))


def parseAuthors(auth, resource):
    ''' Add authors and publisher to XML
    '''

    creators = etree.SubElement(resource, "creators")

    if isinstance(auth, list):
        c = etree.SubElement(creators, "creator")
        # every author in the list
        for author in auth:
            auth_name = author.get('name')
            auth_type = auth.get('@type')
            name_type = nameType_xml.get(auth_type)
            etree.SubElement(c, "name", nameType=name_type)._setText(auth_name)

    if isinstance(auth, dict):
        creator = etree.SubElement(creators, "creator")

        auth_name = auth.get('name')
        auth_type = auth.get('@type')
        name_type = nameType_xml.get(auth_type)

        etree.SubElement(creator, "creatorName")._setText(auth_name)
        etree.SubElement(resource, "publisher")._setText(auth_name)


def parseFunder(funder,resource):
    ''' Update the etree element with the funding references if they exist
    '''
    funding_reference = etree.SubElement(resource, "fundingReferences")

    if funder == None:
        pass

    if isinstance(funder,list):
        for fund_elem in funder:
            fundingRef = etree.SubElement(funding_reference, "fundingReference")

            fund_name   = fund_elem.get('name')
            fund_id     = fund_elem.get('@id')
            award_num   = fund_elem.get('awardNumber')
            award_title = fund_elem.get('awardTitle')

            if fund_name:
                etree.SubElement(fundingRef, "funderName")._setText(fund_name)

            if fund_id:
                etree.SubElement(fundingRef, "funderIdentifier", funderIdentifierType="Other")._setText(fund_id)

            if award_num:
                etree.SubElement(fundingRef, "awardNumber")._setText(award_num)

            if award_title:
                etree.SubElement(fundingRef, "awardTitle")._setText(award_title)

    if isinstance(funder,dict):
        fundingRef = etree.SubElement(funding_reference, "fundingReference")

        fund_name   = funder.get('name')
        fund_id     = funder.get('@id')
        award_num   = funder.get('awardNumber')
        award_title = funder.get('awardTitle')

        if fund_name:
            etree.SubElement(fundingRef, "funderName")._setText(fund_name)

        if fund_id:
            etree.SubElement(fundingRef, "funderIdentifier", funderIdentifierType="Other")._setText(fund_id)

        if award_num:
            etree.SubElement(fundingRef, "awardNumber")._setText(award_num)

        if award_title:
            etree.SubElement(fundingRef, "awardTitle")._setText(award_title)


def parseKeywords(subject_list, subject_xml):
    ''' Update the subject list with split keyword arguments
    '''

    if isinstance(subject_list, str):
        subject_list = subject_list.split(',')

    if isinstance(subject_list, list):
        for sub in subject_list:
           etree.SubElement(subject_xml, "subject")._setText(sub)




############################
#   Convert to JSON-ld     #
#
        #raw_xml = base64.b64decode()
        #if isinstance(raw_xml, str):
        #    xml_formatted = raw_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        #if isinstance(raw_xml, bytes):
        #    xml_formatted = raw_xml.replace(b'<?xml version="1.0" encoding="UTF-8"?>', b'')

        #self.xml = xml_formatted.strip()
        #raw_xml = base64.b64decode()
        #if isinstance(raw_xml, str):
        #    xml_formatted = raw_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        #if isinstance(raw_xml, bytes):
        #    xml_formatted = raw_xml.replace(b'<?xml version="1.0" encoding="UTF-8"?>', b'')
        #self.xml = xml_formatted.strip()
############################

class DoiANVL(object):
    ''' Ark DOI Metadata '''
    def __init__(self, anvl_dict, guid):
        self.guid = guid
        self.anvl = anvl_dict
        self.json_ld = {'@context': 'https://schema.org'}


    def to_json_ld(self):
        self.parseAuthors()
        self.parseIdentifiers()
        self.parseResource()
        return self.json_ld


    def parseIdentifiers(self):
        ark = 'https://n2t.net/'+self.guid
        self.json_ld['@id'] = ark
        identifiers = [ark]

        related = self.anvl.get('datacite.alternateIdentifiers')

        if related is not None:
            for relatedId in related.split(';'):
                if 'ark' in relatedId:
                    identifiers.append('https://n2t.net/'+relatedId)
                else:
                    identifiers.append('https://doi.org/'+relatedId.replace('doi:/',''))

            self.json_ld['identifier'] = identifiers


    def parseAuthors(self):
        creators = self.anvl.get('datacite.creator')

        if len(creators.split(';'))>1:
            # if multipule creators
            authors = []
            for creator in creators.split(';'):

                author = {}
                if len(creator.split(','))==2:
                    author['familyName'], author['givenName'] = creator.split(',')
                    author['@type'] = 'Person'
                    author['name'] = creator

                if len(creator.split(' '))==2:
                    author['givenName'], author['familyName'] = creator.split(' ')
                    author['@type'] = 'Person'
                    author['name'] = creator

                else:
                    author['@type'] = 'Organization'
                    author['name'] = creator

                authors.append(author)

            self.json_ld['author'] = authors

        else:

            author = {}
            if len(creators.split(','))==2:
                author['familyName'], author['givenName'] = creators.split(',')
                author['@type'] = 'Person'
                author['name'] = creators

            if len(creators.split(' '))==2:
                author['givenName'], author['familyName'] = creators.split(',')
                author['@type'] = 'Person'
                author['name'] = creators

            else:
                author['@type'] = 'Organization'
                author['name'] = creators

            self.json_ld['author'] = author


    def parseResource(self):
        self.json_ld['url'] = self.anvl.get('_target')
        self.json_ld['name'] = self.anvl.get('datacite.title')
        self.json_ld['datePublished'] = self.anvl.get('datacite.publicationYear')
        self.json_ld['@type'] = self.anvl.get('datacite.resourceType')



class DoiXML(object):
    ''' Ark XML
    '''
    def __init__(self, raw_xml):
        self.xml_root = etree.fromstring(raw_xml)
        self.json = {}
        self.json_ld = {}


    def parse(self):
        self.prefix = '{'+ self.xml_root.nsmap[None]+ '}'

        self.unpackBasics()
        self.unpackCreators()
        self.unpackFunders()
        self.unpackKeywords()
        self.unpackDescriptions()
        self.unpackRelatedIds()
        self.unpackMedia()
        return self.json_ld


    def unpackBasics(self):
        ''' Fills in essential components of json-ld, looks within xml first then json
        - @context
        - @type
        - @id
        - name
        - version
        - datePublished
        '''
        self.json_ld['@context'] = 'https://schema.org'

        # assign @type based on resource type
        resource_type_xml = self.xml_root.find(self.prefix+'resourceType')
        resource_attrib = None
        if resource_type_xml is not None:
            resource_attrib = resource_type_xml.attrib.get('resourceTypeGeneral')

        types = {'dataset': 'Dataset', 'Collection': 'DataCatalog'}
        if resource_attrib is not None:
            self.json_ld['@type'] = types.get(resource_attrib, resource_attrib)
        elif self.json.get('resource-type-id') is not None:
            self.json_ld['@type'] = types.get(self.json.get('resource-type-id'), self.json.get('resource-type-id'))


        # assign the identifier and format
        identifier = self.xml_root.find(self.prefix+'identifier')
        if identifier is not None:
            if identifier.attrib.get('identifierType') == 'DOI':
                self.json_ld['identifier'] = 'https://doi.org/'+ identifier.text
                self.json_ld['@id'] = 'https://doi.org/'+ identifier.text
            if identifier.attrib.get('identifierType') == 'ARK':
                self.json_ld['identifier'] = 'https://n2t.net/ark:/'+ identifier.text
                self.json_ld['@id'] = 'https://n2t.net/ark:/'+ identifier.text
        else:
            self.json_ld['identifier'] = self.json.get('identifier')
            self.json_ld['@id'] = self.json.get('identifier')

        # parse xml titles
        titles = self.xml_root.find(self.prefix+'titles')
        if titles is not None:
            self.json_ld['name'] = titles.findtext(self.prefix+'title')
        else:
            self.json_ld['name'] = self.json.get('title')

        # version
        version = self.xml_root.findtext(self.prefix+'version')
        if version is not None:
            self.json_ld['version'] = version
        elif self.json.get('version') is not None:
            self.json_ld['version'] = self.json.get('version')

        # datepublished
        datePublished = self.xml_root.findtext(self.prefix+'publicationYear')
        if datePublished is not None:
            self.json_ld['datePublished'] = datePublished
        else:
            self.json_ld['datePublished'] = self.json.get('published')

        # url
        if self.json.get('url') is not None:
            self.json_ld['url'] = self.json.get('url')



    def unpackKeywords(self):
        keywords = self.xml_root.find(self.prefix+'subjects')
        if keywords is not None and keywords.getchildren() is not None:
            self.json_ld['keywords'] = ', '.join([child.text.strip() for child in keywords.getchildren()])


    def unpackCreators(self):
        creators = self.xml_root.find(self.prefix+'creators')
        if creators is not None and creators.getchildren() is not None:
            author_list = []

            for creator in creators.getchildren():
                author = {}
                creator_name = creator.findtext(self.prefix+'creatorName')
                creator_id = creator.findtext(self.prefix+'nameIdentifier')
                creator_type = creator.attrib.get('nameType')

                if creator_name is not None:
                    author['name'] = creator_name
                if creator_id is not None:
                    author['@id'] = creator_id
                if creator_type is not None:
                    author['@type'] = re.sub(r'al$', '', str(creator_type))
                else:
                    author['@type'] = 'Person'

                    #attempt to assign
                    split_name = creator_name.split(' ', 1)
                    if len(split_name) == 2:
                        author['givenName'] = split_name[0]
                        author['familyName'] = split_name[1]

                author_list.append(author)

            if len(author_list)==1:
                self.json_ld['author']=author_list[0]
            else:
                self.json_ld['author']=author_list



    def unpackDescriptions(self):
        descriptions = self.xml_root.find(self.prefix+'descriptions')
        if descriptions is not None:
            tech_description = descriptions.findtext(self.prefix+'description[@descriptionType="TechnicalInfo"]')
            description = descriptions.findtext(self.prefix+'description')
            self.json_ld['description']= description


    def unpackFunders(self):
        funders = self.xml_root.find(self.prefix+'fundingReferences')
        if funders is not None:
            self.json_ld['funder'] = []
            for fundingRef in funders:
                funder_name = fundingRef.findtext(self.prefix+'funderName')
                fund_id = fundingRef.findtext(self.prefix+'funderIdentifier')
                self.json_ld['funder'].append({'name': funder_name, '@type': 'Organization', '@id': fund_id})


    def unpackRelatedIds(self):
        relatedIds = self.xml_root.find(self.prefix+'relatedIdentifiers')
        descriptions = self.xml_root.find(self.prefix+'descriptions')
        dc_name = self.xml_root.findtext(self.prefix + 'descriptions/' + self.prefix + 'description[@descriptionType="SeriesInformation"]')

        if relatedIds is not None:
            for child in relatedIds.getchildren():
                id_type  = child.attrib.get('relatedIdentifierType')
                rel_type = child.attrib.get('relationType')
                if rel_type.lower()=="ispartof":
                    self.json_ld['includedInDataCatalog'] = {
                        '@id': child.text,
                        '@type': 'DataCatalog',
                        'name': dc_name
                    }
                if rel_type.lower()=="isderivedfrom":
                    self.json_ld['isBasedOn'] = child.text


        alternateIds = self.xml_root.find(self.prefix+'alternateIdentifiers')
        if alternateIds is not None:
            for child in alternateIds.getchildren():
                identifier_type = child.attrib.get('alternateIdentifierType')
                identifier = child.text

                # format identifiers into full urls
                if identifier_type == 'DOI':
                    formatted_id = 'https://doi.org/'+identifier
                if identifier_type == 'ARK':
                    formatted_id = 'https://n2t.net/ark:/'+identifier
                else:
                    formatted_id = identifier

                if isinstance(self.json_ld.get('identifier'),list):
                    self.json_ld['identifier'].append(formatted_id)
                elif isinstance(self.json_ld.get('identifier'), str):
                    id_list = [self.json_ld.get('identifier'), formatted_id]
                    self.json_ld['identifier'] = id_list



    def unpackMedia(self):
        media = self.json.get('media')
        if media is not None:
            self.json_ld['contentUrl'] = [ media_elem.get('url') for media_elem in media]
            self.json_ld['fileFormat'] = list(set([media_elem.get('media_type') for media_elem in media]))

        # contentSize
        sizes = self.xml_root.find('{http://datacite.org/schema/kernel-4}sizes')
        if sizes is not None:
            self.json_ld['contentSize'] = sizes.findtext('{http://datacite.org/schema/kernel-4}size')



nameType_xml = {
    'Organization': 'Organizational',
    'Person': 'Personal'
}
nameType_json = {
    'Organizational': 'Organization',
    'Person': 'Personal'
}

xml_header = '<?xml version="1.0" encoding="UTF-8"?>'
properResourceTag ='<resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">'


class DataciteXML(object):
    XmlHeader = '<?xml version="1.0" encoding="UTF-8"?>'
    ProperResourceTag = '<resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">'


    def __init__(self, doi_json):
        self.doi_json = doi_json


    def convert(self):
        doi_json = self.doi_json

        E = objectify.ElementMaker(
            annotate=False
        )

        resource = E.resource()
        resourceType = etree.SubElement(resource, "resourceType", resourceTypeGeneral='Dataset')._setText("XML")


        # add identifiers
        if doi_json.get('@id') is not None:
            identifier = etree.SubElement(resource, "identifier", identifierType="DOI")._setText(doi_json.get('@id').replace('doi:/',''))


        # publicationYear
        if doi_json.get('datePublished') is not None:
            etree.SubElement(resource, "publicationYear")._setText(doi_json.get('datePublished'))

        # publisher
        publisher = doi_json.get('publisher')
        if publisher is not None:
            if isinstance(publisher, dict):
                etree.SubElement(resource, 'publisher')._setText(publisher.get('name'))

            if isinstance(publisher, list) and len(publisher)!=0:
                etree.SubElement(resource, 'publisher')._setText(publisher[0].get('name'))

            if isinstance(publisher, str):
                etree.SubElement(resource, 'publisher')._setText(publisher)





        # add titles
        titles = etree.SubElement(resource, "titles")
        etree.SubElement(titles, "title")._setText(doi_json.get('name'))


        # add a single description of type abstract
        desc = doi_json.get('description')
        descriptions = etree.SubElement(resource, "descriptions")
        if desc is not None:
            etree.SubElement(descriptions, "description", descriptionType="Abstract")._setText(desc)


        # add version
        version = doi_json.get('version')
        if version is not None:
            etree.SubElement(resource, "version")._setText(version)



        # keywords
        subject_list = doi_json.get('keywords')
        if subject_list is not None:
            subjects = etree.SubElement(resource, "subjects")

            if isinstance(subject_list, str):
                subject_list = subject_list.split(',')

            if isinstance(subject_list, list):
                for sub in subject_list:
                   etree.SubElement(subjects, "subject")._setText(sub)


        # add authors
        auth = doi_json.get('author')
        creators = etree.SubElement(resource, "creators")

        if isinstance(auth, dict):
            auth = [auth]

        if isinstance(auth, list):
            c = etree.SubElement(creators, "creator")
            # every author in the list
            for author_elem in auth:
                auth_name = author_elem.get('name')
                etree.SubElement(c, "creatorName")._setText(auth_name)



        # add funders
        funders = doi_json.get('funder')

        if funders is not None:
            funding_reference = etree.SubElement(resource, "fundingReferences")

            if isinstance(funders,dict):
                funders = [funders]

            if isinstance(funders,list):
                for fund_elem in funder:
                    fundingRef = etree.SubElement(funding_reference, "fundingReference")

                    fund_name   = fund_elem.get('name')
                    fund_id     = fund_elem.get('@id')
                    award_num   = fund_elem.get('awardNumber')
                    award_title = fund_elem.get('awardTitle')

                    if fund_name:
                        etree.SubElement(fundingRef, "funderName")._setText(fund_name)

                    if fund_id:
                        etree.SubElement(fundingRef, "funderIdentifier", funderIdentifierType="Other")._setText(fund_id)

                    if award_num:
                        etree.SubElement(fundingRef, "awardNumber")._setText(award_num)

                    if award_title:
                        etree.SubElement(fundingRef, "awardTitle")._setText(award_title)


        # alternateIdentifiers

        # add relatedIdentifiers and Checksums
        relatedIds = {
            'HasPart': doi_json.get('hasPart'),
            'IsPartOf': doi_json.get('isPartOf'),
            'IsDerivedFrom': doi_json.get('isBasedOn'),
            'PredecessorOf': doi_json.get('predeccessorOf'),
            'SuccessorOf': doi_json.get('successorOf'),
            'includedInDataCatalog': doi_json.get('includedInDataCatalog')
            }

        if not all([id_ is None for id_ in relatedIds.values()]):
            related_identifiers = etree.SubElement(resource, "relatedIdentifiers")

            dc = doi_json.get('includedInDataCatalog')
            if dc is not None:
                if isinstance(dc, str):
                    etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                        relationType="IsPartOf")._setText(dc)

                if isinstance(dc, dict):
                    # get identifier of includedInDataCatalog
                    dc_id = dc.get('@id')
                    etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                        relationType="IsPartOf")._setText(dc_id)
                    # add datacatalog name to descriptions
                    dc_name = dc.get('name')
                    etree.SubElement(descriptions, "description", descriptionType="SeriesInformation")._setText(dc_name)

            relatedIds.pop('includedInDataCatalog')
            for key, value in relatedIds.items():
                    if value is not None:
                        if isinstance(value, str):

                            if re.match(r'doi', value):
                                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="DOI",
                                                    relationType=key)._setText(value)
                            else:
                                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                                    relationType=key)._setText(value)

                        if isinstance(value, dict):
                            if re.match(r'doi', value.get('@id')):
                                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="DOI",
                                                    relationType=key)._setText(value.get('@id'))

                            else:
                                etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="URL",
                                                relationType=key)._setText(value.get('@id'))



        xml_string = etree.tostring(resource).decode('utf-8')
        datacite_xml  = xml_header + xml_string.replace('<resource>', properResourceTag)
        return datacite_xml
