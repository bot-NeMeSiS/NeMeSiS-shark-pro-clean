/* Offline build: one SVG composition and the existing shark, no generated artwork. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ROOT = path.resolve(__dirname, '..');
const DIR = path.join(ROOT, 'static/img/app-icons');
const SIZES = [16, 32, 48, 64, 96, 128, 152, 167, 180, 192, 256, 512];

async function build(sharp) {
  const master = fs.readFileSync(path.join(DIR, 'official_app_icon_master.svg'), 'utf8').replace(/\r\n/g, '\n');
  const sourcePath = path.join(DIR, '../nemesis-shark-atmosphere-v2.webp');
  const source = fs.readFileSync(sourcePath);
  // librsvg may not decode embedded WebP; convert losslessly in memory for SVG rendering.
  const sourcePng = await sharp(source).png().toBuffer();
  const embedded = master.replace('../nemesis-shark-atmosphere-v2.webp',
    'data:image/png;base64,' + sourcePng.toString('base64'));
  const fingerprint = crypto.createHash('sha256').update(master).update(source)
    .update(fs.readFileSync(__filename, 'utf8').replace(/\r\n/g, '\n')).digest('hex').slice(0, 12);
  const render = (svg, size) => sharp(Buffer.from(svg), { density: 144 })
    .resize(size, size).flatten({ background: '#020c18' }).removeAlpha().png({ compressionLevel: 9 });
  const output = [];
  for (const size of SIZES) {
    const name = `app-icon-${size}.png`;
    // Small favicons retain the exact source silhouette instead of unreadable texture.
    const variant = size <= 48 ? embedded.replace('filter="url(#icon-light)"', 'filter="url(#icon-silhouette)"') : embedded;
    await render(variant, size).toFile(path.join(DIR, name));
    output.push(name);
  }
  // The same artwork scales into the central 80% diameter safe circle.
  const maskable = embedded.replace('<g id="shark"',
    '<g transform="translate(512 512) scale(.80) translate(-512 -512)"><g id="shark"')
    .replace('</svg>', '</g></svg>');
  for (const size of [192, 512]) {
    const name = `app-icon-maskable-${size}.png`;
    await render(maskable, size).toFile(path.join(DIR, name));
    output.push(name);
  }
  const frames = await Promise.all([16, 32, 48, 64, 128, 256].map(size =>
    fs.promises.readFile(path.join(DIR, `app-icon-${size}.png`)).then(data => ({ size, data }))));
  const header = Buffer.alloc(6 + 16 * frames.length);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(frames.length, 4);
  let offset = header.length;
  frames.forEach(({ size, data }, i) => {
    const p = 6 + i * 16;
    header[p] = header[p + 1] = size === 256 ? 0 : size;
    header.writeUInt16LE(1, p + 4);
    header.writeUInt16LE(32, p + 6);
    header.writeUInt32LE(data.length, p + 8);
    header.writeUInt32LE(offset, p + 12);
    offset += data.length;
  });
  fs.writeFileSync(path.join(DIR, 'app-icon.ico'), Buffer.concat([header, ...frames.map(x => x.data)]));
  output.push('app-icon.ico');
  const metadata = {
    master: 'official_app_icon_master.svg', source: '../nemesis-shark-atmosphere-v2.webp',
    source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
    fingerprint, sizes: SIZES, maskable_scale: .80,
    files: Object.fromEntries(output.map(name => {
      const bytes = fs.readFileSync(path.join(DIR, name));
      return [name, { bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') }];
    }))
  };
  fs.writeFileSync(path.join(DIR, 'icons.json'), JSON.stringify(metadata, null, 2) + '\n');
  return metadata;
}

if (require.main === module) {
  // --sharp-module allows an already installed build dependency; never auto-installs.
  const index = process.argv.indexOf('--sharp-module');
  const sharp = require(index < 0 ? 'sharp' : process.argv[index + 1]);
  build(sharp).then(result => console.log(JSON.stringify(result, null, 2))).catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
module.exports = { build, SIZES };
