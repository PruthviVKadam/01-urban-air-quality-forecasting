import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// App build/dev config. Test config lives in vitest.config.ts to avoid the
// Vite/Vitest type duplication that comes from mixing the two `defineConfig`s.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
});
