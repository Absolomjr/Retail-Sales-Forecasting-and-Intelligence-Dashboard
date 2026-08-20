import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Dev requests to /api are proxied to FastAPI, so the browser never sees CORS.
    proxy: {
      "/api": { target: process.env.VITE_API_TARGET ?? "http://localhost:8000", changeOrigin: true },
      "/health": { target: process.env.VITE_API_TARGET ?? "http://localhost:8000", changeOrigin: true },
    },
  },
  preview: { host: true, port: 4173 },
  build: {
    rollupOptions: {
      // Recharts + d3 are most of the bundle and change far less often than app
      // code, so they get their own chunk and stay cached across deploys.
      //
      // This has to be the function form. With the object form Rollup followed
      // recharts' own `import "react"` and pulled React into the charts chunk,
      // leaving the declared `react` chunk empty - which defeated the point,
      // since a recharts bump then busted React's cache entry too.
      output: {
        manualChunks(id) {
          const parts = id.replace(/\\/g, "/").split("node_modules/");
          if (parts.length < 2) return;
          const pkg = parts[parts.length - 1].split("/")[0];
          return pkg === "react" || pkg === "react-dom" || pkg === "scheduler"
            ? "react"
            : "charts";
        },
      },
    },
  },
});
