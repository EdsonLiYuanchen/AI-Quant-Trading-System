const fs = require('fs');
const src = fs.readFileSync('C:/Users/Edson/code/.vscode/量化交易/程序本体/web/app.js', 'utf8');
const lines = src.split('\n');

// Check template literal balance around the problematic area
for (let i = 410; i < 520; i++) {
  const line = lines[i];
  let btCount = 0;
  for (const c of line) { if (c === '`') btCount++; }
  console.log('L' + (i + 1) + ': bt=' + btCount + ' ' + line.substring(0, 70));
}
