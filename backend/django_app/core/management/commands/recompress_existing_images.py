from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageOps, UnidentifiedImageError


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.avif'}


class Command(BaseCommand):
    help = 'Recomprime imágenes ya existentes en MEDIA_ROOT y en frontend/static/product-images.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué archivos se procesarían sin escribir cambios.',
        )
        parser.add_argument(
            '--max-size',
            type=int,
            default=1600,
            help='Dimensión máxima en píxeles para ancho o alto.',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=82,
            help='Calidad para JPEG/WebP (1-95).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        max_size = max(256, int(options['max_size'] or 1600))
        quality = max(40, min(95, int(options['quality'] or 82)))

        targets = self._collect_targets()
        if not targets:
            self.stdout.write(self.style.WARNING('No se encontraron imágenes para recomprimir.'))
            return

        processed = 0
        skipped = 0
        failed = 0

        for path in targets:
            try:
                changed = self._optimize_file(path, max_size=max_size, quality=quality, dry_run=dry_run)
                if changed:
                    processed += 1
                    self.stdout.write(self.style.SUCCESS(f'OK {path}'))
                else:
                    skipped += 1
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f'ERROR {path}: {exc}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Finalizado. Procesadas: {processed}, ignoradas: {skipped}, fallidas: {failed}.'
            )
        )

    def _collect_targets(self):
        roots = []

        media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '')
        if media_root.exists():
            roots.append(media_root)

        frontend_static = getattr(settings, 'FRONTEND_DIR', None)
        if frontend_static:
            product_images = Path(frontend_static) / 'static' / 'product-images'
            if product_images.exists():
                roots.append(product_images)

        files = []
        seen = set()
        for root in roots:
            for path in root.rglob('*'):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                if path in seen:
                    continue
                seen.add(path)
                files.append(path)
        return files

    def _optimize_file(self, path: Path, *, max_size: int, quality: int, dry_run: bool) -> bool:
        try:
            original_size = path.stat().st_size
        except FileNotFoundError:
            return False

        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image)
                source_format = (image.format or path.suffix.lstrip('.')).upper()
                if source_format in {'JPG', 'JPEG'}:
                    target_format = 'JPEG'
                elif source_format in {'PNG', 'WEBP'}:
                    target_format = source_format
                elif source_format == 'AVIF':
                    # Convert AVIF to WEBP
                    target_format = 'WEBP'
                else:
                    target_format = None

                if target_format is None:
                    self.stdout.write(self.style.WARNING(f'SKIP {path} (formato no optimizable: {source_format})'))
                    return False

                working = image.copy()
                working.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                if target_format == 'JPEG' and working.mode not in {'RGB', 'L'}:
                    working = working.convert('RGB')

                save_kwargs = {'optimize': True}
                if target_format == 'JPEG':
                    save_kwargs.update({'quality': quality, 'progressive': True})
                elif target_format == 'PNG':
                    save_kwargs.update({'compress_level': 9})
                elif target_format == 'WEBP':
                    save_kwargs.update({'quality': quality, 'method': 6})

                if dry_run:
                    self.stdout.write(f'DRY-RUN {path}')
                    return True

                # If converting from AVIF -> WEBP we need to change the file extension
                if source_format == 'AVIF' and target_format == 'WEBP':
                    new_path = path.with_suffix('.webp')
                else:
                    new_path = path.with_name(f'{path.name}.recompressed')

                try:
                    working.save(str(new_path), format=target_format, **save_kwargs)
                    new_size = new_path.stat().st_size
                    if new_size >= original_size and source_format != 'AVIF':
                        new_path.unlink(missing_ok=True)
                        return False

                    # If we created a new filename (AVIF->WEBP), remove original and update DB references
                    if new_path != path:
                        try:
                            path.unlink(missing_ok=True)
                        except Exception:
                            pass

                        # Update DB references for known fields to point to new relative path
                        from django.db import transaction
                        from django.conf import settings as dj_settings
                        rel = None
                        media_root = Path(getattr(dj_settings, 'MEDIA_ROOT', '') or '')
                        try:
                            rel = str(new_path.relative_to(media_root)).replace('\\', '/')
                        except Exception:
                            rel = None

                        if rel:
                            try:
                                with transaction.atomic():
                                    try:
                                        from ...models import Producto, SolicitudSublimacion, Nota_Entrega
                                        Producto.objects.filter(imagen_producto=str(path.relative_to(media_root)).replace('\\', '/')).update(imagen_producto=rel)
                                    except Exception:
                                        pass
                                    try:
                                        SolicitudSublimacion.objects.filter(imagen_sublimacion=str(path.relative_to(media_root)).replace('\\', '/')).update(imagen_sublimacion=rel)
                                    except Exception:
                                        pass
                                    try:
                                        Nota_Entrega.objects.filter(comprobante_pago=str(path.relative_to(media_root)).replace('\\', '/')).update(comprobante_pago=rel)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        # Also update static/product-images copy if exists
                        frontend_static = getattr(dj_settings, 'FRONTEND_DIR', None)
                        if frontend_static:
                            static_dir = Path(frontend_static) / 'static' / 'product-images'
                            old_static = static_dir / path.name
                            new_static = static_dir / new_path.name
                            try:
                                if old_static.exists():
                                    old_static.unlink(missing_ok=True)
                                if new_path.exists():
                                    import shutil
                                    shutil.copy2(str(new_path), str(new_static))
                            except Exception:
                                pass
                    else:
                        # Replace in-place for same-name formats
                        new_path.replace(path)
                    return True
                finally:
                    if new_path.exists():
                        try:
                            # If we left a temp file with .recompressed extension, clean it up
                            if new_path.suffix == '.recompressed':
                                new_path.unlink(missing_ok=True)
                        except Exception:
                            pass
        except UnidentifiedImageError:
            self.stdout.write(self.style.WARNING(f'SKIP {path} (archivo no es una imagen válida)'))
            return False
        except Exception:
            raise
