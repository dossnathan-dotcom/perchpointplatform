const react = require('eslint-plugin-react');
const hooks = require('eslint-plugin-react-hooks');
const a11y = require('eslint-plugin-jsx-a11y');
const globals = require('globals');
module.exports = [
  { ignores: ['node_modules/**','build/**','plugins/**','src/components/ui/**','src/contracts/**','src/hooks/**'] },
  { files: ['src/**/*.test.js'], languageOptions: { globals: globals.jest } },
  { files: ['src/**/*.{js,jsx}'], languageOptions: { ecmaVersion: 'latest', sourceType: 'module', parserOptions: { ecmaFeatures: { jsx: true } }, globals: {...globals.browser, ...globals.node} }, plugins: { react, 'react-hooks': hooks, 'jsx-a11y': a11y }, settings: { react: { version: 'detect' } }, rules: { ...hooks.configs.recommended.rules, ...a11y.configs.recommended.rules, 'react/jsx-uses-vars':'error', 'no-unused-vars':['error',{argsIgnorePattern:'^_',varsIgnorePattern:'^_'}], 'no-undef':'error' } },
];