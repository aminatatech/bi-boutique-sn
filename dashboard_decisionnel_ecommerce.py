import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import time
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION DE L'IA (SÉCURISÉE) ---
# On récupère la clé depuis les Secrets de Streamlit Cloud pour ne pas l'exposer sur GitHub
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ Clé API manquante. Veuillez la configurer dans les Secrets de Streamlit.")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Scanner BI Pro | Aminata Tech", 
    page_icon="💰", 
    layout="wide"
)

# Style personnalisé
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #0047AB; font-weight: bold; }
    .stButton>button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3em; 
        background-color: #0047AB; 
        color: white;
        font-weight: bold;
    }
    .main-header { font-size: 2.5rem; color: #1E3A8A; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS LOGIQUES ---

def extract_from_cahier(images):
    """Transforme les photos en données JSON via Gemini."""
    prompt = """
    Tu es un expert comptable spécialisé dans le commerce de détail. 
    Analyse ces photos de cahier de vente manuscrit.
    Extrais les données sous forme de liste JSON uniquement.
    Chaque objet doit avoir les clés exactes : "Article", "Prix", "Quantite".
    Ignore les totaux en bas de page et les ratures. 
    Sois précis sur les noms d'articles même s'ils sont abrégés.
    Exemple de sortie : [{"Article": "Pneu 15 pouces", "Prix": 35000, "Quantite": 1}]
    """
    all_data = []
    for img_file in images:
        img = Image.open(img_file)
        try:
            response = model.generate_content([prompt, img])
            # Nettoyage de la réponse IA pour isoler le JSON
            json_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_text)
            all_data.extend(data)
        except Exception as e:
            st.error(f"Erreur de lecture sur une image : {e}")
            continue
    return pd.DataFrame(all_data)

def generate_wa_link(ca, top_art, count):
    """Génère le lien de partage WhatsApp."""
    message = f"*📊 RAPPORT DE VENTES DU JOUR*\n\n" \
              f"💰 *CA Total :* {ca:,.0f} FCFA\n" \
              f"🏆 *Top Produit :* {top_art}\n" \
              f"📦 *Nombre de ventes :* {count}\n\n" \
              f"_Généré par l'outil BI de @aminatatech_"
    return f"https://wa.me/?text={urllib.parse.quote(message)}"

# --- 4. INTERFACE UTILISATEUR ---

st.markdown("<h1 class='main-header'>📈 Digitalisation & Business Intelligence</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>Transformez vos notes manuscrites en outils de décision stratégique.</p>", unsafe_allow_html=True)
st.write("---")

# Zone d'importation
files = st.file_uploader("Flashez ou importez les photos de vos ventes (Cahier)", 
                        type=["jpg", "png", "jpeg"], 
                        accept_multiple_files=True)

if files:
    # ÉTAPE 1 : EXTRACTION IA
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer l'analyse intelligente"):
            with st.spinner("L'IA @aminatatech déchiffre votre cahier..."):
                df_raw = extract_from_cahier(files)
                if not df_raw.empty:
                    st.session_state.data_extracted = df_raw
                    st.rerun()
                else:
                    st.error("Aucune donnée n'a pu être extraite. Assurez-vous que l'image est bien éclairée.")

    # ÉTAPE 2 : VALIDATION ET ÉDITION
    if "data_extracted" in st.session_state:
        st.subheader("📝 1. Vérifiez et validez les données")
        st.info("Vous pouvez modifier le tableau ci-dessous si l'IA a fait une erreur sur un prix ou un nom.")
        
        # Éditeur de données
        df_valid = st.data_editor(st.session_state.data_extracted, 
                                 num_rows="dynamic", 
                                 use_container_width=True)
        
        if st.button("📊 Générer le Tableau de Bord Final"):
            st.write("---")
            
            # Nettoyage numérique
            df_valid["Prix"] = pd.to_numeric(df_valid["Prix"], errors='coerce').fillna(0)
            df_valid["Quantite"] = pd.to_numeric(df_valid["Quantite"], errors='coerce').fillna(0)
            df_valid["Total"] = df_valid["Prix"] * df_valid["Quantite"]
            
            # Calculs des KPIs
            ca_total = df_valid["Total"].sum()
            nb_ventes = len(df_valid)
            top_prod = df_valid.groupby("Article")["Total"].sum().idxmax() if nb_ventes > 0 else "N/A"

            # Affichage des KPIs
            col1, col2, col3 = st.columns(3)
            col1.metric("Chiffre d'Affaires", f"{ca_total:,.0f} FCFA")
            col2.metric("Articles vendus", nb_ventes)
            col3.metric("Meilleure Vente", top_prod)

            # Visualisation
            st.write("---")
            st.subheader("🔍 Analyse visuelle")
            c_left, c_right = st.columns([2, 1])
            
            with c_left:
                fig_bar = px.bar(df_valid, x="Article", y="Total", 
                                title="Répartition du CA par article",
                                color="Total", color_continuous_scale="Viridis")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with c_right:
                st.subheader("💡 Conseil Expert")
                if ca_total > 0:
                    part_top = (df_valid.groupby("Article")["Total"].sum().max() / ca_total) * 100
                    st.write(f"L'article **{top_prod}** génère **{part_top:.1f}%** de vos revenus.")
                    if part_top > 50:
                        st.warning("⚠️ Attention : Votre CA dépend énormément d'un seul article.")
                    else:
                        st.success("✅ Votre inventaire semble bien diversifié.")

            # Options de partage
            st.write("---")
            wa_url = generate_wa_link(ca_total, top_prod, nb_ventes)
            st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#25D366; color:white; border:none; padding:12px; border-radius:8px; cursor:pointer; width:100%;">📲 Envoyer ce bilan au patron sur WhatsApp</button></a>', unsafe_allow_html=True)
            
            if st.button("🔄 Scanner une nouvelle page"):
                del st.session_state.data_extracted
                st.rerun()

else:
    # Message d'attente
    st.info("👋 Prête pour la démo ? Importez une photo de cahier de vente pour voir la magie.")
    st.image("https://img.icons8.com/illustrations/official/xl/financial-growth.png", width=300)
