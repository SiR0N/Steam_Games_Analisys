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
st.title("GameDev Strategy Lab 🚀")
st.write("Dashboard avanzado con filtros dinámicos, análisis y visualizaciones interactivas.")
st.markdown("""
### ¿Cómo usar esta herramienta?
Este panel está diseñado para reducir la incertidumbre en el desarrollo de videojuegos. Analizamos el mercado de Steam para ayudarte a responder tres preguntas críticas:
1. **¿Qué género tiene mejor recepción?** (Aceptación de usuarios)
2. **¿Cuál es el mercado actual?** (Viabilidad económica)
3. **¿Que plataformas son las mas utilizadas ?**
""")
PARQUET_PATH = "games.parquet"

# ============================
# CARGA DEL PARQUET
# ============================
def load_clean_data():
    # Streamlit solo lee el archivo ya procesado, no tiene que calcular nada
    return pd.read_parquet("games.parquet")

df = load_clean_data()
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
# GRÁFICA 3 — Precio vs Reseñas positivas (Enfoque en Género Principal)
# ============================
st.subheader("⭐ Precio vs Reseñas positivas por Género Principal")

if not filtered_df.empty:
    fig3 = px.scatter(
        filtered_df,
        x="Price",
        y="Positive",
        color="Genero_Principal", # Usamos tu columna limpia
        hover_data=["Name", "Developers"],
        opacity=0.7,
        title="¿Qué géneros tienen mejor acogida según su precio?",
        template="plotly_dark",
        labels={
            "Price": "Precio (€)",
            "Positive": "Reseñas Positivas",
            "Genero_Principal": "Género Principal" 
        }
    )

    # Lógica de límites (se mantiene igual)
    max_price_actual = filtered_df["Price"].max()
    max_pos_actual = filtered_df["Positive"].max()

    limite_x = 100 if max_price_actual > 100 else max_price_actual
    limite_y = 200000 if max_pos_actual > 200000 else max_pos_actual

    fig3.update_layout(
        xaxis_range=[0, limite_x],
        yaxis_range=[0, limite_y],
        # La leyenda a la derecha es mejor si tienes muchos géneros, 
        # pero si es muy larga, usa la opción 'h' (horizontal) que te puse antes
        legend=dict(title="Géneros")
    )

    fig3.update_traces(marker=dict(size=6))

    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No hay datos disponibles para los filtros seleccionados.")


# ==============================================================================
# GRÁFICA: Comparativa de Tiempos de Juego vs Precio (Versión Final Corregida)
# ==============================================================================
st.subheader("⏳ Comparativa de Tiempos de Juego vs Precio")

if not filtered_df.empty:
    # 1. Limpieza de Outliers (Percentil 99)
    p99_mediana = filtered_df["Median_playtime_forever"].quantile(0.99)
    p99_promedio = filtered_df["Average_playtime_forever"].quantile(0.99)
    p99_2weeks = filtered_df["Median_playtime_2weeks"].quantile(0.99)
    p99_precio = filtered_df["Price"].quantile(0.99)
    
    # 2. Definir categorías y colores
    categorias = sorted(filtered_df["Genero_Principal"].unique())
    colores = px.colors.qualitative.Pastel[:len(categorias)]
    mapa_colores = dict(zip(categorias, colores))

    # 3. Crear estructura de subplots
    fig_global = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Mediana (Total)", "Promedio (Total)", "Mediana (2 Semanas)"),
        horizontal_spacing=0.08
    )

    # 4. Dibujar trazas
    columnas_y = ["Median_playtime_forever", "Average_playtime_forever", "Median_playtime_2weeks"]
    limites_y = [p99_mediana / 60, p99_promedio / 60, p99_2weeks / 60]

    for gen in categorias:
        df_sub = filtered_df[filtered_df["Genero_Principal"] == gen]
        if df_sub.empty: continue
            
        color = mapa_colores.get(gen, "#FFFFFF")
        
        for i, col_y in enumerate(columnas_y, 1):
            fig_global.add_trace(
                go.Scattergl(
                    x=df_sub["Price"], 
                    y=df_sub[col_y] / 60,
                    mode="markers", 
                    name=gen, 
                    legendgroup=gen,
                    # El tamaño aquí inicializa la traza
                    marker=dict(size=8, color=color), 
                    showlegend=(i == 1),
                    hovertemplate="<b>%{text}</b><br>Precio: %{x}€<br>Horas: %{y:.1f}<extra></extra>",
                    text=df_sub["Name"]
                ),
                row=1, col=i
            )

    # 5. Ajustes finales de DISEÑO
    fig_global.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=20, r=20, t=50, b=120),
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.45,
            xanchor="center",
            x=0.5,
            font=dict(size=14, color="white"),
            itemsizing="constant" # Esto hace que los iconos de la leyenda sean grandes
        )
    )
    
    # Aplicar límites de percentiles
    for i in range(1, 4):
        fig_global.update_xaxes(title_text="Precio (€)", range=[0, p99_precio], row=1, col=i)
        fig_global.update_yaxes(title_text="Horas", range=[0, limites_y[i-1]], row=1, col=i)

    st.plotly_chart(fig_global, use_container_width=True)
else:
    st.info("No hay datos para mostrar.")

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


import streamlit as st
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# 1. FUNCIÓN DE FILTRADO CON CACHÉ (CORREGIDA)
@st.cache_data
def get_filtered_data(df, opcion):
    df_p = df.copy()
    # Convertir columnas tipo lista a tupla para evitar el error de hashing
    for col in df_p.columns:
        if df_p[col].apply(lambda x: isinstance(x, list)).any():
            df_p[col] = df_p[col].apply(lambda x: tuple(x) if isinstance(x, list) else x)
            
    if opcion == "Menos de 5€": df_p = df_p[df_p["Price"] < 5]
    elif opcion == "5€ - 10€": df_p = df_p[(df_p["Price"] >= 5) & (df_p["Price"] < 10)]
    elif opcion == "10€ - 20€": df_p = df_p[(df_p["Price"] >= 10) & (df_p["Price"] < 20)]
    elif opcion == "20€ - 40€": df_p = df_p[(df_p["Price"] >= 20) & (df_p["Price"] < 40)]
    elif opcion == "Más de 40€": df_p = df_p[df_p["Price"] >= 40]
    return df_p

# 2. CONTROL DE FILTRO
st.write("### 💰 Selecciona el Tramo de Inversión / Precio")
opcion_precio = st.radio(
    "Elige el rango de precio para analizar la competencia:",
    ["Todos", "Menos de 5€", "5€ - 10€", "10€ - 20€", "20€ - 40€", "Más de 40€"],
    horizontal=True
)

df_p = get_filtered_data(filtered_df, opcion_precio)

if not df_p.empty:
    df_p["Nombre_Con_Genero"] = df_p["Name"] + " (" + df_p["Genero_Principal"] + ")"

    # --- GRÁFICA I ---
    st.subheader("🔥 Géneros Más Amados")
    df_rank = df_p.groupby("Genero_Principal").agg({"Aceptacion_Real": "mean", "Name": "count"}).rename(columns={"Name": "Total"})
    df_rank = df_rank[df_rank["Total"] >= (5 if opcion_precio == "Más de 40€" else 10)].sort_values("Aceptacion_Real", ascending=True)
    fig1 = px.bar(df_rank, x="Aceptacion_Real", y=df_rank.index, color="Aceptacion_Real", color_continuous_scale="Plasma", orientation="h", template="plotly_dark", text_auto=".1f")
    fig1.update_layout(xaxis_range=[0, 100], yaxis={'categoryorder': 'array', 'categoryarray': df_rank.index})
    st.plotly_chart(fig1, width='stretch')

    # --- GRÁFICA II ---
    st.subheader("🔥 Los Favoritos de la Comunidad")
    df_top = df_p[(df_p["Total_Reviews"] >= 500) & (df_p["Peak_ccu"] >= 100)].sort_values(by="Aceptacion_Real", ascending=False).head(20)
    fig2 = px.bar(df_top, x="Aceptacion_Real", y="Nombre_Con_Genero", color="Total_Reviews", color_continuous_scale="Plasma", orientation="h", template="plotly_dark", text_auto=".1f")
    fig2.update_layout(xaxis_range=[95, 100.1], yaxis={'categoryorder': 'total ascending'}, height=650)
    st.plotly_chart(fig2, width='stretch')

    # --- GRÁFICA III ---
    st.subheader("🏆 Top juegos por Metacritic")
    df_meta = df_p[df_p["Metacritic_score"] > 0].sort_values("Metacritic_score", ascending=False).head(20)
    fig3 = px.bar(df_meta, x="Metacritic_score", y="Nombre_Con_Genero", color="Aceptacion_Real", color_continuous_scale="Viridis", orientation="h", template="plotly_dark", text_auto=True)
    fig3.update_layout(xaxis_range=[0, 100], yaxis={'categoryorder': 'total ascending'}, height=650)
    st.plotly_chart(fig3, width='stretch')

    # --- GRÁFICA IV ---
    st.subheader("🏅 Rentabilidad por Género Puro")
    df_g4 = df_p[df_p["Metacritic_score"] > 0].groupby("Genero_Principal").agg({"Metacritic_score": "mean", "Aceptacion_Real": "mean"}).reset_index()
    fig4 = px.bar(df_g4, x="Metacritic_score", y="Genero_Principal", color="Aceptacion_Real", color_continuous_scale="Viridis", orientation="h", template="plotly_dark", text_auto=".1f")
    fig4.update_layout(xaxis_range=[0, 100], yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig4, width='stretch')

    # --- GRÁFICA VI ---
    st.subheader("🚀 Matriz de Oportunidad")
    df_scatter = df_p.groupby("Genero_Principal").agg({"Aceptacion_Real": "mean", "Mercado_Estimado": "sum", "Name": "count"}).reset_index()
    fig6 = px.scatter(df_scatter, x="Aceptacion_Real", y="Mercado_Estimado", size="Name", color="Genero_Principal", hover_name="Genero_Principal", size_max=60, template="plotly_dark", log_y=True)
    fig6.add_vline(x=df_scatter["Aceptacion_Real"].mean(), line_dash="dash", line_color="white")
    fig6.add_hline(y=df_scatter["Mercado_Estimado"].median(), line_dash="dash", line_color="white")
    st.plotly_chart(fig6, width='stretch')

    # --- TREEMAP ---
    st.subheader("📊 Mercado por Género")
    df_mercado = df_p.groupby("Genero_Principal")["Mercado_Estimado"].sum().reset_index()
    fig_tree = px.treemap(df_mercado, path=['Genero_Principal'], values='Mercado_Estimado', color='Mercado_Estimado', color_continuous_scale='Viridis', template="plotly_dark")
    st.plotly_chart(fig_tree, width='stretch')
else:
    st.warning("No hay datos para mostrar en este rango de precio.")

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

st.markdown("---")


st.header("🏁 Conclusiones Estratégicas: ¿Dónde invertir tu esfuerzo?")

# Usamos columnas para organizar las conclusiones por temas
col1, col2 = st.columns(2)

with col1:
    st.subheader("💡 Análisis de Mercado")
    st.markdown("""
    * **Acción como gigante:** El género de 'Acción' lidera el volumen de mercado, pero es un entorno de **alta saturación y competencia feroz**.
    * **Estrategia de Nicho:** Géneros como **RPG, Simulación y Estrategia** no dominan por volumen total, pero son los que poseen la **mejor tasa de aceptación** (fidelidad del usuario). Si eres un estudio independiente, el nicho suele ofrecer un camino más sostenible.
    """)

with col2:
    st.subheader("🛠️ Recomendaciones para el Dev")
    st.markdown("""
    * **Estándar de Calidad:** La 'Matriz de Oportunidad' demuestra que, en Steam, **la calidad (aceptación > 70%) es el precio de entrada** para cualquier mercado relevante.
    * **Prioridad Técnica:** Windows es la plataforma indiscutible. La optimización del rendimiento en esta arquitectura no es opcional, es el requisito base para asegurar tu calificación positiva.
    """)

# Conclusión final destacada
st.info("""
### 🚀 Veredicto para el desarrollador:
El mercado actual no premia simplemente el 'lanzamiento' de un juego, sino la **calidad constante**. Si buscas rentabilidad, prioriza géneros con alta aceptación (RPG/Simulación) y asegúrate de que tu experiencia de usuario sea impecable en Windows. El éxito en Steam ya no depende de la cantidad, sino de la **fidelidad que logres generar en tu nicho.**
""")
