const fs = require('fs');
const path = require('path');
const { compile } = require('json-schema-to-typescript');

async function main() {
  const root = path.resolve(__dirname, '../../contracts/generated');
  const index = JSON.parse(fs.readFileSync(path.join(root, 'schema-index.json')));
  const definitions = {};
  for (const name of index.schemas) {
    const schema = JSON.parse(fs.readFileSync(path.join(root, `${name}.schema.json`)));
    Object.assign(definitions, schema.$defs || {});
    delete schema.$defs;
    definitions[name] = schema;
  }
  const schema = { title: 'FoundationContracts', type: 'object', additionalProperties: false, properties: Object.fromEntries(index.schemas.map((name) => [name, { $ref: `#/$defs/${name}` }])), $defs: definitions };
  const types = await compile(schema, 'FoundationContracts', { bannerComment: '/* Generated from Pydantic Phase 0 schemas. Do not edit. */', unreachableDefinitions: true });
  const target = path.resolve(__dirname, '../src/contracts/generated.d.ts');
  fs.mkdirSync(path.dirname(target), { recursive: true });
  if (process.argv.includes('--check')) {
    if (fs.readFileSync(target, 'utf8') !== types) throw new Error('Stale generated TypeScript contracts');
    console.log('Generated TypeScript contracts match source schemas.');
  } else { fs.writeFileSync(target, types); console.log('Generated TypeScript foundation contracts.'); }
}
main().catch((e) => { console.error(e); process.exit(1); });