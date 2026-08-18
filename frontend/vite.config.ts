import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
// Imported from "vitest/config" (not "vite") so the `test` field below
// type-checks — it re-exports Vite's defineConfig merged with Vitest's
// config types.
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split heavy, rarely-changing libraries into their own chunks so a
        // code change doesn't force users to re-download all of vendor JS.
        // Function form (not the object form) so this type-checks regardless
        // of which Rollup type version "vitest/config" vs "vite" resolves.
        manualChunks(id: string) {
          if (id.includes("node_modules/recharts")) return "vendor-charts";
          if (
            id.includes("node_modules/react-hook-form") ||
            id.includes("node_modules/@hookform/resolvers") ||
            id.includes("node_modules/zod")
          ) {
            return "vendor-forms";
          }
          if (
            id.includes("node_modules/react/") ||
            id.includes("node_modules/react-dom") ||
            id.includes("node_modules/react-router-dom") ||
            id.includes("node_modules/scheduler")
          ) {
            return "vendor-react";
          }
        },
      },
    },
  },
});
