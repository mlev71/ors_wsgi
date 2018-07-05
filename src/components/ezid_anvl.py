import re

######################
# JSON OUTPUT HELPERS#
######################

useless_anvl_keys = ['_profile', '_ownergroup', '_target', '_status', '_export', '_updated', '_owner', '_created']


def convertArkToJson(anvl):
    ''' Single process to format json-ld from ANVL - simplifies Get Path
    '''
    # turn anvl text into a dictionary
    anvl_dict = ingestAnvl(anvl)

    # remove all the NIHdc. prefixes from tags and 
    formatted = removeProfileFormat(anvl_dict)

    # recursivly unpack keys into object 
    unpacked = unroll(formatted)

    # format the json-ld keys and return
    return formatJson(unpacked) 



def formatJson(anvl):
    '''Add appropriate @ symbols to important keys
    Used to output json-ld properly
    '''

    # @context
    if anvl.get('context') is not None:
        temp = anvl.pop('context')
        anvl['@context'] = temp
    else:
        anvl['@context'] = "http://schema.org"
    
    # @id
    if anvl.get('id') is not None:
        temp = anvl.pop('id')
        anvl['@id'] = temp

    
    # @type
    if anvl.get('type') is not None:
        temp = anvl.pop('type')
        anvl['@type'] = temp
    else:
        anvl['@type'] = 'Dataset'

    # remove uninformative ez keys
    init_keys = anvl.keys()

    for useless_key in useless_anvl_keys:
        if useless_key in anvl.keys():
            anvl.pop(useless_key, None)


    return anvl


def removeProfileFormat(anvlDict):
    '''Remove NIHdc from every key
    '''
    output = {}
    for key, value in anvlDict.items():
        key = re.sub("NIHdc.", "", key)
        output[key] = value
    return output


def unroll(anvl):
    output = {}
    temp_dict = {}
    conflicted_input_keys = set()
    
    for key, value in anvl.items():
        if len(key.rsplit(".") )==2:
            root_key, sub_key = key.rsplit(".")
            
            # if the key already exists in the input
            if root_key in anvl.keys():
                if root_key in anvl.keys():
                    conflicted_input_keys.add(root_key)
                    
                if temp_dict.get(root_key) == None:
                    temp_dict[root_key] = {sub_key: value}
                    
                else:
                    update = {sub_key: value}
                    temp_dict.get(root_key).update(update)
            
            else:
                # insert a key
                if output.get(root_key) == None:
                    output[root_key] = {sub_key: value}
                # if the key already exists update with new values
                else:
                    output[root_key].update({sub_key:value})
        else:
            output[key]=value

    for con_key in conflicted_input_keys:
        # coerce to list 
        output[con_key]= [output[con_key], temp_dict.get(con_key)]
        
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
