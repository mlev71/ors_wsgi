import requests

exDoi = "/10.25491/sx2w-0730"


response = requests.get(
        url = "https://api.datacite.org/works" + exDoi
        )

print(response.content)
