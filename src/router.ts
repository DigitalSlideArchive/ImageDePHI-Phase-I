import Home from 'src/views/Home.vue';
import ItemDetail from 'src/views/ItemDetail.vue';
import { createRouter, createWebHistory } from 'vue-router';

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
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
