import requests


def obtener_tasa_cambio():
    URL= "https://api.dolarvzla.com/public/bcv/exchange-rate"
    MI_API_KEY= "eeb48306e200fe4256ad51f5bdf6e2cbd52dc6aab667b46a5c54b02be2332881"
    HEADERS = {"x-dolarvzla-key": MI_API_KEY}

    response = requests.get(URL,headers=HEADERS)
    datos= response.json()
    return datos['current']['usd']


