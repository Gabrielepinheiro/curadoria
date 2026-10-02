// pdf.mjs — imprime o HTML da curadoria em PDF (A4 horizontal) com o Chromium.
// Uso: node ferramentas/pdf.mjs entrada.html saida.pdf
import { createRequire } from 'module';
import { pathToFileURL } from 'url';
import path from 'path';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require('/opt/node-tools/node_modules/playwright')); }

const [entrada, saida] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(path.resolve(entrada)).href, { waitUntil: 'networkidle', timeout: 120000 });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: saida, preferCSSPageSize: true, printBackground: true });
await browser.close();
console.log('PDF:', saida);
