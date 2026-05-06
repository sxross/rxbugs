import { defineConfig } from "vite";

export default defineConfig({
  root: "src",
  base: "/static/",
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/bugs": "http://localhost:5000",
      "/agents": "http://localhost:5000",
      "/api": "http://localhost:5000",
      "/auth": "http://localhost:5000",
    },
  },
});
