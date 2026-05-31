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

# --- 3. FONCTION SCANNEUSE COMPORTANT UN ANCRAGE PAR NUMÉROTATION EN TABLEAU ---
def extract_data(images):
    all_data = []
    
    # On revient au Markdown pour la fidélité textuelle, mais avec un index géométrique obligatoire
    p1 = "Tu es un scanner OCR de documents de commerce d'une précision absolue. " \
         "Analyse l'image ligne par ligne de haut en bas et génère un tableau Markdown " \
         "horizontal strict contenant EXACTEMENT ces 5 colonnes : " \
         "| N° | Date | Article | Prix | Quantite |\n"
         
    p2 = "DIRECTIVES DE COPIE RIGIDES :\n" \
         "1. La colonne 'N°' doit contenir l'index de la ligne physique sur l'image (1, 2, 3...).\n" \
         "2. Recopie le contenu textuel de chaque cellule avec une fidélité totale, sans rien reformuler.\n" \
         "3. Tu dois générer une ligne Markdown pour CHAQUE ligne physique du cahier. Si la dernière ligne en bas " \
         "est coupée ou s'il lui manque ses bordures, attribue-lui son numéro (ex: | 8 |) et extrais le texte visible. " \
         "Laisse les cases vides si l'information est tronquée, mais ne fusionne JAMAIS deux lignes entre elles.\n" \
         "4. Si une cellule est vide au milieu du tableau, laisse l'espace vide entre les '|'. Ne décale pas les données.\n" \
         "Ne donne aucune explication, commence directement par l'en-tête du tableau Markdown."
         
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
                # On ignore les lignes de structure Markdown
                if not line or "Article" in line or "---" in line or ":::" in line:
                    continue
                
                if line.startswith("|") and line.endswith("|"):
                    parts = [p.strip() for p in line.split("|")]
                    # parts[0] et parts[-1] sont vides à cause des pipes aux extrémités.
                    # Le contenu réel est décalé de 1 à cause de la nouvelle colonne N°
                    actual_data = parts[1:-1]
                    
                    row = {"Date": "", "Article": "", "Prix": "", "Quantite": ""}
                    
                    # Remplissage par position relative à la colonne N° (actual_data[0] étant le N°)
                    if len(actual_data) >= 2: row["Date"] = actual_data[1]
                    if len(actual_data) >= 3: row["Article"] = actual_data[2]
                    if len(actual_data) >= 4: row["Prix"] = actual_data[3]
                    if len
