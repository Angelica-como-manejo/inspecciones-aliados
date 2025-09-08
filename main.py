# ---------- main.py ----------
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# -------------------------------------------------------------------
# CONFIGURACIÓN
# -------------------------------------------------------------------
JOTFORM_API_KEY  = "8d86afa90542339182a9c7c55f8f3411"   # clave API de Jotform
FORM_ID          = "251257540772660"                    # ID del formulario
TOKEN_SEGURIDAD  = "CM53071988AK"                       # token para Authorization

LIMIT  = 1000  # registros por página

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
    url_base = (
        f"https://api.jotform.com/form/{FORM_ID}/submissions"
        f"?apikey={JOTFORM_API_KEY}"
    )

    registros_totales = []
    offset = 0

    while True:
        url = f"{url_base}&limit={LIMIT}&offset={offset}"
        response = requests.get(url)
        data = response.json()

        content = data.get("content", [])
        if not content:
            break

        registros_totales.extend(content)
        offset += LIMIT

    if not registros_totales:
        return jsonify({"error": "No se encontraron respuestas"}), 500

    # --- Procesar cada submission ---
    registros = []
    for sub in registros_totales:
        respuestas = sub.get("answers", {})
        fila = {}
        for k, v in respuestas.items():
            clave = v.get("text", f"campo_{k}")
            valor = v.get("answer", "")

            # Normalizar clave
            clave_limpia = (
                clave.lower()
                .replace("–", "-")
                .replace("¿", "")
                .replace("?", "")
                .replace("á", "a").replace("é", "e").replace("í", "i")
                .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            )
            # Mantener alfanumérico y espacio; todo lo demás "_"
            clave_limpia = ''.join(
                c if c.isalnum() or c == " " else "_" for c in clave_limpia
            )
            # Cambiar espacios a "_"
            clave_limpia = "_".join(clave_limpia.split()).lower()
            fila[clave_limpia] = valor

        registros.append(fila)

    df = pd.DataFrame(registros)

    # Devolver JSON con encabezado correcto
    return df.to_json(orient="records", force_ascii=False), 200, {
        "Content-Type": "application/json"
    }

# -------------------------------------------------------------------
# EJECUCIÓN LOCAL / RENDER
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Render asigna el puerto en la variable de entorno PORT
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)

