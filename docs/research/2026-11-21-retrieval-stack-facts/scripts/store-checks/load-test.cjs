const { createRequire } = require('node:module');
const req = createRequire(process.argv[2] + '/package.json');
const Database = req('better-sqlite3');
const sv = req('sqlite-vec');
const db = new Database(':memory:');
sv.load(db);
console.log(process.version, 'better-sqlite3 sqlite', db.prepare('select sqlite_version() v').get().v, 'vec', db.prepare('select vec_version() v').get().v);
const binding = req.resolve('better-sqlite3');
console.log('fs build dir exists:', require('fs').existsSync(require('path').join(binding, '..', '..', 'build')));
