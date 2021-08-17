import { createRouter, createWebHistory } from 'vue-router';

import Home from './views/Home.vue';
import ItemDetail from './views/ItemDetail.vue';
import Login from './views/Login.vue';
import ModalAnnotate from './views/ModalAnnotate.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/:itemId',
    name: 'Item',
    component: ItemDetail,
    props: true,
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
  },
  {
    path: '/annotate/:itemId?',
    name: 'ModalAnnotate',
    component: ModalAnnotate,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
