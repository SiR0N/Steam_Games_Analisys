# Steam Games Market Insights

## 1. Objetivo del Proyecto
Este dashboard tiene como objetivo reducir la incertidumbre en el proceso de toma de decisiones para el desarrollo de videojuegos, proporcionando una visión analítica del mercado de Steam. El proyecto busca identificar patrones de éxito, evaluar la viabilidad económica por géneros y entender qué factores (precio, tags, métricas de comunidad) correlacionan mejor con la aceptación real de los usuarios.

## 2. Metodología y Fuentes
- **Dataset Original:** 120,000 registros iniciales.
- **Dataset Final:** 83,912 juegos tras el proceso de limpieza.
- **Proceso de filtrado:** Se aplicó una limpieza profunda que eliminó aproximadamente el 30% del volumen inicial. Esta reducción se debió principalmente a la exclusión de software que no clasificaba como videojuego (herramientas de edición, desarrollo, contabilidad, etc.) mediante una lista negra curada, y a la eliminación de registros incompletos o sin actividad de reseñas (`Total_Reviews = 0`). Esto garantiza que el análisis de viabilidad económica y aceptación se base únicamente en productos con una presencia real en el mercado.

## 3. Limitaciones y Sesgos Identificados
Es fundamental reconocer que los datos presentan sesgos inherentes a la naturaleza de la plataforma:

- **Sesgo de Popularidad:** Las métricas están fuertemente sesgadas hacia títulos con alto volumen de reseñas, lo que oculta el rendimiento de juegos de nicho o lanzamientos recientes.
- **Sesgo de Supervivencia:** El análisis refleja el estado actual de la plataforma, ignorando títulos que fueron retirados o cuya presencia comercial es nula.
- **Sesgo de Selección:** La clasificación de "Género Principal" fue simplificada para evitar la ambigüedad, lo que podría ocultar híbridos de géneros que tienen un rendimiento distinto.
- **Sesgo de Estimación:** Al usar el valor mínimo del rango de propietarios (`Estimated_owners_min`), los ingresos calculados representan un "piso" conservador y no deben tomarse como el valor real absoluto de facturación.
- **Sesgo de Modelo de Negocio (Free to Play vs. Premium):** El mercado de Steam está polarizado entre juegos de pago (Premium) y gratuitos (F2P). Los F2P dominan las métricas de volumen (`Peak_ccu`) y tiempo de juego, distorsionando las comparativas tradicionales. En este análisis, se ha considerado que el F2P es un segmento operativo distinto, donde la viabilidad no depende de la venta unitaria inicial sino de la retención y microtransacciones.

## 4. Hallazgos Principales
- **Saturación vs. Aceptación:** Géneros como "Acción" dominan en volumen de mercado, pero presentan una alta saturación competitiva. Géneros de nicho como "Simulación" o "Estrategia" muestran, en promedio, una mayor fidelidad y aceptación por parte de la comunidad.
- **La trampa del precio:** No existe una correlación lineal directa entre un precio elevado y una mayor aceptación; los datos sugieren que la calidad percibida (`Aceptacion_Real`) es el predictor más fuerte de éxito a largo plazo.
- **Matriz de Oportunidad:** Se ha identificado que los juegos con alta aceptación pero mercado estimado medio representan las mejores oportunidades de "Océano Azul" para nuevos desarrolladores.

*Nota técnica:* El análisis estadístico de la `Aceptacion_Real` muestra una alta concentración en rangos positivos, confirmando la existencia de un "sesgo de positividad" característico de las reseñas de Steam, donde el usuario tiende a recomendar aquello que consume.

## 5. Tecnologías Utilizadas
- **Lenguaje:** Python
- **Análisis de datos:** Pandas, NumPy
- **Visualización:** Plotly, Streamlit
---
