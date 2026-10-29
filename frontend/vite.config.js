import { copyFile, mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En el stand, FastAPI sirve dist/ con StaticFiles(html=True), que no conoce las rutas de React.
// Copiar index.html a cada ruta hace que /panel y /acerca abran aunque se recargue la página
// o se entre directo desde el QR.
const RUTAS = ['panel', 'acerca']
const rutasEstaticas = {
  name: 'rutas-estaticas',
  apply: 'build',
  async closeBundle() {
    const dist = resolve(import.meta.dirname, 'dist')
    for (const ruta of RUTAS) {
      await mkdir(resolve(dist, ruta), { recursive: true })
      await copyFile(resolve(dist, 'index.html'), resolve(dist, ruta, 'index.html'))
    }
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), rutasEstaticas],
  // En desarrollo, /api se reenvía al backend de FastAPI (docs/05c §3.4): sin problemas de CORS.
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
