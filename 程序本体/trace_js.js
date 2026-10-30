const fs = require('fs');
const src = fs.readFileSync('C:/Users/Edson/code/.vscode/量化交易/程序本体/web/app.js', 'utf8');
const lines = src.split('\n');
let depth = 0;
let inBt = false; // inside template literal

for (let i = 0; i < lines.length; i++) {
  let line = lines[i];
  let j = 0;
  while (j < line.length) {
    let c = line[j];
    // Skip escaped chars
    if (c === '\\' && j + 1 < line.length) { j += 2; continue; }
    // Backtick toggles template literal mode
    if (c === '`') { inBt = !inBt; j++; continue; }
    if (inBt) {
      // Inside template literal: only count ${...} expressions
      if (c === '$' && j + 1 < line.length && line[j + 1] === '{') {
        depth++; j += 2; continue;
      }
      if (c === '}') { depth--; }
      j++; continue;
    }
    // Outside template literal: count all braces
    if (c === '{') depth++;
    else if (c === '}') depth--;
    j++;
  }
  if (depth < 0) { console.log('NEGATIVE at line', i + 1, 'depth=', depth); break; }
  if (i >= 397 && i <= 512) console.log('L' + (i + 1) + ': d=' + depth + ' ' + line.substring(0, 55));
}
console.log('Final:', depth);
