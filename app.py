# app.py – Dashboard Streamlit : Analyse Énergétique France

import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.request

# Lien direct vers le fichier CSV hébergé sur Google Drive
url = "https://drive.google.com/uc?export=download&id=1CFSC1Xq7MR1EDw1TRhuy4gF0psL5t2-a"
output_file = "eco2mix_clean_final_2.csv"

# Télécharger le fichier
urllib.request.urlretrieve(url, output_file)

# Charger les données
df = pd.read_csv(output_file, sep=";")

# Vérification des colonnes pour éviter les erreurs liées à la colonne de date
st.write("Colonnes disponibles dans le fichier :")
st.write(df.columns)

# Vérification si la colonne "Date - Heure" existe
if "Date - Heure" not in df.columns:
    st.error("La colonne 'Date - Heure' est introuvable dans le fichier.")
    st.stop()  # Arrêter l'exécution si la colonne est absente

# Corriger les espaces ou caractères invisibles dans les noms de colonnes
df.columns = df.columns.str.strip()

# Convertir la colonne "Date - Heure" en datetime
df["Date - Heure"] = pd.to_datetime(df["Date - Heure"], errors="coerce")

# Création des colonnes Année et Mois
df["Année"] = df["Date - Heure"].dt.year
df["Mois"] = df["Date - Heure"].dt.month

# Afficher un aperçu des données pour vérifier que tout est bon
st.write(df.head())

# Définir la page
st.set_page_config(page_title="Énergie France – Dashboard", layout="wide")

# --- SIDEBAR
st.sidebar.title(" Navigation")
pages = ["Accueil", "Exploration", "Visualisations", "Risque national", "Focus Hiver", "Focus ENR", "Synthèse", "Conclusion", "Scénario 2030"]
page = st.sidebar.radio("Aller à :", pages)
regions = sorted(df["Région"].dropna().unique())
region = st.sidebar.selectbox("Sélectionnez une région :", regions)
annee = st.sidebar.slider("Filtrer par année", min_value=int(df["Année"].min()), max_value=int(df["Année"].max()), value=(2018, 2023))

df_filtered = df[(df["Région"] == region) & (df["Année"].between(*annee))]

# --- PAGE : ACCUEIL
if page == "Accueil":
    st.title(" Projet Analyse Énergétique – eco2mix (2013–2023)")
    st.markdown("""
    Bienvenue sur ce tableau de bord interactif visant à analyser :
    
    - le **phasage entre la consommation et la production**
    - les **déséquilibres régionaux** 
    - les **risques de blackout national** 
    - le rôle des **énergies renouvelables** 
    
    Données issues de [RTE eco2mix](https://odre.opendatasoft.com), nettoyées et enrichies.
    """)

# --- PAGE : EXPLORATION
elif page == "Exploration":
    st.header(" Exploration des données")
    st.write(f" Région : {region} |  Années : {annee[0]} – {annee[1]}")
    st.dataframe(df_filtered)
    st.download_button("⬇ Télécharger les données filtrées", df_filtered.to_csv(index=False).encode(), file_name="donnees_region.csv")

# --- PAGE : VISUALISATIONS
elif page == "Visualisations":
    st.header(" Visualisations interactives")
    
    st.subheader("Consommation vs Production Totale (par mois)")
    df_month = df_filtered.copy()
    df_month["Mois"] = df_month["Date - Heure"].dt.to_period("M").astype(str)
    monthly = df_month.groupby("Mois")[["Consommation (MW)", "Production_totale"]].mean().reset_index()
    st.plotly_chart(px.bar(monthly, x="Mois", y=["Consommation (MW)", "Production_totale"], barmode="group", title="Évolution mensuelle"))

    st.subheader("Évolution de la consommation pour pompage (stockage)")
    df_pompage = df_filtered.groupby("Année")["Pompage (MW)"].mean().reset_index()
    fig_pompage = px.line(df_pompage, x="Année", y="Pompage (MW)", title="Utilisation annuelle du pompage")
    st.plotly_chart(fig_pompage)

    st.subheader("Déséquilibre Production - Consommation (Boxplot)")
    df_filtered["delta"] = df_filtered["Production_totale"] - df_filtered["Consommation (MW)"]
    st.plotly_chart(px.box(df_filtered, x="Mois", y="delta", points="all", title="Distribution mensuelle du déséquilibre"))

    st.subheader("Structure de la production par filière (stacked bar)")
    prod_filtres = df_filtered.groupby("Année")[["Nucléaire (MW)", "Thermique (MW)", "Hydraulique (MW)",
                                                  "Solaire (MW)", "Eolien (MW)", "Bioénergies (MW)"]].mean().reset_index()
    fig_stack = px.bar(prod_filtres, x="Année",
                       y=["Nucléaire (MW)", "Thermique (MW)", "Hydraulique (MW)", "Solaire (MW)", "Eolien (MW)", "Bioénergies (MW)"],
                       title="Structure moyenne de la production par filière",
                       labels={"value": "MW"}, barmode="stack")
    st.plotly_chart(fig_stack)

# --- PAGE : RISQUE NATIONAL
elif page == "Risque national":
    st.header(" Analyse des risques de blackout (niveau national)")

    st.markdown("""
    ###  Risque de Blackout : qu'est-ce que c'est ?
    Un blackout survient lorsqu’il y a un **déséquilibre national brutal** entre l’offre et la demande d’électricité.
    Cela peut être causé par :
    - une **sous-production** (pénurie d’électricité),
    - une **surconsommation** (notamment en hiver),
    - une **incapacité du réseau à compenser régionalement**.

    > Nous analysons ici l’évolution du **déséquilibre global (production – consommation)** sur 10 ans pour détecter les périodes critiques.
    """)

    # Agrégation nationale
    df_nat = df.groupby("Date - Heure")[["Consommation (MW)", "Production_totale"]].sum().reset_index()
    df_nat["delta"] = df_nat["Production_totale"] - df_nat["Consommation (MW)"]

    # Graphique principal : déséquilibre au fil du temps
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_nat["Date - Heure"], y=df_nat["delta"],
                             mode="lines", name="Delta (Prod - Conso)", line=dict(color="firebrick")))
    fig.update_layout(title="Déséquilibre national au fil du temps",
                      xaxis_title="Date", yaxis_title="Delta (MW)", height=500)
    st.plotly_chart(fig)

    # Focus sur les mois d'hiver
    st.subheader("❄️ Zoom sur les périodes hivernales (Déc–Fév)")
    df_hiver = df_nat[df_nat["Date - Heure"].dt.month.isin([12, 1, 2])]
    fig_hiver = px.line(df_hiver, x="Date - Heure", y="delta", title="Zoom sur les Hivers (Déc–Fév)", labels={"delta": "Delta (MW)"})
    st.plotly_chart(fig_hiver)

    # Histogramme des déséquilibres critiques
    st.subheader(" Distribution des déséquilibres critiques")
    neg_count = (df_nat["delta"] < 0).sum()
    st.metric(" Nombre de situations critiques", f"{neg_count} cas")
    fig_hist = px.histogram(df_nat[df_nat["delta"] < 0], x="delta", nbins=50, title="Distribution des déséquilibres négatifs (blackouts potentiels)", labels={"delta": "Delta (MW)"})
    st.plotly_chart(fig_hist)

    # Score de stress électrique
    st.subheader(" Score global de stress énergétique")
    score = df_nat["delta"].apply(lambda x: -x if x < 0 else 0).sum()
    st.metric(" MW cumulés en déséquilibre", f"{int(score):,} MW")

    st.info("Ce score totalise tous les MW en déficit sur 10 ans. Plus il est élevé, plus le risque national est important.")

# --- PAGE : FOCUS HIVER
elif page == "Focus Hiver":
    st.header("❄️ Analyse critique des hivers énergétiques")

    st.markdown("""
    En hiver, la consommation électrique atteint des niveaux records à cause du chauffage.
    Ce pic saisonnier met en tension le réseau, notamment en cas de **production insuffisante** ou de **fort déséquilibre régional**.
    """)

    # Filtrage hiver (Déc-Janv-Fév)
    df_hiver = df[df["Date - Heure"].dt.month.isin([12, 1, 2])]

    st.subheader(" Évolution nationale de l'équilibre en hiver")
    df_hiver_nat = df_hiver.groupby("Date - Heure")[["Consommation (MW)", "Production_totale"]].sum().reset_index()
    df_hiver_nat["delta"] = df_hiver_nat["Production_totale"] - df_hiver_nat["Consommation (MW)"]

    fig = px.line(df_hiver_nat, x="Date - Heure", y="delta", title="Déséquilibre National en Hiver", labels={"delta": "Delta (MW)"})
    st.plotly_chart(fig)

    st.subheader(" Régions les plus critiques (hiver uniquement)")
    df_risk = df_hiver.groupby("Région")["delta_prod_cons"].mean().sort_values()
    st.plotly_chart(px.bar(df_risk, title="Delta moyen par région en hiver", labels={"value": "Delta (MW)"}))


# --- PAGE : ENERGIES RENOUVELABLES
elif page == "Focus ENR":
    st.header(" Focus Énergies Renouvelables")
    df_enr = df.copy()
    df_enr["Prod_ENR"] = df_enr[["Solaire (MW)", "Eolien (MW)", "Hydraulique (MW)", "Bioénergies (MW)"]].sum(axis=1)
    enr_reg = df_enr.groupby("Région")["Prod_ENR"].mean().sort_values()
    st.plotly_chart(px.bar(enr_reg, x=enr_reg.values, y=enr_reg.index, orientation="h", title="Production ENR Moyenne par Région"))

# --- PAGE : SYNTHESE
elif page == "Synthèse":
    st.header(f"🧾 Synthèse pour la région : {region}")
    auto = round(df_filtered["Autonomie"].mean()*100, 1)
    delta = round(df_filtered["delta_prod_cons"].mean(), 0)
    st.metric(" Taux d'autonomie ENR", f"{auto} %")
    st.metric(" Delta moyen Prod - Conso", f"{delta:,} MW")
    dependance = df_filtered["Ech. physiques (MW)"].sum() / df_filtered["Consommation (MW)"].sum()
    st.metric("Dépendance aux échanges", f"{round(dependance*100, 1)} %")


    st.markdown("---")
    st.subheader("Interprétation automatique")                                                          
    # Interprétation automatique

    if auto < 30:
        st.error(" Très faible autonomie : la région dépend fortement des imports.")
    elif auto < 70:
        st.warning(" Autonomie moyenne : attention aux pics de conso.")
    else:
        st.success(" Bonne autonomie énergétique.")

    # Bloc carte – toujours affiché
    st.subheader(" Carte des risques régionaux")
    df_carte = df.groupby("Région")["delta_prod_cons"].mean().reset_index()
    df_carte.columns = ["Région", "Delta_Moyen"]

    fig_map = px.choropleth(
        df_carte,
        locations="Région",
        locationmode="geo",
        geojson="https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson",
        featureidkey="properties.nom",
        color="Delta_Moyen",
        color_continuous_scale="RdBu_r",
        title="🗺️ Déséquilibre moyen par région (2013–2023)",
    )

    fig_map.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig_map)

# --- PAGE : CONCLUSION
elif page == "Conclusion":
    st.header(" Conclusion & Recommandations")
    st.markdown("""
    ###  Ce que nous avons observé :
    - De fortes variations saisonnières dans certaines régions
    - Un risque de déséquilibre national en hiver (blackout possible)
    - Un déséquilibre marqué dans les régions peu dotées en ENR

    ### Recommandations :
    - **Renforcer le stockage** dans les régions à pic de consommation
    - **Rééquilibrer l’implantation des ENR**
    - **Simuler des scénarios** avec import/export + stockage pour réduire les deltas

    Merci pour votre attention 
    """)

# --- PAGE : SCÉNARIO 2030
elif page == "Scénario 2030":
    st.header(" Scénario fictif : Hiver 2030, blackout national ?")

    st.markdown("""
    Ce scénario imagine un hiver tendu en 2030 avec :
    - Fermeture progressive des centrales fossiles 
    - Forte vague de froid 
    - Retard sur l'installation d'ENR 
    
    > Objectif : simuler l'impact de plusieurs **régions déficitaires simultanées**.

    **Hypothèse** : les 5 régions les plus déficitaires (delta négatif) tombent sous seuil critique pendant 15 jours.
    """)

    # Identifier les 5 régions les plus déficitaires historiquement
    top_risque = df.groupby("Région")["delta_prod_cons"].mean().nsmallest(5).index.tolist()
    st.write(f" Régions sélectionnées : {', '.join(top_risque)}")

    # Filtrer un hiver
    df_2030 = df[df["Date - Heure"].dt.month.isin([1, 2]) & df["Région"].isin(top_risque)].copy()
    df_2030["Simul_delta"] = df_2030["delta_prod_cons"] * 1.2  # on aggrave un peu la situation

    fig = px.line(df_2030, x="Date - Heure", y="Simul_delta", color="Région", title="Évolution simulée du déséquilibre (hiver tendu)")
    st.plotly_chart(fig)

    total_deficit = df_2030["Simul_delta"].apply(lambda x: -x if x < 0 else 0).sum()
    st.metric(" MW cumulés en déficit simulé", f"{int(total_deficit):,} MW")

    st.warning("""
     Résultat : surcharge estimée de plusieurs GW.
    Le réseau national, sans compensation, entre en **zone rouge**.
    """)

    st.markdown("""
    **Leçons du scénario** :
    - Le réseau peut absorber un certain nombre de déficits locaux, **mais pas en simultané**.
    - La résilience énergétique dépend de **l'interconnexion**, **du stockage**, et de **l'anticipation**.

     Ce scénario montre que sans planification d’ici 2030, un blackout massif est **mathématiquement plausible**.
    """)

# FIN
