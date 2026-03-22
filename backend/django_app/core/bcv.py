import requests


def obtener_tasa_cambio():
    URL= "https://api.dolarvzla.com/public/bcv/exchange-rate"
    MI_API_KEY= "2cd88fbe8131d0bb68990eac5e21757528a27aaabda4019fa29b8c43ee9da02e"
    HEADERS = {"x-dolarvzla-key": MI_API_KEY}

    response = requests.get(URL,headers=HEADERS)
    datos= response.json()
    return datos['current']['usd']


