from lxml import objectify, etree
import re


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
        E.identifier(doi_json.get('@id'), identifierType="DOI"),     
        E.publicationYear(doi_json.get('datePublished')),
        E.resourceType(doi_json.get('@type'), resourceTypeGeneral='Dataset')
    )
    
    # add titles
    titles = etree.SubElement(resource, "titles")
    etree.SubElement(titles, "title")._setText(doi_json.get('name'))
    
    
    # get the author
    auth = doi_json.get('author')
    if auth is not None:
        parseAuthors(auth, resource)


    # add included in data catalog
    dc = doi_json.get('includedInDataCatalog')
    related_identifiers = etree.SubElement(resource, "relatedIdentifiers")
    if isinstance(dc, str):
        etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="DOI",
                            relationType="IsPartOf")._setText(dc)
    
    if isinstance(dc, dict):
        # get identifier of includedInDataCatalog
        dc_id = dc.get('@id')
        etree.SubElement(related_identifiers, "relatedIdentifier", relatedIdentifierType="DOI",
                            relationType="IsPartOf")._setText(dc_id)
    
    # Version
    version = doi_json.get('version')
    if version is not None:
        etree.SubElement(resource, "version")._setText(version)
    
    # add a single description of type abstract
    desc = doi_json.get('description')
    if desc is not None:
        descriptions = etree.SubElement(resource, "descriptions")
        etree.SubElement(descriptions, "description", descriptionType="Abstract")._setText(desc)
     
    
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
############################


def convertDoiToJson(doiXml):
    ''' Feed in a Doi string of XML return a dictionary of JSON-LD
    '''
  
    # preform string formatting
    xmlFormatted = doiXml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
    xmlFormatted = re.sub("%0A", "", xmlFormatted)
    xmlFormatted = xmlFormatted.strip()
    
    # return initial dictionary 
    unpackedDoi  = unpack_xml(etree.fromstring(xmlFormatted) ) 
    
    # format the keys to conform with JSON-LD
    renamedDoi = rename(unpackedDoi)
   
    return renamedDoi


def unpackSubjects(subjElem):
    subj_list = []
    for sub in subjElem.getchildren():
        subj_list.append(sub.text.strip())
    return ', '.join(subj_list)

def unpackCreators(creatorsElem):
    creator_list = []
    for creator in creatorsElem.getchildren():

        # attempt to unpack all the elements of a creator
        creator_obj = {}

        # name 
        creator_name = creator.findtext('{http://datacite.org/schema/kernel-4}creatorName')
        if creator_name is not None:
            creator_obj.update({'name': creator_name})

        # id
        creator_id = creator.findtext('{http://datacite.org/schema/kernel-4}nameIdentifier')
        if creator_id is not None:
            creator_obj.update({'@id': creator_id})

        if creator.attrib.get('nameType') == "Organizational":
            creator_obj['@type'] = 'Organization'
            
        if creator.attrib.get('nameType') == "Personal":
            creator_obj['@type'] = 'Person'

        # other keys 
        # familyName
        #givenName
        #affiliation


        creator_list.append(creator_obj)

    if len(creator_list)==1:
        return creator_list[0]
    else:
        return creator_list


def unpackFunders(fundingReferences):
    fund_list = []
    for fundingRef in fundingReferences:
        fund_obj = {}

        fund_name = fundingRef.findtext('{http://datacite.org/schema/kernel-4}funderName')
        if fund_name is not None:
            fund_obj.update({'name': fund_name, '@type': 'Organization'})

        fund_id = fundingRef.findtext('{http://datacite.org/schema/kernel-4}funderIdentifier')
        if fund_name is not None:
            fund_obj.update({'@id': fund_id})
                    
        fund_list.append(fund_obj)

    if len(fund_list)==1:
        return fund_list[0]
    else:
        return fund_list
                    

def parseIds(relatedIds):
    ''' Parse XML for related Ids
    '''
  
    id_obj = {} 
    contentUrl = []

    for child in relatedIds.getchildren():
        
        id_type  = child.attrib.get('relatedIdentifierType')
        rel_type = child.attrib.get('relationType')

        if rel_type=="IsDocumentedBy" and id_type=="URL":
            id_obj['url'] = child.text

        if rel_type=="IsPartOf" and (id_type=="DOI" or id_type=="ARK"):
            id_obj['includedInDataCatalog'] = child.text

        if rel_type=="HasMetadata" and id_type=="URL":
            contentUrl.append(child.text) 

    if len(contentUrl)!=0:
        id_obj['contentUrl'] = contentUrl

    return id_obj


def unpack_xml(input_root):
    xml_dict = {}

    xml_dict['@context'] = 'https://schema.org'

    identifier = input_root.find('{http://datacite.org/schema/kernel-4}identifier')
    if identifier is not None:
        xml_dict['identifier'] = identifier
        xml_dict['@id'] = identifier

    keywords = input_root.find('{http://datacite.org/schema/kernel-4}subjects')
    if keywords is not None:
        xml_dict['keywords'] = unpackSubjects(keywords)

    creators = input_root.find('{http://datacite.org/schema/kernel-4}creators')
    if creators is not None:
        xml_dict['author'] = unpackCreators(creators)

    descriptions = input_root.find('{http://datacite.org/schema/kernel-4}descriptions')
    if descriptions is not None:
        xml_dict['description']=descriptions.findtext('{http://datacite.org/schema/kernel-4}description')

    funders = input_root.find('{http://datacite.org/schema/kernel-4}fundingReferences')
    if funders is not None:
        xml_dict['funder'] = unpackFunders(funders)


    resourceType = input_root.findtext('{http://datacite.org/schema/kernel-4}resourceType')
    if resourceType is not None:
        xml_dict['@type'] = resourceType
 
    # url and includedInDataCatalog
    relatedId = input_root.find('{http://datacite.org/schema/kernel-4}relatedIdentifiers')
    parsedIds = parseIds(relatedId)

    xml_dict.update(parsedIds)

    # name from title
    titles = input_root.find('{http://datacite.org/schema/kernel-4}titles')

    if titles is not None:
        name = titles.findtext('{http://datacite.org/schema/kernel-4}title')
        xml_dict['name'] = name

    # version
    version = input_root.findtext('{http://datacite.org/schema/kernel-4}version')
    if version is not None:
        xml_dict['version'] = version

    # datepublished
    datePublished = input_root.findtext('{http://datacite.org/schema/kernel-4}publicationYear')
    if datePublished is not None:
        xml_dict['datePublished'] = datePublished



    return xml_dict


# Keys to rename for xml converted to json-ld
renamedKeys = {
    'FundingReference': "funder",
    'funderName': 'name',
    'Identifier': 'identifier',
    'PublicationYear': 'datePublished',
    'RelatedIdentifier': 'url', # should be object full of stuff but ok
    'Subjects': 'keywords',
    'Title': 'title',
    'Version': 'version',
    'creators': 'author',
}


def rename(almost_json):
    ''' Convert Key and Value names to conform with schema.org
    '''
    final = {}
    for key, value in almost_json.items():        
        if key == '@type':
            value = nameType_json.get(value, value) 
        new_key = renamedKeys.get(key,key)
        if isinstance(value,str): 
            final[new_key] = value    
        if isinstance(value,list):        
            final[new_key] = [rename(elem) if isinstance(elem,dict) else elem for elem in value ]
        if isinstance(value, dict):
            final[new_key] = rename(value) 
    return final
    

