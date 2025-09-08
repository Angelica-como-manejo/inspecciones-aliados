# ---------- main.py ----------
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# -------------------------------------------------------------------
# CONFIGURACIÓN (usa env vars si existen; si no, toma los defaults)
# -------------------------------------------------------------------
JOTFORM_API_KEY = os.getenv("JOTFORM_API_KEY", "8d86afa90542339182a9c7c55f8f3411")
FORM_ID         = os.getenv("FORM_ID", "251257540772660")
TOKEN_SEGURIDAD = os.getenv("TOKEN_SEGURIDAD", "CM53071988AK")

LIMIT = 1000  # registros por página
SESSION = requests.Session()
SESSION.headers.update({"Connection": "keep-alive"})

# -------------------------------------------------------------------
# RUTA DE SALUD
# -------------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return "✅ La API de inspecciones está corriendo correctamente."

# -------------------------------------------------------------------
# RUTA PRINCIPAL
# -------------------------------------------------------------------
@app.route("/inspecciones_aliados", methods=["GET"])
def inspecciones_aliados():
    # --- Autorización por token ---
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {TOKEN_SEGURIDAD}":
        return jsonify({"error": "No autorizado"}), 401

    # --- Paginación Jotform ---
    url_base = f"https://api.jotform.com/form/{FORM_ID}/submissions?apikey={JOTFORM_API_KEY}"

    registros_totales = []
    offset = 0

    while True:
        url = f"{url_base}&limit={LIMIT}&offset={offset}"
        try:
            resp = SESSION.get(url, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return jsonify({"error": "Fallo consultando Jotform", "detalle": str(e), "offset": offset}), 502

        content = data.get("content", [])
        if not content:
            break

        # Aplanado mínimo (sin pandas). Power BI entiende listas/objetos en JSON.
        for sub in content:
            answers = sub.get("answers", {})
            fila = {}
            for k, v in answers.items():
                key = v.get("text", f"campo_{k}")
                ans = v.get("answer", "")
                fila[key] = ans
            # Meta útil
            fila["_submission_id"] = sub.get("id")
            fila["_created_at"] = sub.get("created_at")
            registros_totales.append(fila)

        offset += LIMIT
        # Cortafuego por si acaso
        if offset > 50000:
            break

    return jsonify(registros_totales), 200

# -------------------------------------------------------------------
# EJECUCIÓN LOCAL / RENDER
# -------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)

