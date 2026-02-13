import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1) Pedir la clave al usuario (sidebar)
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input(
    "API key de Gemini",
    type="password",
    placeholder="Pega aquí tu API key…",
)

# 2) Bloquear la app hasta que haya clave
if not api_key:
    st.info("Introduce tu API key en la barra lateral para empezar.")
    st.stop()

# 3) Configurar Gemini solo cuando hay clave
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"No se pudo configurar la API key: {e}")
    st.stop()

# Configuración del modelo (usamos Flash por ser rápido y eficiente)
model = genai.GenerativeModel( "models/gemini-2.0-flash")

# 2. Configuración de la Interfaz (Streamlit)
st.set_page_config(page_title="Red Flag Scanner", page_icon="🚩")

st.title("🚩 Detective de Red Flags 2.0")
st.markdown("¿Te están haciendo *ghosting* o solo es *delulu*? Vamos a descubrirlo.")

# Barra lateral para opciones
with st.sidebar:
    st.header("Ajustes del Detective")
    personalidad = st.selectbox(
        "Tono del análisis:",
        ["Sarcástico y Ácido", "Psicólogo Profesional", "Mejor Amigo 'Sin Filtro'"]
    )
    st.info("Sugerencia: Sube una captura de pantalla de WhatsApp para un análisis más real.")

# 3. Entrada de datos (Texto o Imagen)
tab1, tab2 = st.tabs(["Escribir Mensaje", "Subir Captura"])

with tab1:
    texto_input = st.text_area("Pega el mensaje aquí:", placeholder="Ej: 'No quiero etiquetas por ahora...'")

with tab2:
    imagen_input = st.file_uploader("Sube el pantallazo:", type=["png", "jpg", "jpeg"])
    if imagen_input:
        st.image(imagen_input, caption="Evidencia cargada", width=300)

# 4. Lógica de Análisis
if st.button("🔍 ESCANEAR VIBRAS"):
    
    # Construcción del Prompt Maestro
    prompt_base = f"""
    Actúa como un experto en relaciones modernas y lenguaje digital con un tono {personalidad}.
    Analiza la comunicación proporcionada (texto o imagen).
    
    Tu misión es entregar:
    1. **Termómetro de Red Flag**: Un porcentaje del 0% al 100%.
    2. **Traductor de Realidad**: ¿Qué dice el texto vs qué significa realmente en el mundo de las citas?
    3. **Análisis de Manipulación**: Identifica tácticas como gaslighting, love bombing o breadcrumbing si las hay.
    4. **Plan de Acción**: Una respuesta sugerida (brillante y empoderada).
    """

    try:
        with st.spinner('Analizando el subtexto...'):
            if imagen_input:
                # Si hay imagen, Gemini la analiza
                img = Image.open(imagen_input)
                response = model.generate_content([prompt_base, img])
            elif texto_input:
                # Si es solo texto
                response = model.generate_content(f"{prompt_base}\n\nMensaje a analizar: {texto_input}")
            else:
                st.warning("Necesito un mensaje o una imagen para trabajar, no soy adivino (todavía).")
                st.stop()

            # Mostrar resultado
            st.subheader("🕵️‍♂️ Informe del Detective:")
            st.markdown("---")
            st.markdown(response.text)
            
    except Exception as e:
        st.error(f"Hubo un error: {e}")

# 5. Pie de página
st.markdown("---")
st.caption("Usa esta app bajo tu propio riesgo. La IA no se hace responsable de bloqueos en WhatsApp.")