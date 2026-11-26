import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// Pages are lazy-loaded so each route is its own chunk.
const routes: RouteRecordRaw[] = [
  { path: '/', name: 'dashboard', component: () => import('@/pages/HomePage.vue'), meta: { title: 'Dashboard' } },
  { path: '/transactions', name: 'transactions', component: () => import('@/pages/TransactionsPage.vue'), meta: { title: 'Transactions' } },
  { path: '/budgets', name: 'budgets', component: () => import('@/pages/BudgetsPage.vue'), meta: { title: 'Budgets' } },
  { path: '/accounts', name: 'accounts', component: () => import('@/pages/AccountsPage.vue'), meta: { title: 'Accounts' } },
  { path: '/categories', name: 'categories', component: () => import('@/pages/CategoriesPage.vue'), meta: { title: 'Categories' } },
  { path: '/analytics', name: 'analytics', component: () => import('@/pages/AnalyticsPage.vue'), meta: { title: 'Analytics' } },
  { path: '/recurring', name: 'recurring', component: () => import('@/pages/RecurringPage.vue'), meta: { title: 'Recurring payments' } },
  { path: '/goals', name: 'goals', component: () => import('@/pages/GoalsPage.vue'), meta: { title: 'Savings goals' } },
  { path: '/settings', name: 'settings', component: () => import('@/pages/SettingsPage.vue'), meta: { title: 'Settings' } },
  { path: '/profile', name: 'profile', component: () => import('@/pages/ProfilePage.vue'), meta: { title: 'Profile' } },
]

// Component gallery for design review; only in builds made with VITE_DESIGN_GALLERY=1.
if (import.meta.env.VITE_DESIGN_GALLERY === '1') {
  routes.push({ path: '/design', name: 'design', component: () => import('@/pages/DesignGallery.vue'), meta: { title: 'Design' } })
}
routes.push({ path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/pages/NotFound.vue') })

const router = createRouter({ history: createWebHistory('/expense'), routes })

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} – Expense Tracker` : 'Expense Tracker'
})

export default router
