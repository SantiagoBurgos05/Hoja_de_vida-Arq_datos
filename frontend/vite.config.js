import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base relativa: funciona en GitHub Pages (subruta del repositorio). El enrutador usa hash (#/ruta).
export default defineConfig({ base: "./", plugins: [react()], test: { environment: "node" } });
