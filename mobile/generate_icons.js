const sharp = require('sharp');
const path = require('path');
const fs = require('fs');

const iconSrc = path.join(__dirname, 'icon', 'icon.jpeg');
const resDir = path.join(__dirname, 'android', 'app', 'src', 'main', 'res');

// Android mipmap sizes
const sizes = [
    { dir: 'mipmap-mdpi', size: 48 },
    { dir: 'mipmap-hdpi', size: 72 },
    { dir: 'mipmap-xhdpi', size: 96 },
    { dir: 'mipmap-xxhdpi', size: 144 },
    { dir: 'mipmap-xxxhdpi', size: 192 },
];

// Foreground sizes (for adaptive icons, slightly larger)
const fgSizes = [
    { dir: 'mipmap-mdpi', size: 108 },
    { dir: 'mipmap-hdpi', size: 162 },
    { dir: 'mipmap-xhdpi', size: 216 },
    { dir: 'mipmap-xxhdpi', size: 324 },
    { dir: 'mipmap-xxxhdpi', size: 432 },
];

async function generate() {
    console.log('Generating icons from:', iconSrc);

    for (const { dir, size } of sizes) {
        const outDir = path.join(resDir, dir);
        fs.mkdirSync(outDir, { recursive: true });

        // ic_launcher.png
        await sharp(iconSrc)
            .resize(size, size, { fit: 'cover' })
            .png()
            .toFile(path.join(outDir, 'ic_launcher.png'));
        console.log(`  ${dir}/ic_launcher.png (${size}x${size})`);

        // ic_launcher_round.png (same image for now)
        await sharp(iconSrc)
            .resize(size, size, { fit: 'cover' })
            .png()
            .toFile(path.join(outDir, 'ic_launcher_round.png'));
        console.log(`  ${dir}/ic_launcher_round.png (${size}x${size})`);
    }

    // Foreground images for adaptive icons
    for (const { dir, size } of fgSizes) {
        const outDir = path.join(resDir, dir);
        await sharp(iconSrc)
            .resize(size, size, { fit: 'cover' })
            .png()
            .toFile(path.join(outDir, 'ic_launcher_foreground.png'));
        console.log(`  ${dir}/ic_launcher_foreground.png (${size}x${size})`);
    }

    console.log('\nDone! All icons generated.');
}

generate().catch(e => { console.error(e); process.exit(1); });
