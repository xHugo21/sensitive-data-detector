import streamlit as st
import os, io, re, base64
from Middleware import read_document, detect_sensitive_data, compute_risk_level
#from chatgpt_wrapper import generate_response_with_chatgpt
from chatgpt_wrapper import generate_response_with_gemini
from PIL import Image
from openai import OpenAI
from html import escape
import streamlit.components.v1 as components
from streamlit.components.v1 import html
import pandas as pd
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent / "PROMPTS"


def format_response_table(detected_fields, high_risk, medium_risk, low_risk, risk_styles):
    df = pd.DataFrame(detected_fields)

    def classify_field_risk(field_name):
        name = field_name.upper()
        if name in high_risk:
            return "High"
        elif name in medium_risk:
            return "Medium"
        elif name in low_risk:
            return "Low"
        return "None"

    df["Nivel de riesgo"] = df["field"].apply(classify_field_risk)
    df["risk_order"] = df["Nivel de riesgo"].map({"High": 0, "Medium": 1, "Low": 2, "None": 3})
    df = df.sort_values("risk_order").drop(columns="risk_order")

    color_map = {k: v[1] for k, v in risk_styles.items()}
    risk_label_map = {
        "High": "🔴 Alto",
        "Medium": "🟠 Medio",
        "Low": "🟢 Bajo",
        "None": "⚪ Ninguno"
    }

    def format_field(row):
        color = color_map.get(row["Nivel de riesgo"], "#B0B0B0")
        return f"<span style='background-color:{color}; color:white; padding:3px 6px; border-radius:4px'>{row['field']}</span>"

    def format_risk(row):
        return f"<b>{risk_label_map.get(row['Nivel de riesgo'], '❓')}</b>"

    df["Campo"] = df.apply(format_field, axis=1)
    df["Valor"] = df["value"]
    df["Fuente"] = df["source"]
    df["Nivel de riesgo"] = df.apply(format_risk, axis=1)

    return df[["Campo", "Valor", "Fuente", "Nivel de riesgo"]]


# --- Interfaz Streamlit ---
st.set_page_config(page_title="Análisis de Datos Sensibles", layout="wide")
st.title("🔐 Análisis de privacidad en entradas y respuestas LLM con gpt-4o")
st.markdown("Detecta campos sensibles en texto o imágenes y evalúa el riesgo antes de enviarlos a Gemini.")

# --- Estilos de riesgo ---
RISK_STYLES = {
    "High": ("Alto", "#FF4B4B"),
    "Medium": ("Medio", "#FBAE17"),
    "Low": ("Bajo", "#00A86B"),
    "None": (" Ninguno", "gray")
}
RISK_BUTTON_STYLES = {k: f"{v[0]} Sí, enviar a LLM" for k, v in RISK_STYLES.items()}

# --- Entrada de texto ---
mode = st.sidebar.radio("Entrada:", ["Texto manual", "Archivo (.pdf/txt)", "Imagen"])
text_content = ""

if mode == "Texto manual":
    text_content = st.text_area("✍️ Ingresa texto:", height=300)

elif mode == "Archivo (.pdf/txt)":
    f = st.sidebar.file_uploader("Sube PDF/TXT", type=["pdf", "txt"])
    if f:
        with open(f"tmp_{f.name}", "wb") as tmp:
            tmp.write(f.read())
        text_content = read_document(tmp.name) or ""
        text_content = st.text_area("📖 Texto extraído:", value=text_content, height=300)

elif mode == "Imagen":
    imgf = st.sidebar.file_uploader("🖼️ Sube imagen", type=["png", "jpg", "jpeg"])
    if imgf:
        image = Image.open(io.BytesIO(imgf.read()))
        st.image(image, caption="Imagen cargada", use_container_width=True)

        with st.spinner("🧠 Analizando imagen con MiniGPT-4..."):
            image.save("input_image.jpg")
            text_content = generate_description("input_image.jpg")
            text_content = st.text_area("📖 Texto extraído:", value=text_content, height=300)

# --- Prompting mode ---
def load_prompt_files():
    zs_prompt = ""
    zs_enriquecido_prompt = ""
    fs_prompt = ""

    paths = {
        "ZS_prompt": PROMPT_DIR / "ZS_prompt.txt",
        "ZS_enriquecido_prompt": PROMPT_DIR / "ZS_enriquecido_prompt.txt",
        "FS_prompt": PROMPT_DIR / "FS_prompt.txt",
    }

    if paths["ZS_prompt"].exists():
        zs_prompt = paths["ZS_prompt"].read_text(encoding="utf-8")
    if paths["ZS_enriquecido_prompt"].exists():
        zs_enriquecido_prompt = paths["ZS_enriquecido_prompt"].read_text(encoding="utf-8")
    if paths["FS_prompt"].exists():
        fs_prompt = paths["FS_prompt"].read_text(encoding="utf-8")

    return zs_prompt, zs_enriquecido_prompt, fs_prompt


def get_prompt(mode: str):
    zs, zs_enriquecido, fs = load_prompt_files()
    if mode == "Zero-shot":
        return zs
    elif mode == "Zero-shot enriquecido":
        return zs_enriquecido
    elif mode == "Few-shot":
        return fs
    else:
        return zs  # fallback

mode_p = st.sidebar.radio("Prompting:", ["Zero-shot", "Zero-shot enriquecido", "Few-shot"])
custom_prompt = get_prompt(mode_p)
st.sidebar.text_area("📄 Prompt actual:", custom_prompt, height=250)

# Riesgos clasificados
HIGH_RISK = {"PASSWORD", "CREDENTIALS", "SSN", "DNI", "PASSPORTNUMBER", "CREDITCARDNUMBER", "IP", "IPv4", "IPv6", "MAC", "CREDITCARDCVV", "ACCOUNTNUMBER", "IBAN", "PIN", "GENETICDATA", "BIOMETRICDATA", "STREET", "VEHICLEVIN", "HEALTHDATA", "CRIMINALRECORD", "CONFIDENTIALDOC", "LITECOINADDRESS", "BITCOINADDRESS", "ETHEREUMADDRESS", "PHONEIMEI"}
MEDIUM_RISK = {"EMAIL", "PHONENUMBER", "URL", "CLIENTDATA", "EMPLOYEEDATA", "SALARYDETAILS", "COMPANYNAME", "JOBTITLE", "JOBTYPE", "JOBAREA", "ACCOUNTNAME", "PROJECTNAME", "CODENAME", "EDUCATIONHISTORY", "CV", "SOCIALMEDIAHANDLE", "SECONDARYADDRESS", "CITY", "STATE", "COUNTY", "ZIPCODE", "BUILDINGNUMBER", "USERAGENT", "VEHICLEVRM", "NEARBYGPSCOORDINATE", "BIC", "MASKEDNUMBER", "AMOUNT", "CURRENCY", "CURRENCYSYMBOL", "CURRENCYNAME", "CURRENCYCODE", "CREDITCARDISSUER", "USERNAME", "INFRASTRUCTURE"}
LOW_RISK = {"PREFIX", "FIRSTNAME", "MIDDLENAME", "LASTNAME", "AGE", "DOB", "GENDER", "SEX", "HAIRCOLOR", "EYECOLOR", "HEIGHT", "WEIGHT", "SKINTONE", "OTHER FEATURES", "RACIALORIGIN", "RELIGION", "POLITICALOPINION", "PHILOSOPHICALBELIEF", "TRADEUNION", "DATE", "TIME", "ORDINALDIRECTION", "SEXUALORIENTATION", "CHILDRENDATA", "LEGALDISCLOSURE"}

# --- Resaltado de texto ---
def highlight_sensitive_data(text, detected_fields):
    detected_fields = sorted(detected_fields, key=lambda x: len(x["value"]), reverse=True)

    def get_color(field_name):
        if field_name in HIGH_RISK:
            return RISK_STYLES["High"][1]
        elif field_name in MEDIUM_RISK:
            return RISK_STYLES["Medium"][1]
        elif field_name in LOW_RISK:
            return RISK_STYLES["Low"][1]
        return RISK_STYLES["None"][1]

    spans, used_ranges = [], []
    for field in detected_fields:
        value = field["value"]
        color = get_color(field["field"].strip().upper())
        matches = list(re.finditer(re.escape(value), text, flags=re.IGNORECASE))
        for match in matches:
            start, end = match.start(), match.end()
            if not any(us <= start < ue or us < end <= ue for us, ue in used_ranges):
                spans.append({
                    "start": start,
                    "end": end,
                    "replacement": f"<mark style='background-color:{color}; padding:2px 6px; border-radius:4px; font-weight:500'>{escape(text[start:end])}</mark>"
                })
                used_ranges.append((start, end))
                break

    for span in sorted(spans, key=lambda x: x["start"], reverse=True):
        text = text[:span["start"]] + span["replacement"] + text[span["end"]:]

    return text

# --- Análisis de riesgo ---
if st.button("📊 Analizar texto"):
    if not text_content.strip():
        st.warning("Texto vacío.")
    else:
        pii = detect_sensitive_data(text_content, prompt=custom_prompt)
        level = compute_risk_level(pii.get("detected_fields", []))
        pii["risk_level"] = level
        st.session_state.update(pii_data=pii, level=level, text=text_content)

        lbl, color = RISK_STYLES.get(level, ("❓", "gray"))
        st.markdown(f"### 🚨 <span style='color:{color}; font-weight:bold'>Nivel de riesgo: {lbl}</span>", unsafe_allow_html=True)


        if pii["detected_fields"]:
            highlighted_text = highlight_sensitive_data(text_content, pii["detected_fields"])
            st.markdown("### 🖍️ Texto con datos sensibles resaltados")
            components.html(
                f"""
                <div style='font-family: sans-serif; line-height: 1.4; margin: 0; padding: 0;'>
                    {highlighted_text}
                </div>
                """,
                height=200,
                scrolling=True
            )

            st.markdown("<div style='margin-top: -1.5rem; margin-bottom: -1rem;'></div>", unsafe_allow_html=True)
           # Crear DataFrame
            df = pd.DataFrame(pii["detected_fields"])

            # Clasificación de riesgo
            def classify_field_risk(field_name):
                name = field_name.upper()
                if name in HIGH_RISK:
                    return "High"
                elif name in MEDIUM_RISK:
                    return "Medium"
                elif name in LOW_RISK:
                    return "Low"
                return "None"

            # Agregar columnas de riesgo
            df["Nivel de riesgo"] = df["field"].apply(classify_field_risk)
            df["risk_order"] = df["Nivel de riesgo"].map({"High": 0, "Medium": 1, "Low": 2, "None": 3})
            df = df.sort_values("risk_order").drop(columns="risk_order")

            # Formato visual
            color_map = {k: v[1] for k, v in RISK_STYLES.items()}
            risk_label_map = {
                "High": "🔴 Alto",
                "Medium": "🟠 Medio",
                "Low": "🟢 Bajo",
                "None": "⚪ Ninguno"
            }

            def format_field(row):
                color = color_map.get(row["Nivel de riesgo"], "#B0B0B0")
                return f"<span style='background-color:{color}; color:white; padding:3px 6px; border-radius:4px'>{row['field']}</span>"

            def format_risk(row):
                return f"<b>{risk_label_map.get(row['Nivel de riesgo'], '❓')}</b>"

            df["Campo"] = df.apply(format_field, axis=1)
            df["Valor"] = df["value"]
            df["Fuente"] = df["source"]
            df["Nivel de riesgo"] = df.apply(format_risk, axis=1)

            # Mostrar tabla
            st.markdown("### 📌 Campos Detectados")
            st.markdown(
                df[["Campo", "Valor", "Fuente", "Nivel de riesgo"]].to_html(escape=False, index=False),
                unsafe_allow_html=True
            )
if "pii_data" in st.session_state:
    pii, level, txt = st.session_state["pii_data"], st.session_state["level"], st.session_state["text"]
    
    st.markdown("### ❓ ¿Estás seguro de que quieres enviar este texto a Gemini?")

    col1, col2 = st.columns(2)
    with col1:
        send_clicked = st.button("✅ Sí, enviar a LLM", key="send_to_llm")
    with col2:
        cancel_clicked = st.button("❌ No, cancelar", key="cancel_send")

    if send_clicked:
        st.markdown("## 📤 Enviando a Gemini...")
        with st.spinner("Generando respuesta..."):
            resp = generate_response_with_gemini(txt)
        st.text_area("🧠 Respuesta LLM:", value=resp, height=300)
        

        with st.spinner("🔎 Analizando respuesta..."):
            rpii = detect_sensitive_data(resp, prompt=custom_prompt)
            # Mostrar texto con datos sensibles resaltados en la respuesta
            highlighted_resp = highlight_sensitive_data(resp, rpii["detected_fields"])
            st.markdown("### 🖍️ Texto en respuesta con datos sensibles resaltados")
            components.html(
                f"<div style='line-height: 1.6; font-size: 1rem'>{highlighted_resp}</div>",
                height=250,
                scrolling=True
            )
            
            rl = compute_risk_level(rpii.get("detected_fields", []))
            lbl_resp, color_resp = RISK_STYLES.get(rl, ("❓", "gray"))
            st.markdown(
                f"""
                <div style='padding: 12px 20px; background-color: {color_resp}; color: white;
                            font-weight: bold; border-radius: 8px; width: fit-content;
                            margin-top: 1rem; margin-bottom: 1rem; font-size: 1.1rem'>
                    🔎 Riesgo en respuesta: {lbl_resp}
                </div>
                """,
                unsafe_allow_html=True
            )

            if rpii.get("detected_fields"):
                st.markdown("### 📌 Campos Detectados en la Respuesta")
                tabla = format_response_table(
                detected_fields=rpii["detected_fields"],
                high_risk=HIGH_RISK,
                medium_risk=MEDIUM_RISK,
                low_risk=LOW_RISK,
                risk_styles=RISK_STYLES
            )
            st.markdown(tabla.to_html(escape=False, index=False), unsafe_allow_html=True)
