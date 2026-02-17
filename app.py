import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import re
import io

# ============================================================
# CONFIGURACIÓN DE MODELOS
# ============================================================
TEXT_MODEL_ID = "gemini-2.5-flash"  # Rápido para transcripción y JSON
IMAGE_MODEL_ID = "gemini-3-pro-image-preview" # El modelo que solicitaste

st.set_page_config(page_title="Detective Red Flag AI", page_icon="🚩", layout="centered")

# --- Barra Lateral (Configuración) ---
with st.sidebar:
    st.header("🔑 Seguridad y Estilo")
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("🕵️ Ajustes del Detective")
    personalidad = st.selectbox(
        "Tono del Análisis:",
        ["Psicólogo Profesional", "Sarcástico y Ácido", "Mejor Amigo 'Sin Filtro'"]
    )
    st.caption("El tono cambiará cómo la IA interpreta y te responde.")

if not api_key:
    st.info("Introduce tu API Key de Google AI Studio para activar al detective.")
    st.stop()

# Configuración global de Google AI
genai.configure(api_key=api_key)

# --- Funciones de Interfaz ---
def card(title, body, border_color="#e5e7eb"):
    st.markdown(f"""
        <div style="border: 1px solid {border_color}; border-left: 6px solid {border_color}; 
                    padding: 15px; background: white; border-radius: 12px; margin: 10px 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div style="font-weight: bold; color: #333; margin-bottom: 5px;">{title}</div>
            <div style="font-size: 0.95em; color: #555; line-height: 1.4;">{body}</div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================
st.title("🚩 Detective de Red Flags")
st.write(f"Modo actual: **{personalidad}**")

tab1, tab2 = st.tabs(["💬 Pegar Chat", "📸 Subir Captura"])
analysis_text = ""

with tab1:
    texto_input = st.text_area("Pega los mensajes sospechosos:", height=150, placeholder="Ej: 'No quiero etiquetas ahora mismo...'")
    if texto_input:
        analysis_text = texto_input

with tab2:
    file = st.file_uploader("Sube el pantallazo del chat:", type=["png", "jpg", "jpeg"])
    if file:
        img = Image.open(file)
        st.image(img, width=300, caption="Evidencia cargada")
        if st.button("🔍 Transcribir Imagen"):
            with st.spinner("La IA está leyendo los mensajes..."):
                ocr_model = genai.GenerativeModel(TEXT_MODEL_ID)
                response_ocr = ocr_model.generate_content(["Transcribe este chat de forma exacta, sin comentarios adicionales.", img])
                analysis_text = response_ocr.text
                st.success("Texto extraído correctamente.")
                st.text_area("Texto detectado:", value=analysis_text, height=100)

# ============================================================
# BOTÓN DE ACCIÓN: ANÁLISIS + GENERACIÓN DE IMAGEN
# ============================================================
if st.button("🚀 ESCANEAR VIBRAS"):
    if not analysis_text:
        st.warning("Necesito un texto o una imagen para trabajar.")
        st.stop()

    try:
        # 1. ANALISIS DE TEXTO CON EL TONO ELEGIDO
        with st.spinner(f"Analizando como {personalidad}..."):
            model_text = genai.GenerativeModel(TEXT_MODEL_ID)
            prompt_analisis = f"""
            Actúa como un {personalidad}. Analiza el siguiente chat y detecta señales de alerta (Red Flags).
            CHAT: "{analysis_text}"
            
            Devuelve un JSON estrictamente con este formato:
            {{
                "riesgo": (int 0-100),
                "nivel": "Bajo|Medio|Alto",
                "veredicto": "Resumen del análisis con tu tono de {personalidad}",
                "traduccion": "Lo que realmente quiere decir esa persona",
                "prompt_arte": "Una descripción artística y metafórica para generar una imagen sobre este análisis."
            }}
            """
            res_json = model_text.generate_content(prompt_analisis)
            data = json.loads(re.search(r"\{.*\}", res_json.text, re.DOTALL).group())

        # Mostrar Informe
        st.subheader("🕵️ Resultado del Escaneo")
        col_m, col_v = st.columns([1, 2])
        
        with col_m:
            st.metric("Nivel de Red Flags", f"{data['riesgo']}%", data['nivel'])
            st.progress(data['riesgo'])
        
        with col_v:
            color = "#dc2626" if data['riesgo'] > 60 else "#f59e0b" if data['riesgo'] > 30 else "#16a34a"
            card(f"Veredicto del {personalidad}", data['veredicto'], border_color=color)

        card("🧠 Traductor de Realidad", data['traduccion'], border_color="#60a5fa")

        # 2. GENERACIÓN DE IMAGEN CON GEMINI 3 PRO IMAGE
        st.divider()
        st.subheader(f"🎨 Visualización (Modelo: {IMAGE_MODEL_ID})")
        
        with st.spinner("Generando representación visual..."):
            model_img = genai.GenerativeModel(IMAGE_MODEL_ID)
            # Llamamos al modelo que pediste para generar la imagen a partir del prompt creado
            res_img = model_img.generate_content(data['prompt_arte'])
            
            img_found = False
            for part in res_img.candidates[0].content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    st.image(img_bytes, caption="Representación visual de la Red Flag", use_column_width=True)
                    
                    st.download_button(
                        label="📥 Descargar esta Imagen",
                        data=img_bytes,
                        file_name="red_flag_visual.png",
                        mime="image/png"
                    )
                    img_found = True
            
            if not img_found:
                st.info(f"El modelo no devolvió una imagen directa. Prompt generado: {data['prompt_arte']}")

    except Exception as e:
        st.error(f"Error en el proceso: {e}")
        st.info("Asegúrate de que tu API Key tenga permisos para los modelos seleccionados.")



