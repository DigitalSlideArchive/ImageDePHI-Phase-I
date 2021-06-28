import Home from './views/Home.vue';
import ItemDetail from './views/ItemDetail.vue';
import Login from './views/Login.vue';
import { createRouter, createWebHistory } from 'vue-router';
import store from './store';

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
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
