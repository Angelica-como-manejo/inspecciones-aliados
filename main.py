# ---------- main.py ----------
from flask import Flask, request, jsonify, Response
import requests
import json
import os

app = Flask(_name_)

# -------------------------------------------------------------------
# CONFIGURACIÓN (lo que ya usas)
# -------------------------------------------------------------------
JOTFORM_API_KEY = "8d86afa90542339182a9c7c55f8f3411"   # clave API de Jotform
FORM_ID         = "251257540772660"                     # ID del formulario
TOKEN_SEGURIDAD = "CM53071988AK"                        # token para Authorization

# Límites por defecto (puedes cambiarlos aquí si necesitas)
DEFAULT_LIMIT_PER_PAGE = 200    # menos de 1000 para evitar timeouts
DEFAULT_MAX_PAGES      = 200    # tope de páginas para cortar bucles largos
REQUEST_TIMEOUT_SEC    = 25     # timeout por llamada a Jotform (segundos)

# -------------------------------------------------------------------
# UTIL: aplana una submission de Jotform a un diccionario plano
# -------------------------------------------------------------------
def normalizar_texto(clave: str) -> str:
    if not isinstance(clave, str):
        clave = str(clave)
    reemplazos = {
        "–": "-", "¿": "", "?": "",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"
    }
    for a, b in reemplazos.items():
        clave = clave.replace(a, b)
    # Solo alfanumérico y espacio; lo demás a "_"
    clave = "".join(c if (c.isalnum() or c == " ") else "_" for c in clave.lower())
    # Espacios -> "_"
    return "_".join(clave.split())

def aplana_submission(sub: dict) -> dict:
    respuestas = sub.get("answers", {}) or {}
    fila = {}
    for k, v in respuestas.items():
        if not isinstance(v, dict):
            continue
        clave = v.get("text", f"campo_{k}")
        valor = v.get("answer", "")
        clave_limpia = normalizar_texto(clave)

        # Si la respuesta es lista/dict, la pasamos a string JSON para que Power BI la lea
        if isinstance(valor, (list, dict)):
            try:
                valor = json.dumps(valor, ensure_ascii=False)
            except Exception:
                valor = str(valor)

        fila[clave_limpia] = valor

    # Metadatos útiles
    fila["_submission_id"] = sub.get("id")
    fila["_created_at"]    = sub.get("created_at")
    fila["_updated_at"]    = sub.get("updated_at")
    return fila

# -------------------------------------------------------------------
# RUTAS DE SALUD
# -------------------------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    return "✅ API de inspecciones lista."

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# -------------------------------------------------------------------
# RUTA PRINCIPAL: /inspecciones_aliados
#   - Auth por header: Authorization: Bearer <TOKEN_SEGURIDAD>
#   - Query params opcionales:
#       ?limit=200        (por página hacia Jotform)
#       ?max_pages=100    (tope de páginas)
# -------------------------------------------------------------------
@app.route("/inspecciones_aliados", methods=["GET"])
def inspecciones_aliados():
    # --- Autorización por token (igual que tu M en Power BI) ---
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {TOKEN_SEGURIDAD}":
        return jsonify({"error": "No autorizado"}), 401

    # --- Parámetros de control (opcionales) ---
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT_PER_PAGE))
        if limit <= 0 or limit > 1000:
            limit = DEFAULT_LIMIT_PER_PAGE
    except Exception:
        limit = DEFAULT_LIMIT_PER_PAGE

    try:
        max_pages = int(request.args.get("max_pages", DEFAULT_MAX_PAGES))
        if max_pages <= 0:
            max_pages = DEFAULT_MAX_PAGES
    except Exception:
        max_pages = DEFAULT_MAX_PAGES

    # --- Base URL Jotform ---
    base_url = f"https://api.jotform.com/form/{FORM_ID}/submissions?apikey={JOTFORM_API_KEY}"

    # --- Paginación segura (limit + offset) ---
    offset = 0
    pagina = 0
    acumulado = []

    while pagina < max_pages:
        url = f"{base_url}&limit={limit}&offset={offset}"
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.Timeout:
            return jsonify({"error": "Timeout al consultar Jotform", "offset": offset}), 504
        except Exception as e:
            return jsonify({"error": "Fallo al consultar Jotform", "detalle": str(e), "offset": offset}), 502

        content = data.get("content", [])
        if not content:
            break

        # Aplanar y acumular
        for sub in content:
            acumulado.append(aplana_submission(sub))

        # Avanzar paginación
        pagina += 1
        offset += limit

    if not acumulado:
        # Si no vino nada, que sea 200 con array vacío (Power BI lo maneja bien)
        return Response("[]", status=200, mimetype="application/json; charset=utf-8")

    # Devolver JSON de registros (orient records)
    # Usamos json.dumps directo para evitar dependencias pesadas
    body = json.dumps(acumulado, ensure_ascii=False)
    return Response(body, status=200, mimetype="application/json; charset=utf-8")

# -------------------------------------------------------------------
# EJECUCIÓN LOCAL / RENDER
# -------------------------------------------------------------------
if _name_ == "_main_":
    # Render asigna el puerto en PORT
    port = int(os.getenv("PORT", "5000"))
    # host=0.0.0.0 para aceptar tráfico externo
    app.run(host="0.0.0.0", port=port)
