import Vue from '@vitejs/plugin-vue';
import type { UserConfig } from 'vite';

export interface ConditionalServe {
  command: 'serve';
  mode: 'development' | 'production';
}

// https://vitejs.dev/config/
export default (o: ConditionalServe) => {
  const config: UserConfig = {
    plugins: [Vue()],
  };
  // Add a proxy to the API server
  if (o.command === 'serve' && o.mode === 'development') {
    config.server = {
      proxy: {
        '^/api/v1/.*': {
          target: 'http://localhost:8080',
        },
      },
    };
  }
  return config;
};
