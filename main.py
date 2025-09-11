# ---------- main.py ----------
from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

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
# Utilidades
# -------------------------------------------------------------------
DATE_FIELDS = {
    "FECHA DE VENCIMIENTO SOAT",
    "FECHA DE VENCIMIENTO REVISIÓN TECNICOMECÁNICA",
    "FECHA DE VENCIMIENTO REVISIÓN TECNICOMEcÁNICA",   # por si viene con otra tilde
    "FECHA",  # a veces Jotform pone solo "FECHA"
}

def _to_iso_from_parts(obj):
    """Convierte dict con year/month/day (y opcional hora) a ISO 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS'."""
    try:
        y = int(obj.get("year"))
        m = int(obj.get("month"))
        d = int(obj.get("day"))
        hh = int(obj.get("hour", 0))
        mm = int(obj.get("minute", 0))
        ss = int(obj.get("second", 0))
        if hh or mm or ss:
            return datetime(y, m, d, hh, mm, ss).isoformat()
        return datetime(y, m, d).date().isoformat()
    except Exception:
        return None

def _try_parse_text_date(s):
    """Intenta parsear texto común a ISO; si no puede, devuelve el original."""
    if not isinstance(s, str):
        return s
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def normalize_answer(key, ans):
    """Normaliza respuestas:
       - Records con 'datetime' -> ISO
       - Records con year/month/day -> ISO
       - Listas -> texto '; '
       - Fechas en texto -> intenta ISO
    """
    # 1) Si viene como dict con 'datetime'
    if isinstance(ans, dict) and "datetime" in ans:
        val = ans.get("datetime")
        # A veces 'datetime' ya viene ISO. Si no, intenta convertir.
        return _try_parse_text_date(val) if isinstance(val, str) else val

    # 2) Si viene como dict con year/month/day
    if isinstance(ans, dict) and {"year", "month", "day"} <= set(ans.keys()):
        iso = _to_iso_from_parts(ans)
        return iso if iso else ans

    # 3) Si es lista (fotos, selección múltiple)
    if isinstance(ans, list):
        try:
            return "; ".join(str(x) for x in ans)
        except Exception:
            return str(ans)

    # 4) Si es texto y el campo luce de fecha, intenta ISO
    if isinstance(ans, str) and (key.upper() in DATE_FIELDS or "FECHA" in key.upper()):
        return _try_parse_text_date(ans)

    # 5) Caso general
    return ans

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

        # Aplanado mínimo (sin pandas). Normalizamos valores "fecha".
        for sub in content:
            answers = sub.get("answers", {})
            fila = {}
            for k, v in answers.items():
                key = v.get("text", f"campo_{k}") or f"campo_{k}"
                ans = v.get("answer", "")
                fila[key] = normalize_answer(key, ans)

            # Meta útil
            fila["_submission_id"] = sub.get("id")
            fila["_created_at"] = sub.get("created_at")
            registros_totales.append(fila)

        offset += LIMIT
        # Cortafuego por si acaso (evita loops infinitos)
        if offset > 50000:
            break

    return jsonify(registros_totales), 200

# -------------------------------------------------------------------
# EJECUCIÓN LOCAL / RENDER
# -------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)
