import re

######################
# JSON OUTPUT HELPERS#
######################

useless_anvl_keys = ['success', '_profile', '_ownergroup', '_target', '_status', '_export', '_updated', '_owner', '_created']



restricted_keys = {
        'id': '@id',
        'type': '@type',
        'context': '@context',
        'value': '@value'

        }


def unroll(anvl):

    # determine object keys
    unique_root_keys = set([key.split('.')[0] for key in anvl.keys() if len(key.split('.')) ==2 ])

    # add all string values
    output = {key: value.split(';') for key,value in anvl.items() if len(key.split('.'))==1 and isinstance(value, str)}

    # create objects for every unique_root_key
    # ('author', {'name': 'max;other',...} )
    objects = [ (unique_key, {restricted_keys.get(anvl_key.split('.')[1], anvl_key.split('.')[1]): anvl_value 
        for anvl_key, anvl_value in anvl.items() 
        if len(anvl_key.split('.')) == 2 and anvl_key.split('.')[0] == unique_key})
        for unique_key in unique_root_keys]

    for object_elem in objects:
        key = object_elem[0]
        merged = object_elem[1]

        split = [{key: value.split(';')[i] for key,value in merged.items()} 
                for i in range(len(list(merged.values())[0].split(';'))) ]

        if isinstance(output.get(key), str):
            output[key] = [output[key] ] + split


        elif isinstance(output.get(key), list):
            output[key] = output[key] + split

        elif output.get(key) is None:
            output[key] = split

    for key,value in output.items():
        if isinstance(value, list) and len(value)==1:
            output[key]=value[0]

    return output





######################
# ANVL OUTPUT HELPERS#
######################


def profileFormat(anvlDict):
     '''Add NIHdc to every tag, remove @ symbols
     '''
     output = {}
     for key, value in anvlDict.items():
        key = re.sub("@","",key)
        key = ".".join(["NIHdc", key])
        output[key] = value
     return output



def flatten(anvlDict):
    output = {}
    
    for key, value in anvlDict.items():
        
        if isinstance(value, dict):
            for subKey, subValue in value.items():
                joined_key = ".".join([key,subKey])
                output[joined_key] = subValue
            
        if isinstance(value, str):
            output[key] = value

        if isinstance(value, list):
            output[key] = ";".join([string_elem for string_elem in value if isinstance(string_elem, str)])
            
            # add another key if there is a dictionary inside the list
            for dict_elem in value:
                if isinstance(dict_elem, dict):
                    for subKey, subValue in dict_elem.items():
                        joined_key = ".".join([key, subKey])
                        output[joined_key] = subValue
    
    return output


def recursiveFlatten(nestedAnvl):
    output = nestedAnvl
    while all([ isinstance(value, dict)==False for value in output.values()])==False:
        output = flatten(output)
    return output


##################
# Format Text    #
##################

def escape(s):
    return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)

def ingestAnvl(anvl):
    anvlDict = {}
    for element in anvl.split('\n'):
        split_element = str(element).split(': ', 1)
        if len(split_element)==2:
            anvlDict[split_element[0]] = split_element[1]
    return anvlDict


def outputAnvl(anvlDict):
    ''' Encode all objects into strings, lists into strings
    '''
    return "\n".join("%s: %s" % (escape(str(name)), escape(str(value) )) for name,value in anvlDict.items()).encode('utf-8')
