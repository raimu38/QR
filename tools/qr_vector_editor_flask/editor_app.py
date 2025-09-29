# tools/qr_vector_editor_flask/editor_app.py
from __future__ import annotations
import json
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
from PIL import Image

# ルート相対（このファイルからの相対パスにしておく）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_DIR = BASE_DIR / "qr_vector"
ORIG_DIR = BASE_DIR / "qr_tobakosan"
OUTPUT_DIR = BASE_DIR / "qr_raimu"

VECTOR_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


# ---------- 基本I/O ----------
def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(obj: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _find_alt_original(stem: str) -> Optional[Path]:
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        p = ORIG_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def _rebuild_image_from_vector(vector: List[List[int]], width: int, height: int, module: int) -> Image.Image:
    """1=黒(0), 0=白(255) でセル塗りつぶしして Pillow Image(L) を返す"""
    img = np.ones((height, width), dtype=np.uint8) * 255
    cell_w = max(1, width // module)
    cell_h = max(1, height // module)
    grid = np.array(vector, dtype=int)

    for gy in range(module):
        y0 = gy * cell_h
        y1 = (gy + 1) * cell_h if gy < module - 1 else height
        for gx in range(module):
            x0 = gx * cell_w
            x1 = (gx + 1) * cell_w if gx < module - 1 else width
            val = 0 if grid[gy, gx] == 1 else 255
            img[y0:y1, x0:x1] = val
    return Image.fromarray(img, mode="L")


def _image_to_png_bytes(im: Image.Image) -> bytes:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# ---------- 公開API(ロジック) ----------
def list_json_items() -> List[Dict[str, Any]]:
    def _key(p: Path):
        stem = p.stem
        try:
            return (0, int(stem))
        except ValueError:
            return (1, stem)

    files = sorted(VECTOR_DIR.glob("*.json"), key=_key)
    items: List[Dict[str, Any]] = []
    for p in files:
        name = p.name
        try:
            obj = _load_json(p)
            module = int(obj.get("module", 0))
            w = int(obj.get("width", 0))
            h = int(obj.get("height", 0))
            file_field = obj.get("file", "")
            stem = Path(file_field).stem if file_field else p.stem
            orig = _find_alt_original(stem)
            items.append({
                "json": name,
                "module": module,
                "width": w,
                "height": h,
                "original_exists": bool(orig),
                "original_name": orig.name if orig else None,
                "stem": stem,
            })
        except Exception:
            items.append({
                "json": name, "module": None, "width": None, "height": None,
                "original_exists": False, "original_name": None, "stem": p.stem
            })
    return items


def load_json_file(filename: str) -> Dict[str, Any]:
    path = VECTOR_DIR / filename
    obj = _load_json(path)
    if not all(k in obj for k in ("vector", "module", "width", "height")):
        raise ValueError("invalid json structure")
    return obj


def get_original_png(filename: str, size: int = 256) -> bytes:
    # filename は JSON 名
    obj = load_json_file(filename)
    stem = Path(obj.get("file", "")).stem or Path(filename).stem
    opath = _find_alt_original(stem)
    if not opath:
        raise FileNotFoundError("original not found")
    im = Image.open(opath).convert("L")
    im = im.resize((size, size), resample=Image.NEAREST)
    return _image_to_png_bytes(im)


def render_png_from_json(filename: str, size: int = 256) -> bytes:
    obj = load_json_file(filename)
    vector = obj["vector"]
    module = int(obj["module"])
    w = int(obj["width"])
    h = int(obj["height"])
    im = _rebuild_image_from_vector(vector, width=w, height=h, module=module)
    im = im.resize((size, size), resample=Image.NEAREST)
    return _image_to_png_bytes(im)


def toggle_cell_and_save(filename: str, gx: int, gy: int) -> int:
    path = VECTOR_DIR / filename
    obj = _load_json(path)
    vec = obj.get("vector")
    module = int(obj.get("module", 0))
    if vec is None or module <= 0:
        raise ValueError("invalid json structure")
    try:
        current = int(vec[gy][gx])
        new_val = 1 - current
        vec[gy][gx] = new_val
    except Exception as e:
        raise IndexError("index out of range") from e
    obj["vector"] = vec
    _save_json(obj, path)
    return int(new_val)


def save_whole_json(filename: str, vector: List[List[int]], module: int, width: int, height: int) -> str:
    path = VECTOR_DIR / filename
    obj = {
        "file": Path(filename).with_suffix(".png").name,
        "module": int(module),
        "width": int(width),
        "height": int(height),
        "vector": vector,
    }
    _save_json(obj, path)
    return str(path)


def export_png_from_json(filename: str, out_name: Optional[str] = None) -> str:
    obj = load_json_file(filename)
    vector = obj["vector"]
    module = int(obj["module"])
    w = int(obj["width"])
    h = int(obj["height"])
    im = _rebuild_image_from_vector(vector, width=w, height=h, module=module)
    if not out_name:
        out_name = Path(filename).with_suffix(".png").name
    out_path = OUTPUT_DIR / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path)
    return str(out_path)
