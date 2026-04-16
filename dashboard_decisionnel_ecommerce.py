import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import time
import plotly.express as px
from fpdf import FPDF
import urllib.parse

# --- 1. CONFIGURATION DE L'IA (GEMINI 1.5 FLASH) ---
# Conseil : Remplace par ta clé API récupérée sur https://aistudio.google.com/
API_KEY = "VOTRE_CLE_API_ICI" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Scanner BI Pro - Freelance Solution", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 2rem; color: #0047AB; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #0047AB; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS LOGIQUES ---

def extract_from_cahier(images):
    """Utilise l'IA pour transformer des photos de cahier en données structurées JSON."""
    prompt = """
    Tu es un expert comptable. Analyse ces photos de cahier de vente.
    Extrais les données sous forme de liste JSON UNIQUEMENT. 
    Chaque objet doit avoir les clés exactes : "Article", "Prix", "Quantite".
    Ignore les totaux manuscrits et les lignes raturées.
    Exemple : [{"Article": "Pneu", "Prix": 25000, "Quantite": 2}]
    """
    all_data = []
    for img_file in images:
        img = Image.open(img_file)
        try:
            response = model.generate_content([prompt, img])
            # Nettoyage du texte pour ne garder que le JSON
            json_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_text)
            all_data.extend(data)
        except Exception as e:
            st.error(f"Erreur de lecture sur une page : {e}")
            continue
    return pd.DataFrame(all_data)

def generate_wa_link(ca, top_art, count):
    """Crée un lien WhatsApp pour envoyer le rapport au patron."""
    message = f"*RAPPORT DE VENTES DU JOUR*\n\n" \
              f"💰 *CA Total :* {ca:,.0f} FCFA\n" \
              f"🏆 *Top Produit :* {top_art}\n" \
              f"📦 *Nombre de ventes :* {count}\n\n" \
              f"_Généré par votre Assistant BI Expert_"
    return f"https://wa.me/?text={urllib.parse.quote(message)}"

# --- 4. INTERFACE UTILISATEUR ---

st.title("📈 Digitalisation & BI : Scanner de Cahier")
st.write("Transformez vos photos de cahier en rapports professionnels instantanément.")
st.write("---")

# Zone d'importation
files = st.file_uploader("Flashez ou importez les photos de votre cahier", 
                        type=["jpg", "png", "jpeg"], 
                        accept_multiple_files=True)

if files:
    # ÉTAPE 1 : EXTRACTION IA
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Extraire les données des photos"):
            with st.spinner("L'intelligence artificielle déchiffre votre cahier..."):
                time.sleep(1) # Effet visuel
                df_raw = extract_from_cahier(files)
                if not df_raw.empty:
                    st.session_state.data_extracted = df_raw
                    st.rerun()
                else:
                    st.error("L'IA n'a pas pu lire de données. Vérifiez la netteté des photos.")

    # ÉTAPE 2 : VALIDATION ET ÉDITION
    if "data_extracted" in st.session_state:
        st.subheader("📝 Étape de Validation")
        st.info("Corrigez les éventuelles erreurs de lecture de l'IA directement dans le tableau ci-dessous.")
        
        # Éditeur de données interactif
        df_valid = st.data_editor(st.session_state.data_extracted, 
                                 num_rows="dynamic", 
                                 use_container_width=True)
        
        if st.button("📊 Valider et Générer l'Analyse"):
            st.write("---")
            
            # Conversion numérique de sécurité
            df_valid["Prix"] = pd.to_numeric(df_valid["Prix"], errors='coerce').fillna(0)
            df_valid["Quantite"] = pd.to_numeric(df_valid["Quantite"], errors='coerce').fillna(0)
            df_valid["Total"] = df_valid["Prix"] * df_valid["Quantite"]
            
            # CALCULS KPIs
            ca_total = df_valid["Total"].sum()
            nb_lignes = len(df_valid)
            top_prod = df_valid.groupby("Article")["Total"].sum().idxmax() if nb_lignes > 0 else "N/A"

            # AFFICHAGE KPIs
            col1, col2, col3 = st.columns(3)
            col1.metric("Chiffre d'Affaires", f"{ca_total:,.0f} FCFA")
            col2.metric("Lignes de Ventes", nb_lignes)
            col3.metric("Top Article", top_prod)

            # VISUALISATION
            st.write("---")
            c_left, c_right = st.columns([2, 1])
            
            with c_left:
                fig_bar = px.bar(df_valid, x="Article", y="Total", 
                                 title="Volume de vente par Article",
                                 color="Total", color_continuous_scale="Blues")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with c_right:
                # Analyse narrative simplifiée
                st.subheader("🧠 Analyse Expert")
                if ca_total > 0:
                    part_top = (df_valid.groupby("Article")["Total"].sum().max() / ca_total) * 100
                    st.write(f"Votre article **{top_prod}** représente **{part_top:.1f}%** de vos revenus actuels.")
                    if part_top > 50:
                        st.warning("⚠️ Attention : Forte dépendance à un seul produit.")
                    else:
                        st.success("✅ Votre mix produit est bien équilibré.")

            # OPTIONS DE PARTAGE
            st.write("---")
            wa_url = generate_wa_link(ca_total, top_prod, nb_lignes)
            st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; width:100%;">📲 Partager le bilan sur WhatsApp au Patron</button></a>', unsafe_allow_html=True)
            
            if st.button("🔄 Scanner un nouveau cahier"):
                del st.session_state.data_extracted
                st.rerun()

else:
    # Message d'accueil pro pour les clients
    st.info("👋 Bienvenue ! Veuillez importer les photos de votre cahier de ventes pour commencer la digitalisation.")
    st.image("https://img.icons8.com/illustrations/official/xl/business-analysis.png", width=300)
