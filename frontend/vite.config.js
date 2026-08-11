import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./", // This ensures assets load correctly
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
  server: {
    port: 3000,
  },
});
