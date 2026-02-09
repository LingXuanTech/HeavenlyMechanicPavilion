import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    const isAnalyze = mode === 'analyze';

    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
      },
      plugins: [
        react(),
        tailwindcss(),
        // Bundle 分析模式: npm run build -- --mode analyze
        ...(isAnalyze
          ? [
              import('rollup-plugin-visualizer').then((m) =>
                m.visualizer({ open: true, gzipSize: true, brotliSize: true }),
              ),
            ]
          : []),
      ],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.NEXT_PUBLIC_API_URL': JSON.stringify(env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api')
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      },
      build: {
        rollupOptions: {
          output: {
            manualChunks: {
              // React 生态 (~150KB)
              'vendor-react': ['react', 'react-dom', 'react-router-dom'],
              // 图表库 (~300KB)
              'vendor-charts': ['recharts', 'lightweight-charts'],
              // 动画库 (~100KB)
              'vendor-motion': ['framer-motion'],
              // 数据层
              'vendor-query': ['@tanstack/react-query'],
            },
          },
        },
      },
    };
});
