import requests


def obtener_tasa_cambio():
    URL= "https://api.dolarvzla.com/public/bcv/exchange-rate"
    MI_API_KEY= "eeb48306e200fe4256ad51f5bdf6e2cbd52dc6aab667b46a5c54b02be2332881"
    HEADERS = {"x-dolarvzla-key": MI_API_KEY}

    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        datos = response.json()
        tasa = datos.get('current', {}).get('usd')
        if tasa:
            return tasa
    except Exception:
        pass

    try:
        from .models import Bcv
        ultimo = Bcv.objects.order_by('-id').first()
        if ultimo and ultimo.precio_actual:
            return ultimo.precio_actual
    except Exception:
        pass

    return 'N/A'


