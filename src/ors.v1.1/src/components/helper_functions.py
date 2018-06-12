import re

######################
# JSON OUTPUT HELPERS#
######################

def formatJson(anvl):
    '''Add appropriate @ symbols to important keys
    Used to output json-ld properly
    '''
    print(anvl)

    # @context
    #temp = anvl.pop('context')
    anvl['@context'] = "http://schema.org"
    
    # @id
    temp = anvl.pop('id')
    anvl['@id'] = temp
    
    # @type
    temp = anvl.pop('type')
    anvl['@type'] = temp
    
    return anvl

def removeProfileFormat(anvlDict):
    '''Remove NIHdc from every key
    '''
    output = {}
    for key, value in anvlDict.items():
        key = re.sub("NIHdc.", "", key)
        output[key] = value
    return output

def unpack(anvl):
    ''' Splits a flatten anvl doc into a nested json object

    Used to read in anvl and translate to json
    '''
    output = {}
    for key, value in anvl.items():
        if len(key.split(".", 1))==2:
            split_key, split_val = key.split(".", 1)
            output[split_key] = {split_val:value}
        else:
            output[key]=value
    return output

def recursiveUnpack(anvl):
    ''' Unpacks until all the keys have no subkeys
    '''
    output = anvl
    while all([len(key.split(".",1))==1 for key, value in output.items()])==False:
        output = unpack(output)
    return output


######################
# ANVL OUTPUT HELPERS#
######################


def profileFormat(anvlDict):
     '''Add NIHdc to every tag
     '''
     output = {}
     for key, value in anvlDict.items():
        key = ".".join(["NIHdc", key])
        output[key] = value
     return output

def flatten(anvlDict):
    output = {}
    if isinstance(anvlDict, dict):
        for key, value in anvlDict.items():
            key = re.sub("@","", key)
            if isinstance(value, dict):
                for subKey, subValue in value.items():
                    key = ".".join([key, subKey])
                    output[key] =subValue

            if isinstance(value, str):
                 output[key] = value

            if isinstance(value, list):

                # if a list of strings
                if all([isinstance(el, str) for el in value]):
                    output[key] = ";".join(value)
                if any([isinstance(el, dict) for el in value]):
                    for item in value:
                        output[key] = flatten(item)
        return output
    if isinstance(anvlDict, str):
        return anvlDict

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
