# 🎤 KaraokeTandem

App de karaoke para fiestas: lista de canciones con votación, sesiones con
turnos rotativos, retos, ranking con logros, estadísticas personales e
historial — todo guardado en un Google Sheet.

- **Backend**: FastAPI (Python), Google Sheets como base de datos vía
  `gspread` + cuenta de servicio.
- **Frontend**: React + Vite + Tailwind, PWA con soporte offline (Workbox).
- **Despliegue**: una sola imagen Docker (`Dockerfile`), lista para Render
  (`render.yaml`).

Ver [DEPLOY.md](./DEPLOY.md) para la guía completa de instalación (crear la
cuenta de servicio de Google, correr en local, desplegar).

## Funcionalidades

- **Semana**: agregar canciones, buscar/filtrar por género, votar (una vez
  por persona), Top 10, exportar CSV.
- **Karaoke**: crear sesión, turnos rotativos automáticos (nunca la misma
  persona dos veces seguidas), selección aleatoria evitando repetidas,
  marcar cantada con puntuación 1–10, saltar canción, link directo a YouTube.
- **Retos**: reto aleatorio por categoría (Normal, Picante, Creativo, Grupo),
  crear retos personalizados.
- **Ranking**: de la noche e histórico, con logros/badges calculados
  automáticamente (Debut, Maratonista, Voz de Oro, Fiel Asistente, Explorador
  de Géneros).
- **Estadísticas**: canciones cantadas, promedio de puntuación, géneros
  favoritos, mejores presentaciones — por persona.
- **Historial**: todas las sesiones pasadas con su playlist.
