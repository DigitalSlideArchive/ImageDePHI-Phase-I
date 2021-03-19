module.exports = {
  ignorePatterns: ['vite.config.ts'],
  root: true,
  env: {
    node: true,
  },
  extends: [
    'airbnb-base/legacy',
    'plugin:vue/vue3-recommended',
    'eslint:recommended',
    '@vue/typescript',
    'plugin:prettier/recommended',
  ],
  plugins: ['vue', 'prettier'],
};
