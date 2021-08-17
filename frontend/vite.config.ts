import Vue from '@vitejs/plugin-vue';
import type { UserConfig } from 'vite';

// https://vitejs.dev/config/
export default (o: ConditionalServe) => {
  const config: UserConfig = {
    plugins: [Vue()],
  };
  return config;
};
