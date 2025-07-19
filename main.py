from flask import Flask, request, jsonify
import pandas as pd
import requests

app = Flask(_name_)

# Configuración
JOTFORM_API_KEY = "8d86afa90542339182a9c7c55f8f3411"  # Asegúrate de poner tu clave de API de Jotform
FORM_ID = "251257540772660"  # ID de tu formulario
TOKEN_SEGURIDAD = "CM53071988AK"  # Token de seguridad que usas en tu API

# Ruta raíz para confirmar que la API está corriendo
@app.route("/", methods=["GET"])
def home():
    return "✅ La API de inspecciones está corriendo correctamente."

# Ruta para acceder a los datos
@app.route("/inspecciones_aliados", methods=["GET"])
def inspecciones_aliados():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {TOKEN_SEGURIDAD}":
        return jsonify({"error": "No autorizado"}), 401
    
    # URL base para obtener los registros de Jotform
    url_base = f"https://api.jotform.com/form/{FORM_ID}/submissions?apikey={JOTFORM_API_KEY}"

    # Paginación: Obtener más de 1000 registros
    registros_totales = []
    offset = 0
    limit = 1000  # Cuántos registros por página
    while True:
        url = f"{url_base}&limit={limit}&offset={offset}"
        response = requests.get(url)
        data = response.json()

        if "content" not in data or len(data["content"]) == 0:
            break  # Si no hay más registros, salimos del bucle

        registros_totales.extend(data["content"])
        offset += limit  # Avanzamos el offset para obtener la siguiente página

    if not registros_totales:
        return jsonify({"error": "No se encontraron respuestas"}), 500
    
    # Procesar los registros obtenidos
    registros = []
    for sub in registros_totales:
        respuestas = sub.get("answers", {})
        fila = {}
        for k, v in respuestas.items():
            clave = v.get("text", f"campo_{k}")
            valor = v.get("answer", "")
            # Limpiamos y formateamos las claves
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

    # Convertir los registros a DataFrame
    df = pd.DataFrame(registros)
    return df.to_json(orient="records", force_ascii=False)

if _name_ == "_main_":
    app.run()
