#!/usr/bin/env node
/**
 * Validate Archify JSON, deliver HTML, and export dual-theme SVG for README.
 *
 * Requires a local Archify checkout (https://github.com/tt-a1i/archify) and Chrome.
 *
 *   $env:ARCHIFY_ROOT = "C:\\path\\to\\archify\\archify"
 *   node scripts/render-archify.mjs
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const irRoot = path.join(repoRoot, 'docs', 'diagrams', 'archify');
const outRoot = path.join(repoRoot, 'docs', 'assets', 'archify');

const diagrams = [
  { type: 'architecture', stem: 'runtime-architecture' },
  { type: 'architecture', stem: 'trace-core-model' },
  { type: 'architecture', stem: 'visualization-intent' },
  { type: 'architecture', stem: 'mcp-evidence-layer' },
  { type: 'workflow', stem: 'mcp-capture-display' },
  { type: 'workflow', stem: 'coding-agent-capture' },
];

function resolveArchifyRoot() {
  const envRoot = process.env.ARCHIFY_ROOT;
  const candidates = [
    envRoot,
    path.join(process.env.TEMP || '', 'archify', 'archify'),
    path.join(repoRoot, 'vendor', 'archify', 'archify'),
  ].filter(Boolean);
  for (const candidate of candidates) {
    const cli = path.join(candidate, 'bin', 'archify.mjs');
    if (fs.existsSync(cli)) return candidate;
  }
  throw new Error(
    'Set ARCHIFY_ROOT to the cloned archify/archify package (the folder that contains bin/archify.mjs).',
  );
}

function runArchify(archifyRoot, args) {
  const cli = path.join(archifyRoot, 'bin', 'archify.mjs');
  const result = spawnSync(process.execPath, [cli, ...args], {
    cwd: repoRoot,
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(
      `archify ${args.join(' ')} failed (exit ${result.status}):\n${result.stdout || ''}\n${result.stderr || ''}`,
    );
  }
  return result.stdout;
}

async function exportSvg(archifyRoot, htmlPath, svgPath) {
  const { ChromeVisualBrowser, findChrome } = await import(
    pathToFileURL(path.join(archifyRoot, 'bin', 'visual-check.mjs')).href
  );
  const chrome = findChrome();
  if (!chrome) {
    throw new Error('Chrome is required to export dual-theme SVG. Set ARCHIFY_CHROME if it is not on PATH.');
  }
  const browser = new ChromeVisualBrowser(chrome);
  try {
    const sessionId = await browser.sessionPromise;
    await browser.cdp.send(
      'Emulation.setDeviceMetricsOverride',
      { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false },
      sessionId,
    );
    const loaded = browser.cdp.waitFor('Page.loadEventFired', sessionId);
    const navigation = await browser.cdp.send(
      'Page.navigate',
      { url: pathToFileURL(htmlPath).href },
      sessionId,
    );
    if (navigation.errorText) throw new Error(`Chrome navigation failed: ${navigation.errorText}`);
    await loaded;

    const svg = await browser.cdp.send('Runtime.evaluate', {
      expression: `(async function () {
        var start = performance.now();
        while (!(window.Archify && Archify.exportMenu && document.querySelector('.diagram-container svg'))) {
          if (performance.now() - start > 15000) throw new Error('Archify viewer did not become ready');
          await new Promise(function (resolve) { setTimeout(resolve, 50); });
        }
        if (window.Archify.readerLayout && typeof Archify.readerLayout.whenStable === 'function') {
          await Archify.readerLayout.whenStable();
        }
        var originalCreateObjectURL = URL.createObjectURL;
        var originalAnchorClick = HTMLAnchorElement.prototype.click;
        var captured;
        URL.createObjectURL = function (blob) {
          captured = blob.text();
          return 'blob:lumiagent-archify-svg';
        };
        HTMLAnchorElement.prototype.click = function () {};
        try {
          await Archify.exportMenu.run('svg');
          if (!captured) throw new Error('SVG export did not produce a blob');
          return await captured;
        } finally {
          URL.createObjectURL = originalCreateObjectURL;
          HTMLAnchorElement.prototype.click = originalAnchorClick;
        }
      })()`,
      awaitPromise: true,
      returnByValue: true,
    }, sessionId);

    if (svg.exceptionDetails) {
      throw new Error(
        svg.exceptionDetails.exception?.description
          || svg.exceptionDetails.text
          || 'SVG export failed',
      );
    }
    const text = svg.result?.value;
    if (typeof text !== 'string' || !text.includes('<svg')) {
      throw new Error('SVG export did not return SVG markup');
    }
    fs.writeFileSync(svgPath, text);
  } finally {
    await browser.close();
  }
}

async function main() {
  const archifyRoot = resolveArchifyRoot();
  fs.mkdirSync(outRoot, { recursive: true });
  for (const diagram of diagrams) {
    const input = path.join(irRoot, `${diagram.stem}.json`);
    const html = path.join(outRoot, `${diagram.stem}.html`);
    const svg = path.join(outRoot, `${diagram.stem}.svg`);
    process.stdout.write(`${diagram.stem}: validate… `);
    runArchify(archifyRoot, ['validate', diagram.type, input, '--quality', 'showcase', '--json']);
    process.stdout.write('deliver… ');
    runArchify(archifyRoot, ['deliver', diagram.type, input, html, '--quality', 'showcase', '--json']);
    process.stdout.write('svg… ');
    await exportSvg(archifyRoot, html, svg);
    const bytes = fs.statSync(svg).size;
    console.log(`ok (${bytes} bytes)`);
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
