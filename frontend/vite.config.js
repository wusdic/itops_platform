import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()]
    }),
    Components({
      resolvers: [ElementPlusResolver()]
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://172.20.0.7:8000',
        changeOrigin: true,
        // 强制使用 IPv4，避免 Vite 代理尝试 IPv6 导致 ECONNREFUSED
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            if (err.code === 'ECONNREFUSED') {
              console.error('代理连接被拒绝，请检查后端服务是否在 127.0.0.1:8000 运行')
            }
          })
        }
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
