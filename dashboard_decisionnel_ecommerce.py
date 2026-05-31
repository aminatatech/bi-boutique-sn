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
st.set_page_config(page_title="Business Intelligence Dashboard", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .main-header { font-size: 2.5rem; color: #0F172A; text-align: left; font-weight: 800; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #64748B; margin-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #2563EB; font-weight: 700; }
    div[data-testid="metric-container"] { background-color: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.2em; background-color: #2563EB; color: white; font-weight: 600; border: none; }
    .stButton>button:hover { background-color: #1D4ED8; color: white; }
    </style>
    """, unsafe_allow_html=True)

def calculate_image_hash(img_file):
    return hashlib.md5(img_file.getvalue()).hexdigest()

def encode_image_to_base64(img_file):
    image = Image.open(img_file)
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 3. FONCTION SCANNEUSE ULTRA-ROBUSTE (CORRIGÉE SANS PANDAS.READ_CSV) ---
def extract_data(images):
    all_data = []
    
    prompt = "Tu es un scanner de documents de commerce hautement fidèle. Tu devez numériser ce cahier de vente sous forme de tableau horizontal strict. " \
             "Si l'image ne contient aucun texte, aucune liste de vente ou aucun chiffre, réponds UNIQUEMENT par le mot : ERREUR_AUCUN_TABLEAU. " \
             "Sinon, génère un tableau Markdown contenant EXACTEMENT ces 4 colonnes dans cet ordre précis : | Date | Article | Prix | Quantite |\n" \
             "CONSIGNES DE NUMÉRISATION RIGIDES :\n" \
             "1. Analyse l'image ligne par ligne de haut en bas, sans sauter de ligne et sans regrouper de lignes entre elles.\n" \
             "2. Recopie fidèlement ce que tu lis sans rien corriger ou adapter.\n" \
             "3. Si une colonne ou une information est manquante ou vide sur une ligne de l'image originale, laisse la case vide entre les séparateurs verticaux. Ne décale pas les données des colonnes voisines.\n" \
             "Ne donne aucune explication, génère uniquement le tableau Markdown commençant par '| Date | Article | Prix | Quantite |'."

    for img_file in images:
        try:
            base64_image = encode_image_to_base64(img_file)
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                temperature=0.0
            )
            
            raw_text = response.choices[0].message.content.strip()
            
            if "ERREUR_AUCUN_TABLEAU" in raw_text:
                st.error(f"❌ Document invalide : `{img_file.name}` ne contient aucune donnée de vente exploitable.")
                continue
            
            # Découpage ligne par ligne ultra-tolérant aux erreurs de colonnes
            lines = raw_text.split("\n")
            for line in lines:
                line = line.strip()
                # On ignore les entêtes du tableau Markdown et les lignes vides
                if not line or "Date" in line or "---" in line or ":::" in line:
                    continue
                
                if line.startswith("|") and line.endswith("|"):
                    # On découpe par la barre verticale et on nettoie les espaces
                    parts = [p.strip() for p in line.split("|")]
                    # Comme la ligne commence et finit par "|", parts[0] et parts[-1] sont vides.
                    # Les vraies données se trouvent au milieu.
                    actual_data = parts[1:-1]
                    
                    structured_line = {"Date": "", "Article": "", "Prix": "", "Quantite": ""}
                    
                    # On remplit selon la position trouvée, aucun plantage possible si trop de colonnes
                    if len(actual_data) >= 1: structured_line["Date"] = actual_data[0]
                    if len(actual_data) >= 2: structured_line["Article"] = actual_data[1]
                    if len(actual_data) >= 3: structured_line["Prix"] = actual_data[2]
                    if len(actual_data) >= 4: structured_line["Quantite"] = actual_data[3]
                    
                    all_data.append(structured_line)
                    
        except Exception as e:
            st.error(f"Erreur lors du traitement de {img_file.name} : {e}")
            
    # Création propre du tableau de validation final
    df = pd.DataFrame(all_data)
    if not df.empty:
        df = df[["Date", "Article", "Prix", "Quantite"]].fillna("")
    return df

# --- 4. INTERFACE GRAPHIQUE ---
st.markdown("<h1 class='main-header'>Analyse & Digitalisation de Ventes</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Suivi en temps réel et OCR de vos cahiers de commerce.</p>", unsafe_allow_html=True)

files = st.file_uploader("Déposez les photos de votre cahier de vente", type=["jpg", "png", "jpeg"], accept_multiple_files=True, label_visibility="collapsed")

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
        for orig, dup in duplicate_names:
            st.write(f"L'image `{dup}` semble être identique à l'image `{orig}`.")
        
        confirm = st.radio("S'agit-il d'un choix volontaire ou d'une erreur d'importation ?", 
                           ["C'est fait exprès (importer tout de même)", "C'est une erreur (je vais corriger mes fichiers)"])
        if "erreur" in confirm.lower():
            allow_proceed = False
            st.info("Veuillez retirer l'image en double ou recharger la page pour corriger.")

    st.write("### Aperçu des documents importés")
    cols = st.columns(min(len(files), 6))
    for idx, f in enumerate(files):
        with cols[idx % 6]:
            st.image(f, use_container_width=True)
            st.caption(f.name[:15] + "..." if len(f.name) >
