import json
import requests
from commonTestObjects import *

ADDR = "http://localhost:8080"
putURL = ADDR + '/mint'
getURL = ADDR + '/ark:/99999/fk4r8776t'

BasicAuth = requests.auth.HTTPBasicAuth('apitest', 'apitest')
JSON = minidJSON


response = requests.delete(getURL, auth=BasicAuth)
print(response.content)

response = requests.put(putURL, auth=BasicAuth, data=json.dumps(JSON))
print(response.content) 

exists = requests.get(getURL)
print(exists.content)

response = requests.delete(getURL, auth=BasicAuth)
print(response.content)

