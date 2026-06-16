import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import matplotlib.pyplot as plt
from wordcloud import WordCloud

import os

# ============================
# CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Steam Games Dashboard", layout="wide")
st.title("🎮 Steam Games Dashboard")
st.write("Dashboard avanzado con filtros dinámicos, análisis y visualizaciones interactivas.")

PARQUET_PATH = "games.parquet"

# ============================
# CARGA DEL PARQUET
# ============================
@st.cache_data
def load_and_clean_data():
    df = pd.read_parquet(PARQUET_PATH)
    
    # 1. Definir lista negra aquí mismo para tenerla a mano
    LISTA_NEGRA = [
        "Web Publishing", "Animation & Modeling", "Education", "Software Training", 
        "Accounting", "Video Production", "Utilities", "Audio Production", 
        "Design & Illustration", "Photo Editing", "Game Development", "Software"
    ]
    
    df["Release_date"] = pd.to_datetime(df["Release_date"], errors="coerce")
    df["Year"] = df["Release_date"].dt.year
    df["Positive"] = pd.to_numeric(df["Positive"], errors="coerce").fillna(0)
    df["Negative"] = pd.to_numeric(df["Negative"], errors="coerce").fillna(0)
    df["Total_Reviews"] = df["Positive"] + df["Negative"]
    df["Aceptacion_Real"] = (df["Positive"] / df["Total_Reviews"] * 100).fillna(0)
    
    df["Median_playtime_forever"] = pd.to_numeric(df["Median_playtime_forever"], errors="coerce").fillna(0)
    df["Median_playtime_2weeks"] = pd.to_numeric(df["Median_playtime_2weeks"], errors="coerce").fillna(0)
    
    # 2. Limpieza de Géneros (Procesamos primero)
# 2. Función de limpieza que filtra la lista al vuelo
    def procesar_generos_limpios(x):
        if pd.isna(x): return []
        # Limpia espacios Y elimina los que están en la lista negra
        return [g.strip() for g in str(x).split(",") if g.strip() and g.strip() not in LISTA_NEGRA]
    
    df["Genres_list"] = df["Genres"].apply(procesar_generos_limpios)
    
    # 3. Ahora el Género Principal ya no puede ser software
    df["Genero_Principal"] = df["Genres_list"].apply(lambda x: x[0] if x else "Otros")
    
    # 4. Filtro de filas (opcional, pero recomendado)
    df = df[df["Genres_list"].apply(len) > 0]
    
    # 3. FILTRADO GLOBAL: Eliminamos software y basura de un solo golpe
    df = df[~df["Genero_Principal"].isin(LISTA_NEGRA)]
    df = df[(df["Total_Reviews"] > 0) | (df["Median_playtime_forever"] > 0)]
    
    # Limpiar Estimated_owners (convertir rango a valor numérico conservador)
    def extraer_min_owners(x):
        if pd.isna(x) or str(x) == '0 - 0': return 0
        try: return float(str(x).split('-')[0].strip())
        except: return 0

        # Asegurar que el precio es float limpio
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)
    # Crear una bandera para diferenciar F2P fácilmente en tus gráficas
    df["Is_Free"] = df["Price"] == 0


    # Limpieza básica para evitar duplicados en filtros
    df["Developers"] = df["Developers"].fillna("Unknown").str.strip()
    df["Publishers"] = df["Publishers"].fillna("Unknown").str.strip()

    # Si hay duplicados, nos quedamos con la última entrada (o la que tenga más reviews)
    df = df.sort_values("Total_Reviews", ascending=False).drop_duplicates(subset="Appid", keep="first")

    df["Estimated_owners_min"] = df["Estimated_owners"].apply(extraer_min_owners)
    
    # Cálculos de negocio (Hecho una vez aquí)
    df["Mercado_Estimado"] = df["Estimated_owners_min"] * df["Price"]
    
    df["Tag_List"] = df["Tags"].apply(lambda x: [t.strip() for t in str(x).split(",")] if pd.notna(x) else [])
    
    return df

df = load_and_clean_data()

# ============================
# FILTROS DINÁMICOS
# ============================
st.sidebar.header("🎛️ Filtros")

# Géneros
all_genres = sorted({g for sub in df["Genres_list"] for g in sub})
genre_filter = st.sidebar.multiselect("Géneros", all_genres)

# Años
min_year, max_year = int(df["Year"].min()), int(df["Year"].max())
year_range = st.sidebar.slider("Año de lanzamiento", min_year, max_year, (min_year, max_year))

# Precio
min_price, max_price = float(df["Price"].min()), float(df["Price"].max())
price_range = st.sidebar.slider("Rango de precio (€)", min_price, max_price, (min_price, max_price))

# Desarrollador
#devs = sorted(df["Developers"].dropna().unique().tolist())
#developer_filter = st.sidebar.selectbox("Desarrollador", ["Todos"] + devs)

# Buscador
#st.sidebar.subheader("🔍 Buscar juego")
#query = st.sidebar.text_input("Nombre del juego")

# ============================
# APLICAR FILTROS
# ============================
filtered_df = df.copy()

if genre_filter:
    filtered_df = filtered_df[filtered_df["Genres_list"].apply(lambda x: any(g in x for g in genre_filter))]

filtered_df = filtered_df[(filtered_df["Year"] >= year_range[0]) & (filtered_df["Year"] <= year_range[1])]
filtered_df = filtered_df[(filtered_df["Price"] >= price_range[0]) & (filtered_df["Price"] <= price_range[1])]

#if developer_filter != "Todos":
#    filtered_df = filtered_df[filtered_df["Developers"] == developer_filter]

#if query:
#    filtered_df = filtered_df[filtered_df["Name"].str.contains(query, case=False, na=False)]

st.subheader(f"📊 Resultados filtrados: {len(filtered_df)} juegos")
st.dataframe(filtered_df.head(50), use_container_width=True)


# ============================
# GRÁFICA 1 — Distribución de precios (Optimizada)
# ============================
st.subheader("💰 Distribución de precios")

# Creamos el histograma básico
fig1 = px.histogram(
    filtered_df, 
    x="Price", 
    nbins=100, 
    title="Distribución de precios (Vista enfocada)",
    template="plotly_dark",
    labels={"Price": "Precio (€)", "count": "Cantidad de Juegos"}
)

# --- EL TRUCO ---
# Forzamos el rango del eje X. Si el precio máximo actual es muy alto, 
# lo limitamos visualmente a 100€ para que no se comprima la gráfica.
max_actual = filtered_df["Price"].max()
if max_actual > 100:
    fig1.update_layout(xaxis_range=[0, 100])
else:
    fig1.update_layout(xaxis_range=[0, max_actual])

st.plotly_chart(fig1, use_container_width=True)

# ============================
# GRÁFICA 2 — Top géneros (Con colores dinámicos)
# ============================
st.subheader("🎭 Top géneros más frecuentes")

all_genres_flat = [g for sub in filtered_df["Genres_list"] for g in sub]

if all_genres_flat:
    # Convertimos a DataFrame para que Plotly Express asigne los colores de forma más limpia
    genre_counts = pd.Series(all_genres_flat).value_counts().head(10).reset_index()
    genre_counts.columns = ["Género", "Cantidad"]

    fig2 = px.bar(
        genre_counts,
        x="Cantidad",
        y="Género",
        color="Género", # <--- ESTO ASIGNA UN COLOR DIFERENTE A CADA BARRA
        orientation="h",
        title="Top 10 géneros más comunes",
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Pastel # Paleta de colores suave/pastel
    )

    # Truco visual: Ordenamos de mayor a menor para que la barra más larga quede arriba
    fig2.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False # Ocultamos la leyenda lateral porque el nombre ya sale en el eje Y
    )
    
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No hay géneros disponibles para los filtros seleccionados.")

# ============================
# GRÁFICA 10 — Evolución Top 5 Géneros por Año
# ============================
st.subheader("📈 Evolución de los 5 Géneros más populares")

# Usamos una copia de los datos filtrados para no afectar otras gráficas
df_evo = filtered_df.copy()

# 1. Aseguramos que la columna Year existe y filtramos rango razonable
df_evo = df_evo[(df_evo["Year"] >= 2014) & (df_evo["Year"] <= 2025)]

if not df_evo.empty:
    # 2. 'Explode' para separar los géneros en filas individuales
    df_exploded_evo = df_evo.explode("Genres_list")
    
    # 3. Agrupamos y contamos
    df_counts = df_exploded_evo.groupby(["Year", "Genres_list"]).size().reset_index(name="Cantidad")
    
    # 4. Obtenemos el Top 5 por cada año
    df_top5 = df_counts.sort_values(["Year", "Cantidad"], ascending=[True, False])
    df_top5 = df_top5.groupby("Year").head(5)

    fig_evo = px.bar(
        df_top5, 
        x="Year", 
        y="Cantidad", 
        color="Genres_list",
        barmode="group",
        title="Top 5 Tipos de Juegos por Año (2014 - 2025)",
        labels={"Year": "Año", "Cantidad": "Número de Juegos", "Genres_list": "Género"},
        template="plotly_dark"
    )
    
    fig_evo.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    st.plotly_chart(fig_evo, use_container_width=True)
else:
    st.info("Ajusta el filtro de años en la barra lateral para ver la evolución (2014-2025).")

# ============================
# GRÁFICA 11 — Distribución de Géneros (Pie Chart)
# ============================
st.subheader("🍕 Distribución Detallada por Año")

col1, col2 = st.columns([1, 2])

with col1:
    # Selectores locales para esta gráfica
    año_sel = st.selectbox("Selecciona el Año para el detalle:", 
                           options=sorted(filtered_df["Year"].dropna().unique().astype(int), reverse=True),
                           index=0)
    
    top_x = st.slider("Cantidad de géneros principales (Top X):", 3, 15, 8)

with col2:
    # Lógica de procesamiento
    df_year = filtered_df[filtered_df["Year"] == año_sel].explode("Genres_list")
    
    if not df_year.empty:
        conteo_gen = df_year["Genres_list"].value_counts().reset_index()
        conteo_gen.columns = ["Genero", "Cantidad"]
        
        # Separar Top X y "Otros"
        df_top = conteo_gen.head(top_x).copy()
        cantidad_otros = conteo_gen["Cantidad"].iloc[top_x:].sum() if len(conteo_gen) > top_x else 0
        
        if cantidad_otros > 0:
            fila_otros = pd.DataFrame([{"Genero": "Otros Géneros", "Cantidad": cantidad_otros}])
            df_final_pie = pd.concat([df_top, fila_otros], ignore_index=True)
        else:
            df_final_pie = df_top

        fig_pie = px.pie(
            df_final_pie,
            values="Cantidad",
            names="Genero",
            title=f"Géneros en {año_sel} (Top {top_x})",
            template="plotly_dark",
            hole=0.4
        )
        
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.write("No hay datos para el año seleccionado.")

# ============================
# GRÁFICA 3 — Precio vs Reseñas positivas (Optimizada)
# ============================
st.subheader("⭐ Precio vs Reseñas positivas")

if not filtered_df.empty:
    fig3 = px.scatter(
        filtered_df,
        x="Price",
        y="Positive",
        color="Year", # Añade color por año para darle más vida y analítica
        hover_data=["Name", "Developers"],
        opacity=0.6,
        title="Relación Precio vs Reseñas Positivas (Vista Enfocada)",
        template="plotly_dark",
        labels={
            "Price": "Precio (€)",
            "Positive": "Reseñas Positivas",
            "Year": "Año"
        },
        color_continuous_scale=px.colors.sequential.Viridis
    )

    # --- EL TRUCO PARA ELIMINAR LOS OUTLIERS VISUALMENTE ---
    max_price_actual = filtered_df["Price"].max()
    max_pos_actual = filtered_df["Positive"].max()

    # Si hay juegos que superan los 100€, recortamos el eje X para que no se comprima
    limite_x = 100 if max_price_actual > 100 else max_price_actual
    
    # Si hay super-hits (como CS:GO/Dota) que pasan de 200k reseñas, recortamos el eje Y 
    # para poder ver la distribución de los juegos normales
    limite_y = 200000 if max_pos_actual > 200000 else max_pos_actual

    fig3.update_layout(
        xaxis_range=[0, limite_x],
        yaxis_range=[0, limite_y]
    )

    # Mejorar el tamaño de los puntos para que se aprecien mejor
    fig3.update_traces(marker=dict(size=6))

    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No hay datos disponibles para los filtros seleccionados.")

# ============================
# GRÁFICA 4 — Lanzamientos por año
# ============================
st.subheader("📅 Lanzamientos por año")
year_counts = filtered_df["Year"].value_counts().sort_index()
fig4 = px.line(
    x=year_counts.index,
    y=year_counts.values,
    markers=True,
    title="Número de lanzamientos por año"
)
st.plotly_chart(fig4, use_container_width=True)

from plotly.subplots import make_subplots
import plotly.graph_objects as go

from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ==============================================================================
# GRÁFICA 5 — Versión Ultra-Fluida (Rendimiento optimizado con WebGL)
# ==============================================================================
st.subheader("⏳ Comparativa de Tiempos de Juego vs Precio")
st.write("Análisis sincronizado de alto rendimiento utilizando aceleración por hardware (WebGL).")

if not filtered_df.empty:
    # 1. Preparar y limpiar los datos de tiempo (Pasar de minutos a horas)
    df_tiempos = filtered_df.copy()
    df_tiempos["Horas_Mediana_Total"] = df_tiempos["Median_playtime_forever"] / 60
    df_tiempos["Horas_Promedio_Total"] = df_tiempos["Average_playtime_forever"] / 60
    df_tiempos["Horas_Mediana_2Semanas"] = df_tiempos["Median_playtime_2weeks"] / 60

    # 2. Identificar los 5 géneros más comunes actuales
    df_exploded_temp = df_tiempos.explode("Genres_list")
    top_5_generos = df_exploded_temp["Genres_list"].value_counts().head(5).index.tolist()

    # 3. Clasificación Top 5 + Otros
    def asignar_genero_principal(lista_generos):
        if not isinstance(lista_generos, list) or len(lista_generos) == 0:
            return "Otros"
        for g in lista_generos:
            if g in top_5_generos:
                return g
        return "Otros"

    df_tiempos["Genero_Principal"] = df_tiempos["Genres_list"].apply(asignar_genero_principal)
    
    categorias_genero = top_5_generos + ["Otros"]
    colores_pastel = px.colors.qualitative.Pastel[:len(categorias_genero)]
    mapa_colores = dict(zip(categorias_genero, colores_pastel))

    # 4. Definir límites dinámicos de Outliers
    max_price_actual = df_tiempos["Price"].max()
    limite_x = 100 if max_price_actual > 100 else max_price_actual

    # 5. CREAR LA ESTRUCTURA DE SUBPLOTS
    fig_global = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Mediana de Juego Total", "Promedio de Juego Total", "Mediana (Últimas 2 Semanas)"),
        horizontal_spacing=0.05
    )

    # 6. ENROUTAR LOS DATOS POR GÉNERO (Usando WebGL via Scattergl)
    for gen in categorias_genero:
        df_sub = df_tiempos[df_tiempos["Genero_Principal"] == gen]
        
        if not df_sub.empty:
            color_asignado = mapa_colores[gen]

            # --- SUBTRAMA 1 (Mediana Total) ---
            fig_global.add_trace(
                go.Scattergl( # <--- CAMBIO CLAVE: Usamos aceleración por hardware
                    x=df_sub["Price"], y=df_sub["Horas_Mediana_Total"],
                    mode="markers", name=gen, legendgroup=gen,
                    marker=dict(size=5, color=color_asignado, line=dict(width=0.3, color="white")),
                    hovertext=df_sub["Name"],
                    hovertemplate="<b>%{hovertext}</b><br>Precio: %{x}€<br>Horas: %{y:.1f}<extra></extra>",
                    showlegend=True
                ),
                row=1, col=1
            )

            # --- SUBTRAMA 2 (Promedio Total) ---
            fig_global.add_trace(
                go.Scattergl( # <--- CAMBIO CLAVE
                    x=df_sub["Price"], y=df_sub["Horas_Promedio_Total"],
                    mode="markers", name=gen, legendgroup=gen,
                    marker=dict(size=5, color=color_asignado, line=dict(width=0.3, color="white")),
                    hovertext=df_sub["Name"],
                    hovertemplate="<b>%{hovertext}</b><br>Precio: %{x}€<br>Horas: %{y:.1f}<extra></extra>",
                    showlegend=False
                ),
                row=1, col=2
            )

            # --- SUBTRAMA 3 (Mediana 2 Semanas) ---
            fig_global.add_trace(
                go.Scattergl( # <--- CAMBIO CLAVE
                    x=df_sub["Price"], y=df_sub["Horas_Mediana_2Semanas"],
                    mode="markers", name=gen, legendgroup=gen,
                    marker=dict(size=5, color=color_asignado, line=dict(width=0.3, color="white")),
                    hovertext=df_sub["Name"],
                    hovertemplate="<b>%{hovertext}</b><br>Precio: %{x}€<br>Horas: %{y:.1f}<extra></extra>",
                    showlegend=False
                ),
                row=1, col=3
            )

    # 7. AJUSTES FINALES DE DISEÑO
    max_h1 = df_tiempos["Horas_Mediana_Total"].max()
    max_h2 = df_tiempos["Horas_Promedio_Total"].max()
    max_h3 = df_tiempos["Horas_Mediana_2Semanas"].max()

    fig_global.update_layout(
        template="plotly_dark",
        height=480,
        margin=dict(l=20, r=20, t=50, b=50),
        legend=dict(traceorder="normal", itemclick="toggle", itemdoubleclick="toggleothers")
    )

    # Límites de visualización independientes
    fig_global.update_xaxes(title_text="Precio (€)", range=[0, limite_x], row=1, col=1)
    fig_global.update_yaxes(title_text="Horas", range=[0, 200 if max_h1 > 200 else max_h1], row=1, col=1)

    fig_global.update_xaxes(title_text="Precio (€)", range=[0, limite_x], row=1, col=2)
    fig_global.update_yaxes(title_text="Horas", range=[0, 300 if max_h2 > 300 else max_h2], row=1, col=2)

    fig_global.update_xaxes(title_text="Precio (€)", range=[0, limite_x], row=1, col=3)
    fig_global.update_yaxes(title_text="Horas", range=[0, 40 if max_h3 > 40 else max_h3], row=1, col=3)

    st.plotly_chart(fig_global, use_container_width=True)

else:
    st.info("No hay datos para mostrar con los filtros seleccionados.")
# ==============================================================================
# GRÁFICA 6 — Mapa de calor de correlaciones (Versión Estática y Fluida)
# ==============================================================================
st.subheader("🔥 Mapa de calor de correlaciones")

# 1. Filtramos automáticamente las columnas numéricas
numeric_df = filtered_df.select_dtypes(include=["int64", "float64"])

if not numeric_df.empty and len(numeric_df.columns) > 1:
    # Calculamos la matriz de correlación
    corr = numeric_df.corr()
    columnas = list(corr.columns)

    # 2. Dibujamos el mapa estático con Plotly Express
    fig_corr = px.imshow(
        corr,
        x=columnas,
        y=columnas,
        color_continuous_scale="Viridis", # Excelente contraste para modo oscuro
        zmin=-1, zmax=1,                  # Rango fijo de correlación lineal
        text_auto=".2f",                  # Pinta los números con dos decimales de forma nativa
        title="Matriz de Correlación Lineal",
        template="plotly_dark",
        aspect="auto"
    )

    # 3. Ajustes estéticos fijos de tamaño y diseño
    fig_corr.update_layout(
        height=600,
        margin=dict(l=150, r=50, t=50, b=100),
        # 'select' es el modo estático estándar; desactivamos cualquier lógica de clics complejos
        dragmode="select" 
    )
    
    # Forzamos un tamaño de fuente pequeño y limpio para los números internos
    fig_corr.update_traces(
        textfont=dict(size=10, family="Arial"),
        hovertemplate="Variable X: %{x}<br>Variable Y: %{y}<br>Correlación: %{z:.2f}<extra></extra>"
    )

    # Rotamos los textos del eje X para que no se solapen si son nombres largos
    fig_corr.update_xaxes(tickangle=45, tickfont=dict(size=11))
    fig_corr.update_yaxes(tickfont=dict(size=11))

    # Renderizado directo en Streamlit sin callbacks intermedios
    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("No hay suficientes variables numéricas para calcular el mapa de calor.")


# ==============================================================================
# GRÁFICA 7 — ANÁLISIS DE RENDIMIENTO EN METACRITIC Y COMUNIDAD
# ==============================================================================

# 1. CONTROL DE FILTRO: Botones de Tramo de Precios
# ==============================================================================
if "Price" in filtered_df.columns:
    st.write("### 💰 Selecciona el Tramo de Inversión / Precio")
opcion_precio = st.radio(
    "Elige el rango de precio para analizar la competencia:",
    ["Todos", "Menos de 5€", "5€ - 10€", "10€ - 20€", "20€ - 40€", "Más de 40€"],
    horizontal=True
)

# Filtramos sobre el 'df' global que ya viene limpio de software y basura
df_p = filtered_df.copy()
if opcion_precio == "Menos de 5€": df_p = df_p[df_p["Price"] < 5]
elif opcion_precio == "5€ - 10€": df_p = df_p[(df_p["Price"] >= 5) & (df_p["Price"] < 10)]
elif opcion_precio == "10€ - 20€": df_p = df_p[(df_p["Price"] >= 10) & (df_p["Price"] < 20)]
elif opcion_precio == "20€ - 40€": df_p = df_p[(df_p["Price"] >= 20) & (df_p["Price"] < 40)]
elif opcion_precio == "Más de 40€": df_p = df_p[df_p["Price"] >= 40]

if not df_p.empty:
    df_p["Nombre_Con_Genero"] = df_p["Name"] + " (" + df_p["Genero_Principal"] + ")"

    # --- GRÁFICA I: Géneros Amados (Recuperando el estilo) ---
    st.subheader("🔥 Géneros Más Amados")
    df_exp = df_p.explode("Genres_list")
    df_rank = df_exp.groupby("Genres_list").agg({"Aceptacion_Real": "mean", "Name": "count"}).rename(columns={"Name": "Total"})
    df_rank = df_rank[df_rank["Total"] >= (5 if opcion_precio == "Más de 40€" else 10)]
    
    fig1 = px.bar(df_rank.sort_values("Aceptacion_Real"), x="Aceptacion_Real", y=df_rank.index, 
                  color="Aceptacion_Real", color_continuous_scale="Plasma", orientation="h", 
                  template="plotly_dark", text_auto=".1f")
    fig1.update_layout(xaxis_range=[0, 100], yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig1, use_container_width=True)

    # --- GRÁFICA II: Favoritos (Estilo optimizado) ---
    st.subheader("🔥 Los Favoritos de la Comunidad")
    df_top = df_p[(df_p["Total_Reviews"] >= 500) & (df_p["Peak_ccu"] >= 100)].sort_values(by="Aceptacion_Real", ascending=False).head(20)
    fig2 = px.bar(df_top, x="Aceptacion_Real", y="Nombre_Con_Genero", color="Total_Reviews", 
                  color_continuous_scale="Plasma", orientation="h", template="plotly_dark", text_auto=".1f")
    fig2.update_layout(xaxis_range=[95, 100.1], yaxis={'categoryorder': 'total ascending'}, height=650)
    st.plotly_chart(fig2, use_container_width=True)

    # --- GRÁFICA III: Metacritic (Estilo limpio) ---
    st.subheader("🏆 Top juegos por Metacritic")
    df_meta = df_p[df_p["Metacritic_score"] > 0].sort_values("Metacritic_score", ascending=False).head(20)
    fig3 = px.bar(df_meta, x="Metacritic_score", y="Nombre_Con_Genero", color="Aceptacion_Real", 
                  color_continuous_scale="Viridis", orientation="h", template="plotly_dark", text_auto=True)
    fig3.update_layout(xaxis_range=[0, 100], yaxis={'categoryorder': 'total ascending'}, height=650)
    st.plotly_chart(fig3, use_container_width=True)

    # --- GRÁFICA IV: Rentabilidad Género (Corrigiendo el comportamiento raro) ---
    st.subheader("🏅 Rentabilidad por Género Puro")
    # Para la gráfica IV, es mejor agrupar por Género Principal para que el eje Y no se vuelva loco
    df_g4 = df_p[df_p["Metacritic_score"] > 0].groupby("Genero_Principal").agg({"Metacritic_score": "mean", "Aceptacion_Real": "mean"}).reset_index()
    fig4 = px.bar(df_g4, x="Metacritic_score", y="Genero_Principal", color="Aceptacion_Real", 
                  color_continuous_scale="Viridis", orientation="h", template="plotly_dark", text_auto=".1f")
    fig4.update_layout(xaxis_range=[0, 100], yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig4, use_container_width=True)

# --- GRÁFICA VI: Matriz de Oportunidad (Aceptación vs. Mercado) ---
st.subheader("🚀 Matriz de Oportunidad: Calidad vs. Tamaño de Mercado")

# Agrupamos por género principal calculando la media de aceptación y la suma de mercado
df_scatter = df_p.groupby("Genero_Principal").agg({
    "Aceptacion_Real": "mean",
    "Mercado_Estimado": "sum",
    "Name": "count" # Para el tamaño de la burbuja
}).reset_index()

# Creamos el gráfico de dispersión
fig6 = px.scatter(
    df_scatter, 
    x="Aceptacion_Real", 
    y="Mercado_Estimado", 
    size="Name", 
    color="Genero_Principal",
    hover_name="Genero_Principal",
    size_max=60,
    template="plotly_dark",
    title="¿Dónde está la oportunidad? (Burbuja = Cantidad de juegos)",
    log_y=True # Usamos escala logarítmica en Y porque las diferencias de mercado son gigantes
)

fig6.update_layout(
    xaxis_title="Aceptación Media (%)",
    yaxis_title="Mercado Estimado Total (€) (Log)",
    showlegend=True
)
# Añadir esto a tu código de fig6
fig6.add_vline(x=df_scatter["Aceptacion_Real"].mean(), line_dash="dash", line_color="white")
fig6.add_hline(y=df_scatter["Mercado_Estimado"].median(), line_dash="dash", line_color="white")

st.plotly_chart(fig6, use_container_width=True)

st.subheader("📊 Mercado por Género")
df_mercado = df_p.groupby("Genero_Principal")["Mercado_Estimado"].sum().reset_index()

fig = px.treemap(
    df_mercado, 
    path=['Genero_Principal'], 
    values='Mercado_Estimado',
    color='Mercado_Estimado',
    color_continuous_scale='Viridis',
    template="plotly_dark"
)
st.plotly_chart(fig, use_container_width=True)

# ============================
# GRÁFICA 8 — Compatibilidad por plataforma
# ============================
st.subheader("🖥️ Compatibilidad por plataforma")

# 1. Calculamos los totales individuales como ya hacías
total_windows = filtered_df["Windows"].sum()
total_mac = filtered_df["Mac"].sum()
total_linux = filtered_df["Linux"].sum()

# 2. Calculamos cuántos juegos son compatibles con las TRES plataformas a la vez
# Esto busca filas donde Windows, Mac y Linux sean True simultáneamente
total_todos = filtered_df[(filtered_df["Windows"] == True) & 
                          (filtered_df["Mac"] == True) & 
                          (filtered_df["Linux"] == True)].shape[0]

# 3. Creamos un nuevo diccionario/Series con los datos organizados
platform_data = {
    "Plataforma": ["Windows", "Mac", "Linux", "Todas (Multiplataforma)"],
    "Cantidad de Juegos": [total_windows, total_mac, total_linux, total_todos]
}

# 4. Graficamos usando el diccionario
fig_platform = px.bar(
    platform_data,
    x="Plataforma",
    y="Cantidad de Juegos",
    title="Compatibilidad por plataforma",
    text="Cantidad de Juegos", # Añade el número encima de la barra para mejor lectura
    color="Plataforma" # Opcional: le da un color distinto a cada barra (incluida la de 'Todas')
)

# Mejoramos el diseño para que se vea más limpio
fig_platform.update_traces(textposition='outside')
fig_platform.update_layout(showlegend=False)

st.plotly_chart(fig_platform, use_container_width=True)

st.subheader("📈 Evolución de compatibilidad por año")

# 1. Asegúrate de tener una columna de año. 
# Si tienes 'Release_date' en formato fecha, puedes extraer el año así:
# filtered_df['Year'] = pd.to_datetime(filtered_df['Release_date']).dt.year

# Nota: Ajusta 'Year' al nombre exacto de tu columna de años si es diferente.
if "Year" in filtered_df.columns:
    
    # 2. Creamos la columna 'Todos' en el DataFrame temporal para poder agruparla igual
    df_temporal = filtered_df.copy()
    df_temporal["Todos"] = (
        df_temporal["Windows"] & df_temporal["Mac"] & df_temporal["Linux"]
    )
    
    # 3. Agrupamos por año y sumamos los True de cada plataforma
    df_evolution = df_temporal.groupby("Year")[["Windows", "Mac", "Linux", "Todos"]].sum().reset_index()
    
    # Opcional: Filtrar años raros (por ejemplo, si hay fechas vacías o del futuro)
    df_evolution = df_evolution[(df_evolution["Year"] >= 2000) & (df_evolution["Year"] <= 2026)]

    # 4. Transformamos el DataFrame para que Plotly lo entienda mejor (formato largo)
    df_melted = df_evolution.melt(
        id_vars=["Year"], 
        value_vars=["Windows", "Mac", "Linux", "Todos"],
        var_name="Plataforma", 
        value_name="Cantidad de Juegos"
    )

    # 5. Creamos el gráfico de líneas
    fig_line = px.line(
        df_melted,
        x="Year",
        y="Cantidad de Juegos",
        color="Plataforma",
        title="Evolución del soporte de plataformas por año de lanzamiento",
        markers=True # Añade puntitos en cada año para que se lea mejor
    )
    
    # Mejoras visuales
    fig_line.update_layout(
        xaxis_title="Año de Lanzamiento",
        yaxis_title="Número de Juegos",
        hovermode="x unified" # Al pasar el ratón, muestra los datos de todas las líneas a la vez
    )

    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning("No se encontró la columna 'Year' o 'Release_date' para calcular la evolución temporal.")

# ============================
# GRÁFICA 9 — Nube de palabras de Tags
# ============================
st.subheader("☁️ Nube de palabras de Tags")
tags = " ".join(filtered_df["Tags"].dropna().tolist())
wc = WordCloud(width=800, height=400, background_color="black").generate(tags)
fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
ax_wc.imshow(wc, interpolation="bilinear")
ax_wc.axis("off")
st.pyplot(fig_wc)

# ============================
# RECOMENDADOR SIMPLE
# ============================
st.subheader("🤖 Recomendador híbrido (géneros + tags + precio + positivos)")

game = st.selectbox("Selecciona un juego", df["Name"].dropna().unique())

df["Tag_List"] = df["Tags"].apply(
    lambda x: [t.strip() for t in x.split(",")] if isinstance(x, str) else []
)


if game:
    row = df[df["Name"] == game].iloc[0]

    # --- Preparar listas ---
    genres_target = set(row["Genres"].split(",") if isinstance(row["Genres"], str) else [])
    tags_target = set(row["Tag_List"] if isinstance(row["Tag_List"], list) else [])

    price_target = row["Price"]
    pos_target = row["Positive"]

    # --- Funciones de similitud ---
    def jaccard(a, b):
        a, b = set(a), set(b)
        return len(a & b) / len(a | b) if len(a | b) else 0

    def sim_price(p):
        max_price = max(df["Price"].max(), 1)
        return 1 - abs(p - price_target) / max_price

    def sim_positive(p):
        return 1 - abs(p - pos_target) / df["Positive"].max()

    # --- Calcular similitudes ---
    df["sim_genres"] = df["Genres"].apply(
        lambda x: jaccard(genres_target, x.split(",") if isinstance(x, str) else [])
    )

    df["sim_tags"] = df["Tag_List"].apply(
        lambda x: jaccard(tags_target, x if isinstance(x, list) else [])
    )

    df["sim_price"] = df["Price"].apply(sim_price)
    df["sim_pos"] = df["Positive"].apply(sim_positive)

    # --- Score híbrido (ajustado) ---
    df["similarity_hybrid"] = (
        0.5 * df["sim_tags"] +
        0.3 * df["sim_genres"] +
        0.1 * df["sim_price"] +
        0.1 * df["sim_pos"]
    )

    recs = (
        df[df["Name"] != game]
        .sort_values("similarity_hybrid", ascending=False)
        .head(20)
    )

    st.write("Juegos recomendados:")
    st.dataframe(recs[["Name", "Genres", "Price", "Positive", "similarity_hybrid"]])
