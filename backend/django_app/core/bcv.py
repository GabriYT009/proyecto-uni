import re

import requests
from django.utils import timezone
import requests

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    BeautifulSoup = None
    _HAS_BS4 = False

BCV_FALLBACK_RATE = 0


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
    MI_API_KEY = "087793a06ad3aa94d54fa14af1797a04997d94362defae31f19eb9cbde43f47d"
    
    # Headers para simular navegador (evita bloqueos 403)
    HEADERS_NAV = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # --- INTENTO 1: Scraping Directo al BCV con BeautifulSoup ---
    try:
        if _HAS_BS4:
            response = requests.get(URL_OFICIAL, headers=HEADERS_NAV, timeout=15, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            block_dolar = soup.find('div', id='dolar')
            
            if block_dolar:
                tasa_texto = block_dolar.find('strong').text.strip()
                # Limpiamos el formato: "36,12" -> "36.12"
                tasa = float(tasa_texto.replace('.', '').replace(',', '.'))
                if tasa > 0:
                    _persist_rate(tasa)
                    print(f"Tasa obtenida por Scraping BCV: {tasa}")
                    return tasa
        else:
            # bs4 no está instalado; omitir paso de scraping
            pass
    except Exception as e:
        print(f"Error en Scraping BCV: {e}") # Opcional: logging

    # --- INTENTO 2: API Externa de Respaldo ---
    try:
        headers_api = {"x-dolarvzla-key": MI_API_KEY}
        response = requests.get(URL_API, headers=headers_api, timeout=10)
        response.raise_for_status()
        datos = response.json()
        tasa = datos.get('current', {}).get('usd')
        if tasa:
            tasa = float(tasa)
            _persist_rate(tasa)
            return tasa
    except Exception as e:
        print(f"Error en API Respaldo: {e}")

    # --- INTENTO 3: Último valor guardado en Base de Datos ---
    try:
        from .models import Bcv
        ultimo = Bcv.objects.order_by('-id').first()
        if ultimo and ultimo.precio_actual:
            return ultimo.precio_actual
    except Exception:
        pass

    # --- FALLBACK FINAL: Valor estático ---
    _persist_rate(BCV_FALLBACK_RATE)
    return BCV_FALLBACK_RATE

