# ---------- main.py ----------
from flask import Flask, request, Response, jsonify, stream_with_context
import requests, os, json

app = Flask(_name_)

# ---- CONFIG ----
JOTFORM_API_KEY = "8d86afa90542339182a9c7c55f8f3411"
FORM_ID         = "251257540772660"
TOKEN_SEGURIDAD = "CM53071988AK"

# Tamaño de página hacia Jotform (más pequeño = menos RAM; más llamadas)
LIMIT = int(os.getenv("JT_LIMIT", "300"))  # 300 por defecto

@app.get("/")
def home():
    return "✅ API viva"

@app.get("/inspecciones_aliados")
def inspecciones_aliados():
    # Autorización simple por header
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {TOKEN_SEGURIDAD}":
        return jsonify({"error": "No autorizado"}), 401

    # Permite sobreescribir tamaño/offset si alguna vez quieres probar
    limit  = int(request.args.get("limit",  LIMIT))
    offset = int(request.args.get("offset", 0))

    url_base = f"https://api.jotform.com/form/{FORM_ID}/submissions?apikey={JOTFORM_API_KEY}"

    def normalize_row(answers: dict):
        """Convierte el diccionario answers de Jotform a un registro plano."""
        row = {}
        for k, v in (answers or {}).items():
            key  = v.get("text", f"campo_{k}") or f"campo_{k}"
            val  = v.get("answer", "")
            # normaliza clave (minúsculas, sin tildes ni signos raros)
            key = (key.lower()
                       .replace("–","-").replace("¿","").replace("?","")
                       .replace("á","a").replace("é","e").replace("í","i")
                       .replace("ó","o").replace("ú","u").replace("ñ","n"))
            key = "".join(c if (c.isalnum() or c==" ") else "_" for c in key)
            key = "_".join(key.split()).lower()
            row[key] = val
        return row

    @stream_with_context
    def generate():
        """Devuelve un JSON grande como stream: [ {...},{...}, ... ]"""
        first = True
        yield "["
        cur = offset
        while True:
            url = f"{url_base}&limit={limit}&offset={cur}"
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            data = r.json()
            content = data.get("content", []) or []

            if not content:
                break

            for sub in content:
                row = normalize_row(sub.get("answers"))
                # Escribe coma entre elementos para JSON válido
                if not first:
                    yield ","
                first = False
                yield json.dumps(row, ensure_ascii=False)

            # siguiente página
            cur += limit

        yield "]"

    # Respuesta en streaming = menos RAM, menos timeouts
    return Response(generate(), mimetype="application/json")


if _name_ == "_main_":
    port = int(os.getenv("PORT", "5000"))
    # Un solo worker/threads en local
    app.run(host="0.0.0.0", port=port, debug=False)
