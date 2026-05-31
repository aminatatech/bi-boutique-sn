import streamlit as st
import pandas as pd
from groq import Groq
from PIL import Image
import io
import base64
import plotly.express as px
import urllib.parse
import hashlib

# --- 1. CONFIGURATION DU CLIENT GROQ ---
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=API_KEY)
    MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct" 
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# --- 2. CONFIGURATION DE LA PAGE & STYLE MODERNE ---
st.set_page_config(
    page_title="Business Intelligence Dashboard", 
    layout="wide", 
    page_icon="📈"
)

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .main-header { font-size: 2.5rem; color: #0F172A; font-weight: 800; }
    .sub-header { font-size: 1.1rem; color: #64748B; margin-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #2563EB; font-weight: 700; }
    div[data-testid="metric-container"] { background-color: white; padding: 1.5rem; border-radius: 12px; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #2563EB; color: white; }
    </style>
    """, unsafe_allow_html=True)

def calculate_image_hash(img_file):
    return hashlib.md5(img_file.getvalue()).hexdigest()

def encode_image_to_base64(img_file):
    image = Image.open(img_file)
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 3. FONCTION SCANNEUSE ULTRA-ROBUSTE & PRÉCISE ---
def extract_data(images):
    all_data = []
    
    # Directives rigides pour un alignement matriciel parfait, même sur les lignes coupées
    p1 = "Tu es un scanner de tableau hautement précis et géométrique. " \
         "Analyse la structure visuelle du document ligne par ligne de haut en bas. " \
         "Tu dois générer un tableau Markdown horizontal strict avec EXACTEMENT " \
         "la structure suivante : | Date | Article | Prix | Quantite |\n"
         
    p2 = "CONSIGNES D'ALIGNEMENT ABSOLU :\n" \
         "1. Compte et numérise CHAQUE ligne du tableau physique de l'image. " \
         "Si une ligne en bas du document est coupée, tronquée ou s'il lui manque " \
         "ses bordures, TU DOIS TOUT DE MÊME LA CRÉER et extraire le texte visible.\n" \
         "2. INTERDICTION STRICTE de fusionner, de combiner ou de mélanger les données " \
         "de deux lignes différentes. Une ligne manuscrite/imprimée = Une ligne Markdown.\n" \
         "3. Si une information ou une colonne est illisible ou manquante sur une ligne " \
         "(notamment la ligne coupée du bas), laisse la case vide entre les séparateurs '|'. " \
         "Ne décale jamais les données d'une colonne vers une autre.\n" \
         "Ne fais aucun commentaire, commence directement par le tableau Markdown."
         
    prompt = p1 + p2

    for img_file in images:
        try:
            base64_image = encode_image_to_base64(img_file)
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }}
                    ]
                }],
                temperature=0.0
            )
            
            raw_text = response.choices[0].message.content.strip()
            
            if "ERREUR_AUCUN_TABLEAU" in raw_text:
                st.error(f"❌ Document invalide : `{img_file.name}`")
                continue
            
            lines = raw_text.split("\n")
            for line in lines:
                line = line.strip()
                if not line or "Date" in line or "---" in line:
                    continue
                
                if line.startswith("|") and line.endswith("|"):
                    parts = [p.strip() for p in line.split("|")]
                    actual_data = parts[1:-1]
                    
                    row = {"Date": "", "Article": "", "Prix": "", "Quantite": ""}
                    if len(actual_data) >= 1: row["Date"] = actual_data[0]
                    if len(actual_data) >= 2: row["Article"] = actual_data[1]
                    if len(actual_data) >= 3: row["Prix"] = actual_data[2]
                    if len(actual_data) >= 4: row["Quantite"] = actual_data[3]
                    all_data.append(row)
                    
        except Exception as e:
            st.error(f"Erreur traitement de {img_file.name} : {e}")
            
    df = pd.DataFrame(all_data)
    if not df.empty:
        df = df[["Date", "Article", "Prix", "Quantite"]].fillna("")
    return df

# --- 4. INTERFACE GRAPHIQUE ---
st.markdown("<h1 class='main-header'>Analyse & Digitalisation Ventes</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>OCR de vos cahiers de commerce.</p>", unsafe_allow_html=True)

files = st.file_uploader(
    "Images", 
    type=["jpg", "png", "jpeg"], 
    accept_multiple_files=True, 
    label_visibility="collapsed"
)

if files:
    hashes = {}
    has_duplicate = False
    duplicate_names = []
    
    for f in files:
        f_hash = calculate_image_hash(f)
        if f_hash in hashes:
            has_duplicate = True
            duplicate_names.append((hashes[f_hash], f.name))
        else:
            hashes[f_hash] = f.name
            
    allow_proceed = True
    if has_duplicate:
        st.warning("⚠️ **Alerte Doublon Détectée**")
        allow_proceed = False

    st.write("### Aperçu des documents")
    cols = st.columns(min(len(files), 6))
    for idx, f in enumerate(files):
        with cols[idx % 6]:
            st.image(f, use_container_width=True)
            short_name = f.name[:12] + "..." if len(f.name) > 12 else f.name
            st.caption(short_name)
            
    st.write("")

    if "data_extracted" not in st.session_state and allow_proceed:
        if st.button("Visualiser les données"):
            with st.spinner("Lecture brute en cours..."):
                df_raw = extract_data(files)
                if not df_raw.empty:
                    st.session_state.data_extracted = df_raw
                    st.rerun()

    if "data_extracted" in st.session_state:
        st.write("---")
        st.subheader("📝 Données capturées (Ordre strict)")
        
        df_edited = st.data_editor(
            st.session_state.data_extracted, 
            num_rows="dynamic", 
            use_container_width=True
        )
        
        if st.button("📊 Générer le Rapport BI"):
            df_final = df_edited.copy()
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            
            df_report = df_final[df_final["Article"].str.strip() != ""]
            ca_total = df_report["Total"].sum()
            
            m1, m2 = st.columns(2)
            with m1:
                val_ca = f"{ca_total:,.0f} FCFA"
                st.metric("Chiffre d'Affaires Global", val_ca)
            with m2:
                st.metric("Lignes commercialisées", len(df_report))

            if "Date" in df_report.columns and not df_report["Date"].empty:
                df_report["Date_DT"] = pd.to_datetime(df_report["Date"], errors='coerce')
                df_time = df_report.dropna(subset=["Date_DT"]).groupby("Date_DT")["Total"].sum().reset_index()
                if not df_time.empty:
                    fig = px.line(df_time, x="Date_DT", y="Total", template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)

            msg = f"*📊 BILAN DE VENTES*\nTotal : {ca_total:,.0f} FCFA"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
            
            btn_html = f'<a href="{wa_url}" target="_blank">' \
                       f'<button style="background-color:#10B981; color:white; ' \
                       f'border:none; border-radius:8px; padding:12px; ' \
                       f'width:100%; font-weight:600; cursor:pointer;">' \
                       f'📲 Transmettre sur WhatsApp</button></a>'
            st.markdown(btn_html, unsafe_allow_html=True)

            if st.button("🔄 Réinitialiser"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("Sélectionnez vos images pour démarrer.")
