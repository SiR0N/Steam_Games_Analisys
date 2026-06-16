import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# ============================
# CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Steam Games Dashboard", layout="wide")
st.title("🎮 Steam Games Dashboard — Optimizado")

CSV_PATH = "games.csv"

# ============================
# 1. CARGA Y LIMPIEZA GLOBAL (SE HACE UNA SOLA VEZ)
# ============================
@st.cache_data
def load_and_clean_data():
    df = pd.read_csv(CSV_PATH)
    
    # Conversiones numéricas
    df["Release_date"] = pd.to_datetime(df["Release_date"], errors="coerce")
    df["Year"] = df["Release_date"].dt.year
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)
    df["Positive"] = pd.to_numeric(df["Positive"], errors="coerce").fillna(0)
    df["Negative"] = pd.to_numeric(df["Negative"], errors="coerce").fillna(0)
    df["Total_Reviews"] = df["Positive"] + df["Negative"]
    df["Aceptacion_Real"] = (df["Positive"] / df["Total_Reviews"] * 100).fillna(0)
    
    # Dentro de tu función load_and_clean_data()
    df["median_playtime_forever"] = pd.to_numeric(df["median_playtime_forever"], errors="coerce").fillna(0)
    df["median_playtime_2weeks"] = pd.to_numeric(df["median_playtime_2weeks"], errors="coerce").fillna(0)
    # Eliminar juegos que no tienen ni una reseña Y no tienen tiempo de juego
    df = df[(df["Total_Reviews"] > 0) | (df["median_playtime_forever"] > 0)]

    # Limpieza de Géneros (Global)
    def procesar_generos(x):
        if pd.isna(x): return []
        return [g.strip() for g in str(x).split(",") if g.strip()]
    
    df["Genres_list"] = df["Genres"].apply(procesar_generos)
    df["Genero_Principal"] = df["Genres_list"].apply(lambda x: x[0] if x else "Otros")
    
    # Limpieza de Tags
    df["Tag_List"] = df["Tags"].apply(lambda x: [t.strip() for t in str(x).split(",")] if pd.notna(x) else [])
    
    return df

df = load_and_clean_data()

# ============================
# 2. FILTROS DINÁMICOS
# ============================
st.sidebar.header("🎛️ Filtros")

all_genres = sorted({g for sub in df["Genres_list"] for g in sub})
genre_filter = st.sidebar.multiselect("Géneros", all_genres)
year_range = st.sidebar.slider("Año", int(df["Year"].min()), int(df["Year"].max()), (2010, 2026))
price_range = st.sidebar.slider("Precio (€)", 0.0, float(df["Price"].max()), (0.0, 100.0))

filtered_df = df.copy()
if genre_filter:
    filtered_df = filtered_df[filtered_df["Genres_list"].apply(lambda x: any(g in x for g in genre_filter))]
filtered_df = filtered_df[(filtered_df["Year"] >= year_range[0]) & (filtered_df["Year"] <= year_range[1])]
filtered_df = filtered_df[(filtered_df["Price"] >= price_range[0]) & (filtered_df["Price"] <= price_range[1])]

st.subheader(f"📊 Resultados: {len(filtered_df)} juegos")

# ============================
# 3. VISUALIZACIONES
# ============================

# Gráfica: Distribución Precios
fig1 = px.histogram(filtered_df, x="Price", nbins=50, title="Distribución de Precios", template="plotly_dark")
st.plotly_chart(fig1, use_container_width=True)

# Gráfica: Top Géneros
if not filtered_df.empty:
    st.subheader("🎭 Top géneros")
    genre_counts = pd.Series([g for sub in filtered_df["Genres_list"] for g in sub]).value_counts().head(10).reset_index()
    genre_counts.columns = ["Género", "Cantidad"]
    fig2 = px.bar(genre_counts, x="Cantidad", y="Género", orientation="h", color="Género", template="plotly_dark")
    fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# Gráfica: Top Juegos (Comunidad)
st.subheader("🔥 Top 20 Juegos según Comunidad")
if not filtered_df.empty:
    df_top = filtered_df[filtered_df["Total_Reviews"] > 50].sort_values("Aceptacion_Real", ascending=False).head(20)
    fig_top = px.bar(df_top, x="Aceptacion_Real", y="Name", color="Total_Reviews", orientation="h", 
                     title="Mejor aceptados (con más de 50 reseñas)", template="plotly_dark")
    fig_top.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_top, use_container_width=True)

# ============================
# 4. RECOMENDADOR HÍBRIDO (Simplificado)
# ============================
st.subheader("🤖 Recomendador Simple")
game_select = st.selectbox("Elige un juego base:", df["Name"].unique())

if game_select:
    target = df[df["Name"] == game_select].iloc[0]
    # Filtro sencillo basado en género principal
    recs = df[df["Genero_Principal"] == target["Genero_Principal"]].sort_values("Aceptacion_Real", ascending=False).head(10)
    st.write(f"Juegos similares en género '{target['Genero_Principal']}':")
    st.dataframe(recs[["Name", "Price", "Aceptacion_Real"]])