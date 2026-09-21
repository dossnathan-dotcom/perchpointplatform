// Run the same frontend rules from the repository root or the frontend directory.
const frontend = require('./frontend/eslint.config.cjs');

module.exports = frontend.map((configuration) => ({
  ...configuration,
  ...(configuration.files ? { files: configuration.files.map((pattern) => `frontend/${pattern}`) } : {}),
  ...(configuration.ignores ? { ignores: configuration.ignores.map((pattern) => `frontend/${pattern}`) } : {}),
}));