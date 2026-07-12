import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// Config de Vite: en dev, /api se redirige al backend FastAPI en :8000.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/icon.svg"],
      manifest: {
        name: "KaraokeTandem",
        short_name: "Karaoke",
        description: "Karaoke party app: canciones, turnos, retos y ranking.",
        theme_color: "#0a0a0f",
        background_color: "#0a0a0f",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" },
        ],
      },
      workbox: {
        // Cachea el shell de la app (JS/CSS/HTML) para que abra offline.
        globPatterns: ["**/*.{js,css,html,svg,webp,woff2}"],
        runtimeCaching: [
          {
            // Lecturas GET a la API: red primero, y si no hay conexión usa el cache.
            urlPattern: /\/api\/.*/,
            handler: "NetworkFirst",
            method: "GET",
            options: {
              cacheName: "api-cache",
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 },
              networkTimeoutSeconds: 4,
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts",
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
