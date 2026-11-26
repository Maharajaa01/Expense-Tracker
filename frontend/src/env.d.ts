/// <reference types="vite/client" />
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, any>
  export default component
}

/** Values injected into window by www/expense.py via the jinjaBootData plugin. */
interface Window {
  user?: import('./services/boot').BootUser
  csrf_token?: string
  site_name?: string
  app_version?: string
  currency?: string
  profile?: import('./services/boot').BootProfile | null
  server_date?: string
}

interface ImportMetaEnv {
  readonly VITE_DESIGN_GALLERY?: string
}
