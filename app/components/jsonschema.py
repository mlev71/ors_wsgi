from jsonschema import validate

dataguid_schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Dataguid'
    'additionalProperties': False,
    'description': 'Create a new index from hash & size',
    'properties': {
        'acl': {'items': {'type': 'string'}, 'type': 'array'},
        'baseid': {
            'pattern': '^.*[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            'type': 'string'
        },
        'did': {
            'pattern': '^.*[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            'type': 'string'
        },
        'file_name': {
            'description': 'optional file name of the object',
            'type': 'string'
        },
        'form': {
            'enum': ['object','container', 'multipart']
        },
        'hashes': {
            'anyOf': [{'required': ['md5']},
                      {'required': ['sha1']},
                      {'required': ['sha256']},
                      {'required': ['sha512']},
                     {'required': ['crc']},
                     {'required': ['etag']}],
           'properties': {'crc': {'pattern': '^[0-9a-f]{8}$',
                                  'type': 'string'},
                          'etag': {'pattern': '^[0-9a-f]{32}(-\\d+)?$',
                                   'type': 'string'},
                          'md5': {'pattern': '^[0-9a-f]{32}$',
                                  'type': 'string'},
                          'sha1': {'pattern': '^[0-9a-f]{40}$',
                                   'type': 'string'},
                          'sha256': {'pattern': '^[0-9a-f]{64}$',
                                     'type': 'string'},
                          'sha512': {'pattern': '^[0-9a-f]{128}$',
                                     'type': 'string'}},
                   'type': 'object'},
        'metadata': {'description': 'optional metadata of the object',
                     'type': 'object'},
        'size': {'description': 'Size of the data being indexed in bytes',
                 'minimum': 0,
                 'type': 'integer'},
        'urls': {'items': {'type': 'string'},
                 'type': 'array'},
        'urls_metadata': {'description': 'optional urls metadata of the object',
                          'type': 'object'},
        'version': {'description': 'optional version string of the object',
                    'type': 'string'}
    },
    'required': ['size', 'hashes', 'urls', 'form'],
    'type': 'object'}

dg_schema_org = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'ORS Dataguid',
    'additionalProperties': False,
    'description': 'Schema.org Format of a Dataguid',
    '@context': {'enum': ['https://schema.org']},
    '@type': {'enum': ['Dataset', 'DataCatalog', 'CreativeWork']},
    '@id': {
            'pattern': '^.*[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
            'type': 'string'
        },
    'identifier': {
        'type': 'array',
        'uniqueItems': True,
        'items':
            {'anyOf': [
                {'type': 'object', 'properties': {
                    "@value": {'type': 'string'},
                    "@type": {'enum': ['PropertyValue']},
                    "name": {'enum': ['md5', 'sha', 'sha256', 'sha512', 'crc', 'etag']}
                }
            },
            {'type': 'string', 'pattern': '^.*[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'}
        ]}
    },
    'url': {'type': 'string', 'format': 'uri'},
    'name': {'type':'string'},
    'contentUrl': {'type': 'array', 'items': {'type':'string', 'format': 'uri'}},
    'version': {'type':'string'},
    'contentSize': {'type': 'integer', 'exclusiveMinimum': 0},
    'author': {'oneOf': [
        {'type': 'object', 'properties':{
            '@type': {'type': 'string'},
            'name': {'type': 'string'}
        }},
        {'type': 'string'},
        {'type': 'array', 'items': {'anyOf': [
            {'type': 'object',
             'properties':{
                '@type': {'type': 'string'},
                'name': {'type': 'string'}}
            },
            {'type': 'string'}
        ]}}
    ]},
    'required': ['contentUrl', 'identifier', 'contentSize']
}
