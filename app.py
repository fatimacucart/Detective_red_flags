import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import re
import unicodedata

# ============================================================
# CONFIG FIJA (el usuario NO toca nada)
# ============================================================
MODEL_ID = "models/gemini-2.0-flash"
K_DOCS = 3 # palabras que va a coger de los datos
THRESHOLD = 0.08 #similitud de al menos 0.8

# ============================================================
# UI: Tarjetas con borde de color
# ============================================================
def card(title: str, body_html: str, border_color: str = "#e5e7eb"):
    st.markdown(
        f"""
        <div style="
            border: 1px solid {border_color};
            border-left: 6px solid {border_color};
            border-radius: 14px;
            padding: 14px 16px;
            margin: 10px 0;
            background: white;
            box-shadow: 0 1px 10px rgba(0,0,0,0.04);
        ">
            <div style="font-weight: 700; font-size: 16px; margin-bottom: 8px;">{title}</div>
            <div style="font-size: 14px; line-height: 1.45;">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# Helpers: JSON + riesgo
# ============================================================
def extract_json(text: str): #extraer un JSON limpio
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        return m.group(1)
    m = re.search(r"(\{.*\})", text, flags=re.S)
    if m:
        return m.group(1)
    return None

def clamp_int(x, lo=0, hi=100): #convierte a valor entero y comprueba que esté dentro de un umbral "válido"
    try:
        x = int(x)
    except Exception:
        x = 0
    return max(lo, min(hi, x))

def risk_color_hex(pct: int) -> str:
    if pct < 34:
        return "#16a34a"  # verde
    if pct < 67:
        return "#f59e0b"  # ámbar
    return "#dc2626"      # rojo

def risk_label(pct: int) -> str:
    if pct < 34:
        return "Bajo"
    if pct < 67:
        return "Medio"
    return "Alto"

# ============================================================
# “Vocabulario ampliado”: normalización + keywords por patrón
# ============================================================
def normalize(text: str) -> str:
    """Minúsculas + sin tildes + limpia espacios."""
    text = (text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")  # quita tildes
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str):
    text = normalize(text)
    return set(re.findall(r"[a-z0-9ñ]+", text))

def jaccard(a: set, b: set) -> float: #Mide qué porcentaje de palabras comparten dos textos.
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

#“¿Qué fragmentos de mi base de conocimiento son relevantes para el mensaje del usuario?”
def retrieve_knowledge(query: str, knowledge: list, k: int = 3, threshold: float = 0.08):
    """
    Retrieval básico: Jaccard sobre tokens (title+content+keywords).
    Devuelve hits con score >= threshold, top-k.
    """
    
    q = tokenize(query)
    scored = []
    for item in knowledge:
        doc_text = " ".join([
            item.get("title", ""),
            item.get("content", ""),
            " ".join(item.get("keywords", []))
        ])
        doc = tokenize(doc_text)
        score = jaccard(q, doc)
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    hits = []
    for score, item in scored:
        if score >= threshold:
            hits.append({**item, "score": score})
        if len(hits) >= k:
            break

    max_score = scored[0][0] if scored else 0.0
    return hits, max_score

def build_rag_context(hits: list) -> str:
    if not hits:
        return ""
    return "\n\n".join([f"[{h['title']}] {h['content']}" for h in hits])

# ============================================================
# Tu base de conocimiento (RAG)
# (Aquí es donde amplías vocabulario: keywords)
# ============================================================
KNOWLEDGE = [
    {
        "title": "Ambigüedad intencional",
        "keywords": [
            "ya veremos", "lo que surja", "sin etiquetas", "no quiero nada serio",
            "vamos viendo", "fluimos", "no busco nada", "ahora mismo no",
            "no se", "quizas", "depende", "no prometo nada"
        ],
        "content": (
            "Mantener la puerta abierta sin definir intención. Señales: mensajes vagos, "
            "evita concretar, contradicciones entre lo que dice y hace. "
            "Respuesta: pedir claridad con una pregunta concreta y alinear expectativas."
        ),
    },
    {
        "title": "Breadcrumbing",
        "keywords": [
            "luego hablamos", "otro dia", "cuando pueda", "ando liad", "estoy a mil",
            "te escribo luego", "no desaparezco", "perdon colgue", "te digo algo", "ya te dire"
        ],
        "content": (
            "Mantener interés sin compromiso real. Señales: contacto intermitente, "
            "promesas vagas, evita planes concretos. Respuesta útil: pedir claridad y proponer una acción "
            "con fecha; si no hay respuesta, tomar distancia."
        ),
    },
    {
        "title": "Presión / Urgencia",
        "keywords": [
            "contesta ya", "ahora", "si no respondes", "ultima oportunidad", "decidete",
            "demuestrame", "si me quisieras", "no me hagas esperar"
        ],
        "content": (
            "Empujar a decidir rápido o responder de inmediato. Señales: ultimátums, exigencias, "
            "chantaje emocional. Respuesta: poner un límite claro y mantener tu ritmo."
        ),
    },
    {
        "title": "Love bombing",
        "keywords": [
            "alma gemela", "eres perfecta", "nunca senti esto", "te amo", "para siempre",
            "en serio contigo", "en pocos dias", "exclusividad ya", "solo tu"
        ],
        "content": (
            "Intensidad afectiva rápida para acelerar vínculo. Señales: halagos desmedidos, prisa por exclusividad, "
            "reacciones fuertes cuando pones límites. Recomendación: bajar ritmo y observar consistencia en el tiempo."
        ),
    },
    {
        "title": "Gaslighting (modo prudente)",
        "keywords": [
            "estas exagerando", "te lo inventas", "estas loca", "no paso", "te lo imaginas",
            "siempre lo haces", "yo nunca dije eso"
        ],
        "content": (
            "Hacerte dudar de tu percepción. Señales: negar hechos claros, minimizar lo que sientes, "
            "cambiar la versión. Importante: no diagnosticar; describir el patrón, pedir claridad y cuidar límites."
        ),
    },
]

# ============================================================
# Gemini helpers
# ============================================================
def transcribe_chat_from_image(model, img: Image.Image) -> str:
    """
    Extrae/transcribe texto de un chat en una captura (sin comentarios).
    """
    ocr_prompt = (
        "Extrae y transcribe el texto visible del chat en la imagen.\n"
        "Devuelve SOLO el texto, manteniendo saltos de línea si es posible.\n"
        "No añadas comentarios ni interpretación."
    )
    resp = model.generate_content([ocr_prompt, img])
    return (resp.text or "").strip()

# ============================================================
# APP
# ============================================================
st.set_page_config(page_title="Red Flag Scanner (Gemini + RAG)", page_icon="🚩")

st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("API key de Gemini", type="password", placeholder="Pega aquí tu API key…")

if not api_key:
    st.info("Introduce tu API key en la barra lateral para empezar.")
    st.stop()

try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"No se pudo configurar la API key: {e}")
    st.stop()

model = genai.GenerativeModel(MODEL_ID)

st.title("🚩 Detective de Red Flags (Gemini + RAG automático)")
st.markdown(
    "Puedes pegar un mensaje o subir una captura. "
    "Si el RAG encuentra coincidencias en tu base, las usa; si no, responde con análisis general y prudente."
)

with st.sidebar:
    st.header("Ajustes del Detective")
    personalidad = st.selectbox(
        "Tono del análisis:",
        ["Sarcástico y Ácido", "Psicólogo Profesional", "Mejor Amigo 'Sin Filtro'"]
    )
    st.caption(f"RAG fijo: top-{K_DOCS} con umbral {THRESHOLD:.2f} (automático).")

tab1, tab2 = st.tabs(["Escribir Mensaje", "Subir Captura"])

texto_input = ""
imagen_input = None

with tab1:
    texto_input = st.text_area("Pega el mensaje aquí:", placeholder="Ej: 'No quiero etiquetas por ahora...'")

with tab2:
    imagen_input = st.file_uploader("Sube el pantallazo:", type=["png", "jpg", "jpeg"])
    if imagen_input:
        st.image(imagen_input, caption="Evidencia cargada", width=320)

# Prompt base (JSON)
prompt_base = f"""
Actúa como un experto en relaciones modernas y lenguaje digital con un tono {personalidad}.
Analiza la comunicación proporcionada.

Devuelve EXCLUSIVAMENTE un JSON válido (sin texto extra) con esta estructura:

{{
  "termometro_red_flag": {{
    "porcentaje": 0,
    "nivel": "Bajo|Medio|Alto",
    "razon_breve": "..."
  }},
  "traductor_de_realidad": {{
    "que_dice": "...",
    "que_podria_significar": "...",
    "incertidumbre": "Baja|Media|Alta"
  }},
  "senales_detectadas": [
    {{
      "senal": "...",
      "evidencia": "frase/patron específico",
      "gravedad": "Baja|Media|Alta"
    }}
  ],
  "tacticas_manipulacion": [
    {{
      "tactica": "gaslighting|love bombing|breadcrumbing|culpabilizacion|ambiguedad_intencional|presion|otra",
      "por_que": "..."
    }}
  ],
  "plan_de_accion": {{
    "respuesta_sugerida": "...",
    "limite_recomendado": "...",
    "siguiente_paso": "..."
  }},
  "disclaimer": "..."
}}

Reglas:
- No diagnostiques ni afirmes certezas absolutas: usa lenguaje prudente (“podría”, “parece”, “es compatible con…”).
- Si faltan datos, refleja incertidumbre y sugiere 1-2 preguntas útiles.
- Si el CONTEXTO RAG está vacío, NO fuerces patrones del documento y sube la incertidumbre.
"""

if st.button("🔍 ESCANEAR VIBRAS"):
    try:
        with st.spinner("Analizando..."):
            # 1) Determinar texto a analizar
            analysis_text = ""
            if imagen_input:
                img = Image.open(imagen_input)
                analysis_text = transcribe_chat_from_image(model, img)
                if not analysis_text:
                    st.warning("No pude extraer texto de la captura. Prueba con otra imagen más nítida.")
                    st.stop()
            else:
                analysis_text = (texto_input or "").strip()
                if not analysis_text:
                    st.warning("Necesito un mensaje o una captura para trabajar.")
                    st.stop()

            # 2) Retrieval automático (RAG)
            hits, _ = retrieve_knowledge(analysis_text, KNOWLEDGE, k=K_DOCS, threshold=THRESHOLD)
            rag_context = build_rag_context(hits)
            rag_used = bool(rag_context)
            rag_block = rag_context if rag_used else "(vacío) No se recuperó nada relevante por encima del umbral."

            # UI: qué contexto se usó
            if rag_used:
                items = "<ul style='margin:0 0 0 18px;'>" + "".join(
                    [f"<li><strong>{h['title']}</strong> (score: {h['score']:.2f})</li>" for h in hits]
                ) + "</ul>"
                card("📚 Contexto RAG usado", items, border_color="#0ea5e9")
            else:
                card("📚 Contexto RAG usado", "0 fuentes → análisis general (sin apoyo del documento).", border_color="#94a3b8")

            # 3) Prompt final + llamada a Gemini (solo texto, ya tenemos transcripción)
            prompt_final = f"""{prompt_base}

RAG_USED: {str(rag_used).lower()}

CONTEXTO RAG:
{rag_block}

MENSAJE:
{analysis_text}
"""
            resp = model.generate_content(prompt_final)
            raw = resp.text or ""

        st.subheader("🕵️‍♂️ Informe del Detective")
        st.markdown("---")

        # 4) Parse JSON con fallback
        json_str = extract_json(raw) or raw
        try:
            data = json.loads(json_str)
        except Exception:
            data = None

        if not data:
            st.warning("No pude estructurar la respuesta como JSON. Muestro el informe en texto:")
            st.markdown(raw)
            st.stop()

        # 5) Render cards
        term = data.get("termometro_red_flag", {}) or {}
        pct = clamp_int(term.get("porcentaje", 0))
        level = term.get("nivel") or risk_label(pct)
        color = risk_color_hex(pct)

        colA, colB = st.columns([1, 1])
        with colA:
            st.metric("Termómetro de Red Flags", f"{pct}%", level)
            st.progress(pct)
        with colB:
            card("🌡️ Lectura rápida",
                 f"<strong>Nivel:</strong> {level}<br><strong>Por qué:</strong> {term.get('razon_breve','—')}",
                 border_color=color)

        tr = data.get("traductor_de_realidad", {}) or {}
        card(
            "🧠 Traductor de realidad",
            f"<strong>Qué dice:</strong> {tr.get('que_dice','—')}<br><br>"
            f"<strong>Qué podría significar:</strong> {tr.get('que_podria_significar','—')}<br><br>"
            f"<strong>Incertidumbre:</strong> {tr.get('incertidumbre','—')}",
            border_color="#60a5fa"
        )

        senales = data.get("senales_detectadas", []) or []
        if senales:
            html_items = "<ul style='margin: 0 0 0 18px;'>" + "".join(
                [f"<li><strong>{s.get('senal','')}</strong> (<em>{s.get('gravedad','')}</em>)<br>"
                 f"<span style='opacity:0.9;'>Evidencia: {s.get('evidencia','')}</span></li>"
                 for s in senales[:8]]
            ) + "</ul>"
        else:
            html_items = "<em>No se detectan señales claras con la información actual.</em>"
        card("🚩 Señales detectadas", html_items, border_color="#fb7185")

        tacticas = data.get("tacticas_manipulacion", []) or []
        if tacticas:
            html_t = "<ul style='margin: 0 0 0 18px;'>" + "".join(
                [f"<li><strong>{t.get('tactica','')}</strong>: {t.get('por_que','')}</li>"
                 for t in tacticas[:8]]
            ) + "</ul>"
        else:
            html_t = "<em>No se identifican tácticas claras (por ahora).</em>"
        card("🎭 Posibles tácticas", html_t, border_color="#a78bfa")

        pa = data.get("plan_de_accion", {}) or {}
        card(
            "🧩 Plan de acción",
            f"<strong>Respuesta sugerida:</strong><br>{pa.get('respuesta_sugerida','—')}<br><br>"
            f"<strong>Límite recomendado:</strong><br>{pa.get('limite_recomendado','—')}<br><br>"
            f"<strong>Siguiente paso:</strong><br>{pa.get('siguiente_paso','—')}",
            border_color="#34d399"
        )

        st.caption(data.get("disclaimer", "Usa esta app con criterio. La IA no sustituye apoyo profesional."))

    except Exception as e:
        st.error(f"Hubo un error: {e}")

st.markdown("---")
st.caption("Tip: amplía 'keywords' en KNOWLEDGE para mejorar el vocabulario del RAG.")



