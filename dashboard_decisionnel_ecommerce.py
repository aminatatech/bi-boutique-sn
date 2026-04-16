import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json

# --- 1. CONFIGURATION ---
try:
    # On récupère la clé
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # On force le modèle SANS vérifier s'il existe (on tente l'appel direct)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# --- 2. INTERFACE ---
st.set_page_config(page_title="Scanner BI Pro | Aminata Tech")
st.title("📈 Test Final Scanner BI")

files = st.file_uploader("Photos du cahier", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if st.button("🚀 Tester l'Analyse"):
        all_data = []
        with st.spinner("L'IA tente une lecture directe..."):
            for img_file in files:
                img = Image.open(img_file)
                # Prompt ultra-simple pour tester la réponse
                prompt = "Liste les articles, prix et quantités de cette image en JSON."
                
                try:
                    # Tentative d'appel direct
                    response = model.generate_content([prompt, img])
                    text = response.text.strip()
                    
                    # Nettoyage minimal du JSON
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    
                    data = json.loads(text)
                    all_data.extend(data if isinstance(data, list) else [data])
                except Exception as e:
                    st.error(f"Détail de l'erreur : {e}")
            
            if all_data:
                st.success("Ça fonctionne !")
                st.write(pd.DataFrame(all_data))
            else:
                st.warning("Aucune donnée reçue.")

st.write("---")
st.caption("Si l'erreur 404 persiste, vérifiez que l'API 'Generative Language API' est bien activée dans votre console Google Cloud.")
