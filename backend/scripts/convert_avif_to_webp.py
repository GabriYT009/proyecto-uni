from PIL import Image, ImageOps, UnidentifiedImageError
from pathlib import Path
from django.conf import settings
import django
import sys
import shutil

# Setup Django environment
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
try:
    django.setup()
except Exception as e:
    print('Django setup failed:', e)

from django.db import transaction
from ...django_app.core.models import Producto, SolicitudSublimacion, Nota_Entrega

root = Path(__file__).resolve().parents[1]
media_root = root / 'django_app' / 'media'
frontend_static = Path(root).parents[1] / 'frontend' / 'static' / 'product-images'

files = []
if media_root.exists():
    files.extend(media_root.rglob('*.avif'))
if frontend_static.exists():
    files.extend(frontend_static.rglob('*.avif'))

print('Found', len(files), 'AVIF files')

for p in files:
    try:
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            new_path = p.with_suffix('.webp')
            img.save(str(new_path), format='WEBP', quality=80, method=6)
            print('Converted', p, '->', new_path)
            # remove original
            try:
                p.unlink()
            except Exception:
                pass
            # Update DB references if under media_root
            try:
                rel = str(new_path.relative_to(media_root)).replace('\\', '/')
                old_rel = str(p.relative_to(media_root)).replace('\\', '/')
                with transaction.atomic():
                    Producto.objects.filter(imagen_producto=old_rel).update(imagen_producto=rel)
                    SolicitudSublimacion.objects.filter(imagen_sublimacion=old_rel).update(imagen_sublimacion=rel)
                    Nota_Entrega.objects.filter(comprobante_pago=old_rel).update(comprobante_pago=rel)
            except Exception:
                pass
            # update static copy if exists
            try:
                static_dir = Path(root).parents[1] / 'frontend' / 'static' / 'product-images'
                if static_dir.exists():
                    old_static = static_dir / p.name
                    new_static = static_dir / new_path.name
                    if old_static.exists():
                        old_static.unlink(missing_ok=True)
                    shutil.copy2(str(new_path), str(new_static))
            except Exception:
                pass
    except UnidentifiedImageError:
        print('SKIP not image', p)
    except Exception as exc:
        print('ERROR', p, exc)

print('Done')
