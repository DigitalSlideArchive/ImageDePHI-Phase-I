import './index.scss';

import { createApp } from 'vue';

import ModalAnnotator from './views/ModalAnnotate.vue';

const app = createApp(ModalAnnotator);
app.mount('#app');
