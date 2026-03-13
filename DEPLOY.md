# Despliegue en Railway (Docker + Nginx)

El proyecto está preparado para desplegar **backend y frontend en la misma instancia** usando un único contenedor con **Nginx** (reverse proxy y estáticos) y **Gunicorn** (Django).

## Requisitos

- Cuenta en [Railway](https://railway.app)
- Repo en GitHub (o similar) conectado a Railway

## Pasos en Railway

1. **Nuevo proyecto** → Deploy from GitHub → selecciona este repo.

2. **Root directory**: deja el directorio raíz del repo (donde está el `Dockerfile`).

3. **Build**: Railway detectará el `Dockerfile` y construirá la imagen.

4. **Variables de entorno** (en el dashboard del servicio):
   - `DATABASE_URL`: si añades un plugin PostgreSQL en Railway, se inyecta solo. Si no, la app usa SQLite (datos efímeros en el contenedor).
   - Opcionales:
     - `DJANGO_ADMIN_USER` (default: `admin1`)
     - `DJANGO_ADMIN_PASSWORD` (default: `123456`)
     - `DJANGO_ADMIN_EMAIL` (default: `admin@example.com`)
     - `ALLOWED_HOSTS`: lista separada por comas si necesitas dominios extra.
     - `CSRF_TRUSTED_ORIGINS`: lista separada por comas, ej. `https://tudominio.com`
     - `SECRET_KEY`: clave secreta Django (recomendado en producción).
     - `DEBUG`: `False` en producción (recomendado).

5. **Puerto**: Railway asigna `PORT` automáticamente; el entrypoint hace que Nginx escuche en ese puerto.

6. **Deploy**: tras el build, Railway ejecuta el contenedor. En el arranque se ejecutan migraciones, `collectstatic`, creación de grupos y usuario admin por defecto si no hay usuarios.

## Estructura del contenedor

- **Nginx**: escucha en `$PORT`, sirve `/static/` y `/media/`, y hace proxy del resto a Gunicorn.
- **Gunicorn**: sirve la app Django en `127.0.0.1:8000`.
- Todo en un solo proceso (entrypoint inicia Gunicorn en segundo plano y Nginx en primer plano).

## Probar en local con Docker

```bash
# Desde la raíz del repo (donde está el Dockerfile)
docker build -t pantalla-app .
docker run -p 8000:8000 -e PORT=8000 pantalla-app
```

Abre `http://localhost:8000`.

## Notas

- **Media (subidas)**: en Railway el disco es efímero. Para persistir archivos subidos usa un almacenamiento externo (S3, etc.) y configura Django para ello.
- **PostgreSQL**: recomendable en producción; añade el plugin PostgreSQL en Railway y usa la `DATABASE_URL` que te proporciona.
