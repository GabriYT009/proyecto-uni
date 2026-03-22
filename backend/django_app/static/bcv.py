import requests

URL= "https://ve.dolarapi.com/v1/dolares/oficial"

response = requests.get(URL)
datos= response.json()