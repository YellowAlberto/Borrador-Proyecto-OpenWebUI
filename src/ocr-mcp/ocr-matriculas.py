# ocr-mcp/server.py
import cv2
import easyocr
import re
import os
from mcp.server.fastmcp import FastMCP

# Configuración del servidor
mcp = FastMCP("ContainerOCR")

# Inicializar EasyOCR (CPU por defecto para compatibilidad, cambiar gpu=True si configuras nvidia runtime)
print("--- Cargando modelo OCR... ---")
reader = easyocr.Reader(['en'], gpu=False) 
print("--- Modelo cargado ---")

# --- LÓGICA DE PROCESADO (Tu código optimizado) ---
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contrast = clahe.apply(gray)
    h, w = contrast.shape
    if h < 800: 
        scale = 1.5
        contrast = cv2.resize(contrast, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return contrast

def smart_correction(text):
    dict_letra_a_num = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'A': '4', 'S': '5', 'G': '6', 'B': '8'}
    dict_num_a_letra = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B', '4': 'A', '6': 'G'}
    clean = re.sub(r'[^A-Z0-9]', '', text.upper())
    for i in range(len(clean) - 10):
        candidate = list(clean[i : i+11])
        prefix = candidate[:4]
        suffix = candidate[4:]
        new_prefix = [dict_num_a_letra.get(c, c) if not c.isalpha() else c for c in prefix]
        new_suffix = [dict_letra_a_num.get(c, c) if not c.isdigit() else c for c in suffix]
        final = "".join(new_prefix + new_suffix)
        if re.match(r'^[A-Z]{4}\d{7}$', final):
            return final
    return None

# --- HERRAMIENTA MCP ---
@mcp.tool()
def get_container_plate(filename: str) -> str:
    """
    Lee la matrícula de un contenedor.
    Args:
        filename: El nombre del archivo (ej: "foto1.jpg") que está en la carpeta compartida /data.
    """
    # IMPORTANTE: Definimos la ruta base donde Docker monta el volumen
    base_path = "/data"
    image_path = os.path.join(base_path, filename)
    
    if not os.path.exists(image_path):
        return f"Error: No encuentro el archivo '{filename}' en la carpeta /data. Rutas disponibles: {os.listdir(base_path)}"

    try:
        img = cv2.imread(image_path)
        if img is None: return "Error: Formato de imagen no válido."

        processed = preprocess_image(img)
        results = reader.readtext(processed, detail=0, paragraph=False)
        concat_text = "".join(results)
        matricula = smart_correction(concat_text)

        if matricula:
            return f"Matrícula detectada: {matricula}"
        else:
            return f"No se pudo leer la matrícula. Texto crudo: {concat_text[:50]}"
    except Exception as e:
        return f"Error interno: {str(e)}"

if __name__ == "__main__":
    print("--- Iniciando servidor MCP en 0.0.0.0:8001 ---")
    # IMPORTANTE: Forzar host 0.0.0.0 y puerto 8001
    mcp.run(transport='http', host='0.0.0.0', port=8001, path="/ocr")