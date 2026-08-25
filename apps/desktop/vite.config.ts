import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react") || id.includes("node_modules/scheduler")) return "react-vendor";
          if (id.includes("node_modules/@tauri-apps")) return "tauri-vendor";
          if (id.endsWith("/src/i18n.ts")) return "translations";
          if (id.includes("/src/Phase10Experience.tsx")) return "product-truth";
          if (id.includes("/src/Phase8Experience.tsx") || id.includes("/src/Phase9Experience.tsx")) return "acceptance-surfaces";
          return undefined;
        },
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
