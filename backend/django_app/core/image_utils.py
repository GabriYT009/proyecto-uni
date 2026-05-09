from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps


DEFAULT_MAX_SIZE = (1600, 1600)
DEFAULT_QUALITY = 82


def optimize_uploaded_image(uploaded_file, *, max_size=DEFAULT_MAX_SIZE, quality=DEFAULT_QUALITY, output_format="WEBP"):
    """Return a resized/compressed in-memory image file.

    The function keeps uploads lightweight by scaling down oversized images and
    recompressing them to a modern format. If optimization fails, the original
    file object is returned unchanged so uploads do not break.
    """

    if not uploaded_file:
        return uploaded_file

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        output = BytesIO()
        save_kwargs = {
            "format": output_format,
            "quality": quality,
            "method": 6,
            "optimize": True,
        }

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        elif output_format.upper() in {"JPEG", "JPG"} and image.mode != "RGB":
            image = image.convert("RGB")

        image.save(output, **save_kwargs)
        output.seek(0)

        original_stem = Path(getattr(uploaded_file, "name", "image")).stem or "image"
        optimized_name = f"{original_stem}.webp" if output_format.upper() == "WEBP" else f"{original_stem}.{output_format.lower()}"

        return InMemoryUploadedFile(
            output,
            field_name=getattr(uploaded_file, "field_name", "") or "",
            name=optimized_name,
            content_type=f"image/{output_format.lower()}",
            size=output.getbuffer().nbytes,
            charset=None,
        )
    except Exception:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return uploaded_file
