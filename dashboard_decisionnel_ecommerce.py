import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    
    # FORÇAGE DE LA VERSION API : C'est ici que ça se joue
    # On configure l'API pour pointer vers la version stable
    genai.configure(api_key=API_KEY, transport="rest") 
    
    # On définit le modèle avec son nom de système complet
    model = genai.GenerativeModel('gemini-1.5-flash')
    
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# --- 2. INTERFACE ---
st.title("📈 Scanner BI Pro | Aminata Tech")

files = st.file_uploader("Photos du cahier", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if st.button("🚀 Lancer l'Analyse"):
        all_data = []
        with st.spinner("Lecture en cours..."):
            for img_file in files:
                img = Image.open(img_file)
                prompt = "Extrait les données (Date, Article, Prix, Quantite) en JSON. Retourne uniquement le JSON."
                
                try:
                    # Appel avec gestion d'erreur spécifique au modèle
                    response = model.generate_content([prompt, img])
                    
                    # Extraction du texte
                    text = response.text.strip()
                    
                    # Nettoyage JSON
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    
                    data = json.loads(text)
                    all_data.extend(data if isinstance(data, list) else [data])
                    
                except Exception as e:
                    # Si ça échoue encore, on affiche le type d'erreur pour diagnostiquer
                    st.error(f"Détail technique : {e}")
            
            if all_data:
                st.success("Données extraites !")
                st.write(pd.DataFrame(all_data))
