import { fileURLToPath, URL } from 'node:url';
import path from 'node:path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

const rootDir = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig(() => ({
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': {
        // 端口可由 start.py / Settings 页通过 MAIN_API_PORT 注入，避免“端口改了但 proxy 没改”的漂移。
        target: `http://127.0.0.1:${process.env.MAIN_API_PORT || '6800'}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  plugins: [vue()],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `
          @import "@editor/assets/styles/variable.scss";
          @import "@editor/assets/styles/mixin.scss";
        `,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(rootDir, 'src'),
      '@editor': path.resolve(rootDir, 'src/editor-runtime'),
      '#root': path.resolve(rootDir, '.'),
    },
  },
}));
