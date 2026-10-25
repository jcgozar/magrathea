import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api goes to the Spring Boot service.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8080" } },
});
