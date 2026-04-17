import { defineConfig } from "vite";

export default defineConfig({
  root: "src",
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/bugs": "http://localhost:5000",
      "/agents": "http://localhost:5000",
      "/api": "http://localhost:5000",
    },
  },
});
