# Despliegue en Railway (Docker + Gunicorn)

El proyecto está preparado para desplegar **backend y frontend en la misma instancia** usando un único contenedor con **Gunicorn** sirviendo Django directamente en el puerto público de Railway. Los archivos estáticos se sirven con **WhiteNoise**.

## Requisitos

- Cuenta en [Railway](https://railway.app)
- Repo en GitHub (o similar) conectado a Railway

## Pasos en Railway

1. **Nuevo proyecto** → Deploy from GitHub → selecciona este repo.

2. **Root directory**: deja el directorio raíz del repo (donde está el `Dockerfile`).

3. **Build**: Railway detectará el `Dockerfile` y construirá la imagen.

4. **Variables de entorno** (en el dashboard del servicio):
  - Configura MySQL con alguna de estas opciones:
    - `DATABASE_URL` con formato MySQL, por ejemplo: `mysql://usuario:clave@host:3306/basedatos`
    - o variables separadas: `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`
   - Opcionales:
     - `DJANGO_ADMIN_USER` (default: `admin1`)
     - `DJANGO_ADMIN_PASSWORD` (default: `123456`)
     - `DJANGO_ADMIN_EMAIL` (default: `admin@example.com`)
     - `ALLOWED_HOSTS`: lista separada por comas si necesitas dominios extra.
     - `CSRF_TRUSTED_ORIGINS`: lista separada por comas, ej. `https://tudominio.com`
     - `SECRET_KEY`: clave secreta Django (recomendado en producción).
     - `DEBUG`: `False` en producción (recomendado).

5. **Puerto**: Railway asigna `PORT` automáticamente; el entrypoint hace que Gunicorn escuche directamente en ese puerto.

6. **Deploy**: tras el build, Railway ejecuta el contenedor. En el arranque se ejecutan migraciones, `collectstatic`, creación de grupos y usuario admin por defecto si no hay usuarios.

## Estructura del contenedor

- **Gunicorn**: sirve la app Django en `0.0.0.0:$PORT`.
- **WhiteNoise**: sirve archivos estáticos desde Django.
- El entrypoint ejecuta migraciones con reintentos, `collectstatic`, configuración base de grupos/usuario admin y luego deja Gunicorn en primer plano.

## Probar en local con Docker

```bash
# Desde la raíz del repo (donde está el Dockerfile)
docker build -t pantalla-app .
docker run -p 8000:8000 -e PORT=8000 pantalla-app
```

Abre `http://localhost:8000`.

## Notas

- **Media (subidas)**: en Railway el disco es efímero. Para persistir archivos subidos usa un almacenamiento externo (S3, etc.) y configura Django para ello.
- **MySQL**: usa un servicio gestionado (Railway, PlanetScale, Aiven, etc.) y configura `DATABASE_URL` o `MYSQL_*`.
