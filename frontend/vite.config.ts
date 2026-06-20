import { defineConfig } from "vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    tanstackRouter(),
  ],
  resolve: {
    tsconfigPaths: true,
  },
  server: {
    port: 8080,
  },
  build: {
    chunkSizeWarningLimit: 1000,
  },
});
