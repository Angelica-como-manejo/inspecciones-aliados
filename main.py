# main.py  (versión ligera y estable)
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# === CONFIGURA AQUÍ ===
JOTFORM_API_KEY = "8d86afa90542339182a9c7c55f8f3411"
FORM_ID = "251257540772660"
TOKEN_SEGURIDAD = "CM53071988AK"
# ======================

@app.get("/")
def home():
    return "✅ La API de inspecciones está corriendo correctamente."

@app.get("/inspecciones_aliados")
def inspecciones_aliados():
    # Autorización por header (igual que Power BI)
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {TOKEN_SEGURIDAD}":
        return jsonify({"error": "No autorizado"}), 401

    base_url = f"https://api.jotform.com/form/{FORM_ID}/submissions"
    params = {"apikey": JOTFORM_API_KEY, "limit": 1000, "offset": 0}

    registros = []
    while True:
        r = requests.get(base_url, params=params, timeout=60)
        j = r.json()
        contenido = j.get("content", [])
        if not contenido:
            break

        for sub in contenido:
            respuestas = sub.get("answers", {})
            fila = {}
            for k, v in respuestas.items():
                clave = v.get("text") or f"campo_{k}"
                valor = v.get("answer", "")
                # Normaliza nombre de columna
                clave_limpia = (clave.lower()
                                .replace("–","-").replace("¿","").replace("?","")
                                .replace("á","a").replace("é","e").replace("í","i")
                                .replace("ó","o").replace("ú","u").replace("ñ","n"))
                clave_limpia = "".join(c if c.isalnum() or c==" " else "_" for c in clave_limpia)
                clave_limpia = "_".join(clave_limpia.split())
                fila[clave_limpia] = valor
            registros.append(fila)

        params["offset"] += params["limit"]

    return jsonify(registros)
