# tools/qr_vector_editor_flask/app.py
from __future__ import annotations
import os
from io import BytesIO
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, abort

# 重要：ロジックを別モジュールに集約
from .editor_app import (
    list_json_items,
    load_json_file,
    get_original_png,
    render_png_from_json,
    toggle_cell_and_save,
    save_whole_json,
    export_png_from_json,
    OUTPUT_DIR,  # for download endpoint
)

# Flask のテンプレ/静的パスをこのファイル相対に固定
THIS_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    static_folder=str(THIS_DIR / "static"),
    template_folder=str(THIS_DIR / "templates"),
)


@app.route("/")
def index():
    return render_template("index.html", preselect="")


@app.route("/edit/<name>")
def edit(name: str):
    # JSON が無ければ 404
    try:
        load_json_file(name)
    except Exception:
        abort(404)
    return render_template("index.html", preselect=name)


# -------- API --------
@app.get("/api/list")
def api_list():
    items = list_json_items()
    return jsonify(items)


@app.get("/api/load")
def api_load():
    filename = request.args.get("file")
    if not filename:
        return jsonify({"error": "param 'file' required"}), 400
    try:
        obj = load_json_file(filename)
        return jsonify(obj)
    except FileNotFoundError:
        return jsonify({"error": "not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/original")
def api_original():
    filename = request.args.get("file")
    size = int(request.args.get("size", "256"))
    if not filename:
        return jsonify({"error": "param 'file' required"}), 400
    try:
        data = get_original_png(filename, size=size)
        return send_file(BytesIO(data), mimetype="image/png")
    except FileNotFoundError:
        return jsonify({"error": "original not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/render")
def api_render():
    filename = request.args.get("file")
    size = int(request.args.get("size", "256"))
    if not filename:
        return jsonify({"error": "param 'file' required"}), 400
    try:
        data = render_png_from_json(filename, size=size)
        return send_file(BytesIO(data), mimetype="image/png")
    except FileNotFoundError:
        return jsonify({"error": "json not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/toggle")
def api_toggle():
    data = request.get_json(silent=True) or {}
    filename = data.get("file")
    gx = data.get("gx")
    gy = data.get("gy")
    if filename is None or gx is None or gy is None:
        return jsonify({"error": "missing fields"}), 400
    try:
        new_val = toggle_cell_and_save(filename, int(gx), int(gy))
        return jsonify({"ok": True, "value": int(new_val)})
    except FileNotFoundError:
        return jsonify({"error": "json not found"}), 404
    except IndexError:
        return jsonify({"error": "index out of range"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/save")
def api_save():
    data = request.get_json(silent=True) or {}
    filename = data.get("file")
    vector = data.get("vector")
    module = data.get("module")
    width = data.get("width")
    height = data.get("height")
    if not filename or vector is None or module is None or width is None or height is None:
        return jsonify({"error": "missing fields"}), 400
    try:
        saved = save_whole_json(filename, vector, int(module), int(width), int(height))
        return jsonify({"ok": True, "saved": saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/export_png")
def api_export_png():
    data = request.get_json(silent=True) or {}
    filename = data.get("file")
    out_name = data.get("out_name")
    if not filename:
        return jsonify({"error": "missing fields"}), 400
    try:
        saved = export_png_from_json(filename, out_name=out_name)
        return jsonify({"ok": True, "saved": saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.get("/download/<path:fname>")
def download(fname: str):
    return send_from_directory(OUTPUT_DIR, fname, as_attachment=True)


# tools/qr_vector_editor_flask/app.py 末尾付近

# ... 既存の import や app = Flask(...) の下はそのまま ...

# 末尾付近にヘルスチェックを追加
@app.get("/health")
def health():
    return jsonify({"ok": True})

def start(host: str | None = None, port: int | None = None, debug: bool = False):
    h = host or os.environ.get("FLASK_RUN_HOST", "0.0.0.0")  # ← 既定も 0.0.0.0 に
    p = int(port or os.environ.get("FLASK_RUN_PORT", "5000"))
    app.run(host=h, port=p, debug=debug, use_reloader=False, threaded=True)

if __name__ == "__main__":
    # 直接実行時だけデバッグONでOK（reloaderは引き続き無効）
    start(debug=True)

