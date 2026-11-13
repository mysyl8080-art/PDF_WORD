"""Image converters & utilities."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .common import ToolError, safe_stem, unique_path

Params = dict

try:  # HEIC/HEIF (iPhone photos)
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pass

_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def _open(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        img.load()
        return ImageOps.exif_transpose(img)
    except Exception as e:
        raise ToolError("bad_image", str(e)) from e


def _flatten(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def _save(img: Image.Image, dest_dir: Path, stem: str, fmt: str) -> Path:
    dest = unique_path(dest_dir, f"{stem}.{_EXT[fmt]}")
    if fmt == "JPEG":
        _flatten(img).save(dest, "JPEG", quality=92, optimize=True, subsampling=0)
    elif fmt == "PNG":
        img.convert("RGBA" if "A" in img.getbands() or img.mode == "P" else "RGB").save(dest, "PNG", optimize=True)
    else:
        img.convert("RGBA" if "A" in img.getbands() else "RGB").save(dest, "WEBP", quality=92, method=6)
    return dest


def _converter(fmt: str):
    def run(files: list[Path], out: Path, p: Params) -> list[Path]:
        return [_save(_open(f), out, safe_stem(f), fmt) for f in files]

    return run


to_jpg = _converter("JPEG")   # PNG/WEBP/BMP/GIF/TIFF/HEIC → JPG
to_png = _converter("PNG")    # JPG/WEBP/... → PNG
to_webp = _converter("WEBP")  # JPG/PNG → WEBP


def compress_images(files: list[Path], out: Path, p: Params) -> list[Path]:
    q = int(p.get("quality", 70))
    results = []
    for f in files:
        img = _open(f)
        dest = unique_path(out, f"{safe_stem(f)}_compressed.jpg")
        _flatten(img).save(dest, "JPEG", quality=max(10, min(q, 95)), optimize=True, progressive=True)
        results.append(dest)
    return results


def resize_images(files: list[Path], out: Path, p: Params) -> list[Path]:
    raw = str(p.get("width", "")).strip().lower().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    try:
        if raw.endswith("%"):
            ratio = float(raw[:-1]) / 100
            width = None
        else:
            ratio, width = None, int(raw.replace("px", ""))
    except ValueError as e:
        raise ToolError("bad_pages", raw) from e
    results = []
    for f in files:
        img = _open(f)
        w = int(img.width * ratio) if ratio else width
        if not w or w < 16 or w > 12000:
            raise ToolError("bad_pages", raw)
        h = max(1, round(img.height * (w / img.width)))
        res = img.resize((w, h), Image.LANCZOS)
        fmt = "PNG" if f.suffix.lower() == ".png" else "JPEG"
        results.append(_save(res, out, f"{safe_stem(f)}_{w}px", fmt))
    return results