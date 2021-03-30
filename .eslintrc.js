module.exports = {
  root: true,
  plugins: ['vue', 'import', 'simple-import-sort', '@typescript-eslint'],
  env: {
    node: true,
  },
  extends: [
    'airbnb-typescript/base',
    'plugin:vue/vue3-recommended',
    'prettier',
  ],
  overrides: [
    {
      files: ['*.vue'],
      rules: {
        indent: 'off',
      },
    },
    {
      files: ['**.js'],
      parser: 'vue-eslint-parser',
    },
  ],
  rules: {
    'sort-vars': 'error',
    'simple-import-sort/imports': 'error',
    'simple-import-sort/exports': 'error',
    'simple-import-sort/exports': 'error',
    'vue/no-mutating-props': 'off',
  },
  parserOptions: {
    tsconfigRootDir: __dirname,
    parser: '@typescript-eslint/parser',
    project: 'tsconfig.json',
    extraFileExtensions: ['.vue'],
  },
  settings: {
    'import/resolver': {
      typescript: { alwaysTryTypes: true },
    },
  },
};
