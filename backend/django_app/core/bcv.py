import requests


def obtener_tasa_cambio():
    URL= "https://api.dolarvzla.com/public/bcv/exchange-rate"
    MI_API_KEY= "e76421c6acdd43d60e5a8b01496517028fd712381d17f6785ad6b0c2ab8b2db9"
    HEADERS = {"x-dolarvzla-key": MI_API_KEY}

    response = requests.get(URL,headers=HEADERS)
    datos= response.json()
    return datos['current']['usd']


