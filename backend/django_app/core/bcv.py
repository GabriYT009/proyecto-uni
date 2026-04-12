import re

import requests
from django.utils import timezone


BCV_FALLBACK_RATE = 475.0083


def _persist_rate(rate):
    try:
        from .models import Bcv

        latest = Bcv.objects.order_by('-id').first()
        if latest:
            latest.precio_actual = rate
            latest.fecha = timezone.now()
            latest.save(update_fields=['precio_actual', 'fecha'])
        else:
            Bcv.objects.create(precio_actual=rate, fecha=timezone.now())
    except Exception:
        pass


def obtener_tasa_cambio():
    URL_OFICIAL = "https://www.bcv.org.ve/"
    URL_API = "https://api.dolarvzla.com/public/bcv/exchange-rate"
    MI_API_KEY = "e844224cbd000e3c6f4f3d89f0d9e67e0389984d88d765fbbb25ef1b3910fbd0"
    HEADERS = {"x-dolarvzla-key": MI_API_KEY}

    try:
        response = requests.get(URL_OFICIAL, timeout=15)
        response.raise_for_status()
        html = response.text
        match = re.search(r'USD\s*([0-9]{1,3}(?:[.,][0-9]{1,10})?)', html, re.IGNORECASE)
        if match:
            tasa_texto = match.group(1).replace('.', '').replace(',', '.')
            tasa = float(tasa_texto)
            if tasa > 0:
                _persist_rate(tasa)
                return tasa
    except Exception:
        pass

    try:
        response = requests.get(URL_API, headers=HEADERS, timeout=10)
        response.raise_for_status()
        datos = response.json()
        tasa = datos.get('current', {}).get('usd')
        if tasa:
            tasa = float(tasa)
            _persist_rate(tasa)
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

    _persist_rate(BCV_FALLBACK_RATE)
    return BCV_FALLBACK_RATE


