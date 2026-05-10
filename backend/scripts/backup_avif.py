import shutil
from pathlib import Path
from datetime import datetime

root = Path(__file__).resolve().parents[1]
media_dir = root / 'django_app' / 'media'
frontend_static = Path(root).parents[1] / 'frontend' / 'static' / 'product-images'

now = datetime.now().strftime('%Y%m%d-%H%M%S')
backup_dir = Path(root).parents[1] / 'avif_backups' / now
backup_dir = backup_dir.resolve()
backup_dir.mkdir(parents=True, exist_ok=True)

paths = []
if media_dir.exists():
    paths.extend(media_dir.rglob('*.avif'))
if frontend_static.exists():
    paths.extend(frontend_static.rglob('*.avif'))

count = 0
for p in paths:
    try:
        rel = p.relative_to(Path(root).parents[1])
    except Exception:
        rel = Path(p.name)
    dest = backup_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
    count += 1

print(f'Backed up {count} AVIF files to {backup_dir}')
