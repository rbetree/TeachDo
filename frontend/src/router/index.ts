import { createRouter, createWebHistory } from 'vue-router'
import Editor from '@/views/Editor/index.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('@/views/About.vue')
  },
  {
    path: '/outline',
    name: 'Outline',
    component: () => import('@/views/Outline/index.vue')
  },
  {
    path: '/ppt',
    name: 'PPT',
    component: () => import('@/views/PPT/index.vue')
  },
  {
    path: '/editor',
    name: 'Editor',
    component: Editor
  },
  {
    path: '/app/:id?',
    name: 'APP',
    component: () => import('@/views/APP/index.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
