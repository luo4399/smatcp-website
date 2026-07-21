"""
SomaCard Annotation API Server

Usage:
    python server.py [--port 5502] [--script /path/to/mutation_annotation.py]

    python /media/Rome/home/luodl/website/smatcp-website/somacard/mutation_annotation.py \
        --file-type txt \
        --input /media/Rome/home/luodl/website/smatcp-website/somacard/test_mutation.txt \
        --tissue Adrenal_Gland Muscle

Endpoints:
    POST /api/annotate  — run mutation annotation
    GET  /api/example/<fmt>  — get example file content
    GET  /api/health    — health check
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(os.path.expanduser("~"), "tmp", "somacard")
DEFAULT_ANNOTATION_SCRIPT = os.path.join(SCRIPT_DIR, "mutation_annotation.py")

annotation_script_path = DEFAULT_ANNOTATION_SCRIPT

os.makedirs(TMP_DIR, exist_ok=True)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "script": annotation_script_path,
        "script_exists": os.path.exists(annotation_script_path),
        "tmp_dir": TMP_DIR,
    })


@app.route("/api/example/<fmt>", methods=["GET"])
def get_example(fmt):
    if fmt not in ("txt", "vcf"):
        return jsonify({"error": "format must be txt or vcf"}), 400
    filename = f"test_mutation.{fmt}"
    filepath = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": f"Example file not found: {filename}"}), 404
    with open(filepath, encoding="utf-8") as f:
        return jsonify({"content": f.read(), "filename": filename, "format": fmt})


@app.route("/api/annotate", methods=["POST"])
def annotate():
    data = request.get_json(silent=True) or {}

    mutations = (data.get("mutations") or "").strip()
    file_type = data.get("file_type", "txt")
    tissues = data.get("tissues") or []

    # Demo mode: if SOMACARD_DEMO is set, skip heavy external calls and
    # return a simple mocked result suitable for quick deployments.
    demo_mode = os.environ.get("SOMACARD_DEMO", "0").lower() in ("1", "true", "yes")
    if demo_mode:
        # produce a minimal TSV-like string as demo output
        lines = ["tissue\tmutation_input\tannotation"]
        for i, ln in enumerate(mutations.splitlines(), start=1):
            tissue_val = ",".join(tissues) if tissues else "demo_tissue"
            lines.append(f"{tissue_val}\t{ln}\tDEMO_ANNOT_{i}")
        results = "\n".join(lines) + "\n"
        return jsonify({
            "results": results,
            "input_file": None,
            "output_file": None,
            "demo": True,
        })

    if not mutations:
        return jsonify({"error": "Mutation list is empty"}), 400
    if not tissues:
        return jsonify({"error": "At least one tissue must be selected"}), 400
    if file_type not in ("txt", "vcf"):
        return jsonify({"error": "file_type must be txt or vcf"}), 400

    if not os.path.exists(annotation_script_path):
        return jsonify({
            "error": f"Annotation script not found: {annotation_script_path}"
        }), 500

    # 输入文件保存到 somacard/tmp/
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = ".vcf" if file_type == "vcf" else ".txt"
    input_filename = f"input_{ts}{suffix}"
    input_path = os.path.join(TMP_DIR, input_filename)

    # 输出文件
    output_filename = f"output_{ts}.tsv"
    output_path = os.path.join(TMP_DIR, output_filename)

    try:
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(mutations)
    except OSError as exc:
        return jsonify({"error": f"Cannot write input file: {exc}"}), 500

    try:
        cmd = [
            sys.executable, annotation_script_path,
            "--file-type", file_type,
            "--input", input_path,
            "--tissue", *tissues,
            "-o", output_path,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=os.path.dirname(annotation_script_path) or SCRIPT_DIR,
        )

        if proc.returncode != 0:
            return jsonify({
                "error": "Annotation failed",
                "detail": proc.stderr.strip() or proc.stdout.strip(),
            }), 500

        with open(output_path, encoding="utf-8") as f:
            results = f.read()

        return jsonify({
            "results": results,
            "input_file": input_path,
            "output_file": output_path,
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Annotation timed out (>5 min)"}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def main():
    parser = argparse.ArgumentParser(description="SomaCard Annotation API")
    parser.add_argument("--port", type=int, default=5502)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--script", default=None,
                        help="Path to mutation_annotation.py")
    args = parser.parse_args()

    global annotation_script_path
    if args.script:
        annotation_script_path = args.script

    print(f"Annotation script: {annotation_script_path}")
    print(f"Script exists:    {os.path.exists(annotation_script_path)}")
    print(f"Temp directory:   {TMP_DIR}")
    print(f"Starting SomaCard API on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
