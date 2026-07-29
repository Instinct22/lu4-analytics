import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxyTarget = process.env.VITE_PROXY_TARGET || "http://localhost";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Router and query client are on every page; keeping them in their own
        // chunk lets the per-page chunks stay cached across deploys.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom", "@tanstack/react-query"],
        },
      },
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: proxyTarget, changeOrigin: true },
      "/media": { target: proxyTarget, changeOrigin: true },
    },
  },
});
