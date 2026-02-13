import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# 1. Configuración de la Interfaz (Streamlit) - DEBE IR AL PRINCIPIO
st.set_page_config(page_title="Red Flag Scanner", page_icon="🚩")

# 2. Pedir la clave al usuario (sidebar)
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input(
    "API key de Gemini",
    type="password",
    placeholder="Pega aquí tu API key…",
)

# 3. Bloquear la app hasta que haya clave
if not api_key:
    st.info("Introduce tu API key en la barra lateral para empezar.")
    st.stop()

# 4. Crear el cliente de Gemini (Nuevo SDK)
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Error al conectar con Gemini: {e}")
    st.stop()

# --- DISEÑO DE LA APP ---

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

# Entrada de datos (Texto o Imagen)
tab1, tab2 = st.tabs(["Escribir Mensaje", "Subir Captura"])

with tab1:
    texto_input = st.text_area("Pega el mensaje aquí:", placeholder="Ej: 'No quiero etiquetas por ahora...'")

with tab2:
    imagen_input = st.file_uploader("Sube el pantallazo:", type=["png", "jpg", "jpeg"])
    if imagen_input:
        st.image(imagen_input, caption="Evidencia cargada", width=300)

# 5. Lógica de Análisis (Corregida para el nuevo SDK)
if st.button("🔍 ESCANEAR VIBRAS"):
    
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
                # El nuevo SDK acepta la imagen de PIL directamente en una lista
                img = Image.open(imagen_input)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[prompt_base, img]
                )
            elif texto_input:
                # Caso solo texto
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{prompt_base}\n\nMensaje a analizar: {texto_input}"
                )
            else:
                st.warning("Necesito un mensaje o una imagen para trabajar, no soy adivino (todavía).")
                st.stop()

            # Mostrar resultado
            st.subheader("🕵️‍♂️ Informe del Detective:")
            st.markdown("---")
            st.markdown(response.text)
            
    except Exception as e:
        st.error(f"Hubo un error en el análisis: {e}")

# Pie de página
st.markdown("---")
st.caption("Usa esta app bajo tu propio riesgo. La IA no se hace responsable de bloqueos en WhatsApp.")


