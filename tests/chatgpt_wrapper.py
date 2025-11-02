# chatgpt_wrapper.py
from openai import OpenAI
import os
import google.generativeai as genai

"""client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Usa tu clave de API desde variable de entorno

def generate_response_with_chatgpt(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Asegúrate de tener acceso a este modelo
            messages=[
                {"role": "system", "content": "Eres un asistente útil que responde con claridad."},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error al generar respuesta con ChatGPT:\n\n{str(e)}"
        """
# Usa tu clave de API de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # O directamente: "tu_clave_aqui"
genai.configure(api_key=GEMINI_API_KEY)

# Carga el modelo
model = genai.GenerativeModel("gemini-2.5-pro")

# Función de generación de respuesta
def generate_response_with_gemini(text):
    try:
        response = model.generate_content(text)
        return response.text
    except Exception as e:
        return f"❌ Error al generar respuesta con Gemini:\n{e}"