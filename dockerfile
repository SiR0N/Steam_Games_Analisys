# ── 1. IMAGEN BASE ──────────────────────────────────────────────
# Partimos de Python 3.11 en su versión ligera (sin extras).
# NUNCA uses :latest — la versión puede cambiar y romper la app. 
FROM python:3.11-slim

# ── 2. DIRECTORIO DE TRABAJO ───────────────────────────────────── 
# Crea la carpeta /app dentro del contenedor y se mueve a ella. 
# Todo lo que siga ocurrirá dentro de /app. 
WORKDIR /app 
# ── 3. COPIAR DEPENDENCIAS (ANTES que el código) ───────────────── 
# Truco clave de caché: si el código cambia pero el .txt no, 
# Docker salta los pasos 3 y 4 usando caché → build más rápido. 
COPY requirements.txt . 
# ── 4. INSTALAR DEPENDENCIAS ───────────────────────────────────── 
# --no-cache-dir: no guarda caché de pip → imagen más pequeña. 
RUN pip install --no-cache-dir -r requirements.txt 
# ── 5. COPIAR EL RESTO DEL PROYECTO ───────────────────────────── 
# Ahora sí copiamos app.py, pages/, etc. 
# Va DESPUÉS de pip install para aprovechar la caché. 
COPY . . 
# ── 6. EXPONER EL PUERTO ──────────────────────────────────────── 
# Streamlit usa el 8501. EXPOSE solo documenta — no abre el puerto. 
# El puerto se abre en docker run con -p. 
EXPOSE 8501 
# ── 7. COMANDO DE ARRANQUE ────────────────────────────────────── 
# Lo que se ejecuta cuando el contenedor arranca. 
# Formato JSON obligatorio: ["cmd", "arg1", "arg2"] # 0.0.0.0 = accesible desde fuera del contenedor (imprescindible). 
CMD ["streamlit", "run", "test.py", "--server.address=0.0.0.0", "--server.port=8501"]
