import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
/** Same file as backend + Docker: repo / deploy / .env */
const deployEnvDir = path.resolve(__dirname, "../../deploy");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, deployEnvDir, "VITE_");
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || "http://127.0.0.1:8000";
  const port = Number(env.VITE_DEV_PORT) || 5173;

  return {
    envDir: deployEnvDir,
    plugins: [react()],
    server: {
      port,
      proxy: {
        "/api": { target: proxyTarget, changeOrigin: true },
      },
    },
  };
});
