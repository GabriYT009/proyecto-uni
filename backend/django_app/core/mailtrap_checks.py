import os

import requests
from django.conf import settings
from django.core import checks


def _mailtrap_validation_enabled() -> bool:
    return os.environ.get('MAILTRAP_VALIDATE_ON_STARTUP', 'True').strip().lower() in ('1', 'true', 'yes')


def _is_runserver_main_process() -> bool:
    return os.environ.get('RUN_MAIN', '').strip().lower() == 'true'


@checks.register(checks.Tags.security)
def check_mailtrap_configuration(app_configs, **kwargs):
    if not _mailtrap_validation_enabled():
        return []

    if not _is_runserver_main_process():
        return []

    token = os.environ.get('MAILTRAP_API_TOKEN', '').strip()
    if not token:
        return [checks.Warning(
            'MAILTRAP_API_TOKEN no está configurado.',
            id='mailtrap.W001',
        )]

    placeholder_tokens = ('pon_aqui_', 'tu_token', 'example', 'changeme')
    if any(token.lower().startswith(prefix) for prefix in placeholder_tokens):
        return [checks.Warning(
            'MAILTRAP_API_TOKEN sigue siendo un placeholder. Sustitúyelo por el token real de Mailtrap.',
            id='mailtrap.W005',
        )]

    host = os.environ.get('MAILTRAP_API_HOST', 'https://send.api.mailtrap.io').strip().rstrip('/')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')

    payload = {
        'from': {'email': from_email},
        'to': [{'email': from_email}],
        'subject': 'Mailtrap startup check',
        'text': 'This is a startup validation request.',
    }

    try:
        response = requests.post(
            f'{host}/api/send',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=10,
        )
    except requests.RequestException as exc:
        return [checks.Warning(
            f'No se pudo validar Mailtrap al arrancar: {exc}',
            id='mailtrap.W002',
        )]

    if response.status_code == 401:
        return [checks.Warning(
            'MAILTRAP_API_TOKEN no es válido o no tiene permiso para enviar correos.',
            id='mailtrap.W003',
        )]

    if response.status_code >= 400:
        return [checks.Warning(
            f'Mailtrap devolvió un estado inesperado al arrancar: {response.status_code}',
            id='mailtrap.W004',
        )]

    return []