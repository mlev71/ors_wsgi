from django.shortcuts import render
from django.template import Context, Template

from flask import Response, render_template
import json

from jinja2
jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('app','templates')
    )


def ArkResponseFactory(anvl, guid):
    if anvl.get('_profile')=='erc':
        return ERCResponse(anvl, guid)

    if anvl.get('_profile')=='dc':
        return DublinCoreResponse(anvl, guid)

    if anvl.get('_profile')=='datacite':
        return DataciteResponse(anvl, guid)

    if anvl.get('_profile')=='schema_org':
        return SchemaOrgResponse(anvl, guid)


class ArkResponse(object):
    def render_html(self, request):
        return render(request, self.template_name, self.json_ld)

    def render_json(self):
        return Response(
            response = json.dumps(self.json_ld),
            mimetype= 'application/ld+json'
        )


class SchemaOrgResponse(ArkResponse):
    template_name = 'Ark/schema_org.html'

    def __init__(self, anvl, guid):
        json_ld = format_dict(anvl.get('schema_org'))
        json_ld['@id'] = guid
        self.json_ld = json_ld


class ERCResponse(ArkResponse):
    template_name = 'ark/erc.html'

    def __init__(self, anvl, guid):
        json_ld = {
                    '@id': guid,
                    'identifier': [guid],
                    '@context': 'https://schema.org',
                    'url': anvl.get('_target')
                    }


        if anvl.get('erc') is None:
            # Trim off 'erc.' prefix from all keys
            erc_dict = { key.replace('erc.',''): val for key,val in anvl.items() if 'erc.' in key}

        else:
            # Split compressed element into a dictionary
            erc_lines = anvl.get('erc').split('\n')
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

        self.json_ld = json_ld


class DublinCoreResponse(ArkResponse):
    template_name = 'ark/dc.html'

    def __init__(self, anvl, guid):
        json_ld = { re.sub('dc.', '', key): value for key, value in anvl.items() if 'dc.' in key}
        json_ld['@type'] = anvl.get('dc.type')
        json_ld['@context'] = 'http://purl.org/dc/elements/1.1/'
        json_ld['@id'] = 'https://n2t.net/'+guid
        json_ld['identifier'] = 'https://n2t.net/'+guid

        self.json_ld = json_ld


class DataciteResponse(ArkResponse):
    template_name = 'ark/datacite.html'

    def __init__(self, anvl, guid):
        if anvl.get('datacite') is not None:
            # parse xml
            #json_ld = parseDataciteXML(anvl, guid)
            json_ld = {
                '@id': guid
            }
        else:
            # parse anvl
            ark = guid
            json_ld = {
                '@id': guid,
                '@type': anvl.get('datacite.resourceType'),
                '@context': 'https://schema.org',
                'identifier':  [relID for relID in
                                anvl.get('datacite.alternateIdentifiers').split(';')].append(ark),
                'author': [{'@type': 'Person', 'name': creator} for
                           creator in anvl.get('datacite.creator').split(';')],
                'url': anvl.get('_target'),
                'name': anvl.get('datacite.title'),
                'datePublished': anvl.get('datacite.publicationYear')
            }


        self.json_ld = json_ld

def format_dict(anvl):
    anvl = re.sub(r'^{|}$', '', anvl)
    return  dict(tuple(v.strip().replace("'", "") for v in l.split(":", 1)) \
  for l in anvl.split(','))
