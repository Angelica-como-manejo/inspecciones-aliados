from flask import Flask, request, jsonify
import pandas as pd
import requests

app = Flask(__name__)

# Configuración actualizada
JOTFORM_API_KEY = "8d86afa90542339182a9c7c55f8f3411"
FORM_ID = "251257540772660"
TOKEN_SEGURIDAD = "CM53071988AK"

# Ruta raíz para confirmar que la API está viva
@app.route("/", methods=["GET"])
def home():
    return "✅ La API de inspecciones está corriendo correctamente."

# Ruta protegida que devuelve los datos del formulario
@app.route("/inspecciones_aliados", methods=["GET"])
def inspecciones_aliados():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {TOKEN_SEGURIDAD}":
        return jsonify({"error": "No autorizado"}), 401

    url = f"https://api.jotform.com/form/{FORM_ID}/submissions?apikey={JOTFORM_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "content" not in data:
        return jsonify({"error": "No se encontraron respuestas"}), 500

    registros = []

    for sub in data["content"]:
        respuestas = sub.get("answers", {})
        fila = {}
        for k, v in respuestas.items():
            clave = v.get("text", f"campo_{k}")
            valor = v.get("answer", "")
            clave_limpia = (
                clave.lower()
                .replace("–", "-")
                .replace("¿", "")
                .replace("?", "")
                .replace("á", "a").replace("é", "e").replace("í", "i")
                .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            )
            clave_limpia = "".join(c if c.isalnum() or c == " " else "_" for c in clave_limpia)
            clave_limpia = "_".join(clave_limpia.split()).lower()
            fila[clave_limpia] = valor
        registros.append(fila)

    df = pd.DataFrame(registros)
    return df.to_json(orient="records", force_ascii=False)

if __name__ == "__main__":
    app.run()
