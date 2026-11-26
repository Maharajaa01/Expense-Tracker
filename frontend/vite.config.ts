import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'node:path'
import fs from 'node:fs'
import crypto from 'node:crypto'
import type { Plugin } from 'vite'

/**
 * Emits sw.js next to the build, with the exact list of hashed assets to
 * precache and a version derived from that list (so a new build installs a
 * new worker and old caches are dropped).
 */
function serviceWorker(): Plugin {
  let base = '/'
  return {
    name: 'et-service-worker',
    apply: 'build',
    configResolved(c) {
      base = c.base
    },
    generateBundle(_opts, bundle) {
      const files = Object.keys(bundle)
        .filter((f) => /\.(js|css|woff2)$/.test(f) && !f.endsWith('sw.js') && !/Italic/.test(f))
        .sort()
        .map((f) => base + f)
      const icons = ['icon-192.png', 'icon-512.png', 'favicon-32.png'].map((i) => `/assets/expense_tracker/icons/${i}`)
      const precache = [...files, ...icons]
      const version = crypto.createHash('sha256').update(precache.join('\n')).digest('hex').slice(0, 12)
      const template = fs.readFileSync(path.resolve(__dirname, 'sw/sw.js'), 'utf8')
      const versionDecl = "const VERSION = '__VERSION__'"
      const precacheDecl = 'const PRECACHE = __PRECACHE__'
      if (!template.includes(versionDecl) || !template.includes(precacheDecl)) {
        this.error('sw/sw.js is missing the VERSION or PRECACHE declaration')
      }
      const src = template
        .replace(versionDecl, `const VERSION = '${version}'`)
        .replace(precacheDecl, `const PRECACHE = ${JSON.stringify(precache)}`)
      this.emitFile({ type: 'asset', fileName: 'sw.js', source: src })
    },
  }
}

// Review builds (e.g. the design gallery) can be written elsewhere with
// ET_OUT_DIR so they never replace what the live site serves.
const reviewOut = process.env.ET_OUT_DIR

// Built assets land in ../expense_tracker/public/frontend (served at
// /assets/expense_tracker/frontend/) and index.html is copied to
// ../expense_tracker/www/expense.html, which Frappe renders with boot data.
export default defineConfig({
  plugins: [
    frappeui({
      frontendRoute: '/expense',
      lucideIcons: true,
      frappeProxy: true,
      jinjaBootData: true,
      buildConfig: reviewOut
        ? { outDir: reviewOut, indexHtmlPath: path.join(reviewOut, 'expense.html'), baseUrl: '/review-assets/', emptyOutDir: true }
        : { indexHtmlPath: '../expense_tracker/www/expense.html', emptyOutDir: true },
    }),
    vue(),
    serviceWorker(),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  build: {
    chunkSizeWarningLimit: 700,
  },
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.spec.ts'],
  },
} as any)
