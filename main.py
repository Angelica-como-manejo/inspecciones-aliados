from flask import Flask, request, jsonify, Response
import requests, time, json

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# --- Configuración ---
JOTFORM_API_KEY = "8d86afa90542339182a9c7c55f8f3411"
FORM_ID         = "251257540772660"
TOKEN_SEGURIDAD = "CM53071988AK"

BASE_JF = f"https://api.jotform.com/form/{FORM_ID}/submissions?apikey={JOTFORM_API_KEY}"

# --- Utilidades ---
def autorizado():
    hdr = request.headers.get("Authorization", "")
    q   = request.args.get("token")
    return hdr == f"Bearer {TOKEN_SEGURIDAD}" or q == TOKEN_SEGURIDAD

def limpiar_clave(texto):
    t = (texto or "").lower()
    for a,b in [("–","-"),("¿",""),("?",""),
                ("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a,b)
    t = "".join(c if (c.isalnum() or c == " ") else "_" for c in t)
    return "_".join(t.split()).lower()

def fetch_jotform(limit=400, max_pages=500):
    """Descarga paginada con timeout y reintentos simples."""
    session = requests.Session()
    registros, offset, ultima = [], 0, None

    def get_page(url):
        for intento in range(3):
            try:
                r = session.get(url, timeout=30)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                app.logger.warning(f"Jotform intento {intento+1}/3: {e}")
                time.sleep(1 + intento)
        raise RuntimeError("Jotform sin respuesta tras 3 intentos")

    for _ in range(max_pages):
        url = f"{BASE_JF}&limit={limit}&offset={offset}"
        data = get_page(url)
        content = data.get("content", [])
        if not content:
            break
        registros.extend(content)
        for sub in content:
            ca = sub.get("created_at")
            if ca and (ultima is None or ca > ultima):
                ultima = ca
        offset += limit
        if len(content) < limit:
            break
        time.sleep(0.2)   # Backoff amable
    return registros, ultima

# --- Rutas ---
@app.get("/")
def home():
    return "✅ La API de inspecciones está corriendo correctamente."

@app.get("/status")
def status():
    if not autorizado():
        return jsonify({"error": "No autorizado"}), 401
    try:
        _, ultima = fetch_jotform(limit=1, max_pages=1)
        return jsonify({"ok": True, "ultima_created_at": ultima})
    except Exception as e:
        app.logger.exception("STATUS falló")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/inspecciones_aliados")
def inspecciones_aliados():
    if not autorizado():
        return jsonify({"error": "No autorizado"}), 401
    try:
        registros_totales, ultima = fetch_jotform(limit=400)

        filas = []
        for sub in registros_totales:
            answers = sub.get("answers", {})
            fila = {}
            for k, v in answers.items():
                clave = limpiar_clave(v.get("text", f"campo_{k}"))
                valor = v.get("answer", "")
                fila[clave] = valor
            fila["created_at"] = sub.get("created_at")
            filas.append(fila)

        payload = json.dumps(filas, ensure_ascii=False)
        app.logger.info(f"[DATA] filas={len(filas)} ultima={ultima}")
        return Response(payload, mimetype="application/json; charset=utf-8")
    except Exception as e:
        app.logger.exception("Fallo en /inspecciones_aliados")
        return jsonify({"error": "server_error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
