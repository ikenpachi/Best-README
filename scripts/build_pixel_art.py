#!/usr/bin/env python3
"""Convert local PNGs to cyber SVG rectangles and replace only the left artwork.
Requires ImageMagick (`magick`); no PNG/image elements are retained in the SVG.
"""
from pathlib import Path
import random
import math
import struct
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://www.w3.org/2000/svg'}
WIDTH, HEIGHT = 180, 224
CELL = 372 / WIDTH
DURATION = 18


def pixels(name):
    path = ROOT / 'assets' / (name + '.png')
    w, h = struct.unpack('>II', path.read_bytes()[16:24])
    scale = min(WIDTH / w, HEIGHT / h)
    sw, sh = round(w * scale), round(h * scale)
    raw = subprocess.check_output([
        'magick', str(path), '-filter', 'Box', '-resize', f'{sw}x{sh}!',
        '-depth', '8', 'rgba:-'])
    assert len(raw) == sw * sh * 4
    ox, oy = (WIDTH-sw)/2, (HEIGHT-sh)/2
    points = []
    rng = random.Random(name)
    for y in range(sh):
        for x in range(sw):
            r, g, b, a = raw[(y*sw+x)*4:(y*sw+x+1)*4]
            lum = (0.2126*r + 0.7152*g + 0.0722*b)/255
            # Luminance controls pigment density, retaining the source silhouette.
            if a < 48 or lum < .025 or rng.random() > lum**.72 * a/255:
                continue
            mix = .20 + .60*x/sw
            rgb = [round(v*(.55+.45*lum**.4)) for v in
                   (57*(1-mix), 255-26*mix, 20+235*mix)]
            color = '#'+''.join(f'{v:02x}' for v in rgb)
            points.append((50+(ox+x)*CELL, 98+(oy+y)*CELL, color, a/255))
    # Keep a bounded particle pool; spatial ordering gives coherent local motion.
    if len(points) > 5200:
        points = rng.sample(points, 5200)
    return sorted(points, key=lambda p: (p[1], p[0]))


def portrait(name):
    """Batch tonal samples into paths instead of thousands of animated nodes."""
    path = ROOT / 'assets' / (name + '.png')
    w, h = struct.unpack('>II', path.read_bytes()[16:24])
    scale = min(144/w, 180/h)
    sw, sh = round(w*scale), round(h*scale)
    raw = subprocess.check_output(['magick', str(path), '-filter', 'Box',
        '-resize', f'{sw}x{sh}!', '-depth', '8', 'rgba:-'])
    cell = 372/144
    buckets = [[[] for _ in range(24)] for _ in range(96)]
    pigment_rng = random.Random(f'portrait-pigment-{name}')
    for y in range(sh):
        for x in range(sw):
            r,g,b,a = raw[(y*sw+x)*4:(y*sw+x+1)*4]
            lum = (.2126*r+.7152*g+.0722*b)/255 * a/255
            if lum < .035:
                continue
            level = min(23, round(lum**.75*23))
            px = 50+((144-sw)/2+x)*cell
            py = 98+((180-sh)/2+y)*cell
            # Every source sample becomes pigment. Preserve all tonal samples so
            # the assembled silhouette stays readable instead of deleting it.
            size = cell*pigment_rng.uniform(.62, .88)
            px += (cell-size)/2 + pigment_rng.uniform(-.12, .12)
            py += (cell-size)/2 + pigment_rng.uniform(-.12, .12)
            fragment = (x*37+y*61) % 96
            buckets[fragment][level].append(f'M{px:.2f} {py:.2f}h{size:.2f}v{size:.2f}h-{size:.2f}z')
    return [[f'<path fill="#{round(35*(i/23)):02x}{round(245*(i/23)):02x}{round(175*(i/23)):02x}" d="{"".join(paths)}"/>'
             for i,paths in enumerate(fragment) if paths] for fragment in buckets]


def artwork():
    states = [pixels(name) for name in ('me', 'otherme', 'mylove')]
    count = 768
    output = ['<!-- Cyber pigment: persistent particles morph between three source silhouettes. -->',
              '<defs><clipPath id="cyberVisualClip"><rect x="42" y="90" width="388" height="480" rx="6"/></clipPath></defs>',
              '<g id="cyber-image-cycle" clip-path="url(#cyberVisualClip)" shape-rendering="crispEdges">']
    output += ['<g opacity="0">',
               '<animate attributeName="opacity" values="0;0;1;0;0;1;0;0;1;0" keyTimes="0;.2;.254167;.333333;.533333;.5875;.666667;.866667;.920833;1" dur="18s" begin="3.2s" repeatCount="indefinite"/>']
    particles = [[] for _ in range(60)]
    for i in range(count):
        rng = random.Random(i)
        samples = []
        for state in states:
            # Distribute missing particles throughout the image, with zero opacity.
            index = min(len(state)-1, int(i*len(state)/count))
            point = state[index]
            visible = int((i+1)*len(state)/count) > int(i*len(state)/count)
            samples.append((*point[:3], point[3] if visible else 0))
        clouds = []
        for _ in range(3):
            angle, radius = rng.uniform(0, 2*math.pi), math.sqrt(rng.random())
            clouds.append((236+105*radius*math.cos(angle),
                           330+155*radius*math.sin(angle), '#22eaca', .65))
        frames = [samples[0],samples[0],clouds[0],samples[1],samples[1],
                  clouds[1],samples[2],samples[2],clouds[2],samples[0]]
        jitter = rng.uniform(-.25,.25)
        seconds = [0,4.8+jitter,6.1+jitter,8,12.8+jitter,14.1+jitter,
                   16,20.8+jitter,22.1+jitter,24]
        times = ';'.join(f'{t/24:.6f}' for t in seconds)
        positions = ';'.join(f'{p[0]:.2f} {p[1]:.2f}' for p in frames)
        opacity = ';'.join(f'{p[3]:.3f}' for p in frames)
        common = f'keyTimes="{times}" dur="18s" begin="3.2s" repeatCount="indefinite"'
        particles[i%60].append(
            f'<rect width="1.85" height="1.55" transform="translate({samples[0][0]:.2f} {samples[0][1]:.2f})" fill="#22eaca" opacity="{samples[0][3]:.3f}">'
            f'<animateTransform attributeName="transform" type="translate" values="{positions}" {common}/>'
            f'<animate attributeName="opacity" values="{opacity}" {common}/></rect>')
    for index, rects in enumerate(particles):
        output += [f'<g id="pigment-{index}" opacity="0">',
                   f'<animate attributeName="opacity" values="0;1" dur="0.9s" begin="{.2+index/30:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/>',
                   *rects, '</g>']
    output.append('</g>')
    # Interleaved pigment groups move the actual image samples during departure
    # and arrival. Irregular pigment spacing avoids continuous grid lines.
    for phase,name in enumerate(('me','otherme','mylove')):
        visible = ((0,1,12),(4,5),(8,9))[phase]
        output.append(f'<g id="portrait-{name}">')
        for index, paths in enumerate(portrait(name)):
            rng = random.Random(phase*96+index)
            delay = rng.uniform(-.20,.20)
            seconds = [0,3.1+delay,4.55+delay,4.7+delay,6,
                       9.1+delay,10.55+delay,10.7+delay,12,
                       15.1+delay,16.55+delay,16.7+delay,18]
            times = ';'.join(f'{t/DURATION:.6f}' for t in seconds)
            values = ['1' if frame in visible else '0' for frame in range(13)]
            dx,dy = rng.uniform(-12,12),rng.uniform(-20,20)
            scale = rng.uniform(.60,.72)
            positions = ';'.join('0 0' if frame in visible else f'{236*(1-scale)+dx:.2f} {330*(1-scale)+dy:.2f}'
                                 for frame in range(13))
            scales = ';'.join('1' if frame in visible else f'{scale:.4f}'
                              for frame in range(13))
            common = f'keyTimes="{times}" dur="18s" begin="3.2s" repeatCount="indefinite"'
            output += [f'<g opacity="{1 if phase == 0 else 0}">',
                       f'<animate attributeName="opacity" values="{";".join(values)}" {common}/>',
                       f'<animateTransform attributeName="transform" type="translate" values="{positions}" {common}/>',
                       f'<animateTransform attributeName="transform" type="scale" additive="sum" values="{scales}" {common}/>',
                       *paths, '</g>']
        output.append('</g>')
    output.append('</g>')
    return '\n'.join(output)+'\n'


def main():
    replacement = artwork()
    for filename in ['dark.svg', 'light.svg']:
        path = ROOT / filename
        source = path.read_text()
        # Supports replacing this generator's output, the previous PNG tile cycle,
        # or the original portrait. Everything outside the artwork is kept verbatim.
        candidates = [source.find(marker) for marker in [
            '<!-- Cyber pigment:', '<!-- Self-contained PNG tile cycle:',
            '<g transform="translate(50,86)']]
        start = min(i for i in candidates if i >= 0)
        end = source.index('<path d="M 50 84', start)
        themed = replacement
        result = source[:start]+themed+source[end:]
        root = ET.fromstring(result)
        assert not root.findall('.//s:image', NS)
        path.write_text(result)
        print(f'{filename}: replaced left art with {replacement.count("<rect ")} native rectangles')


if __name__ == '__main__':
    main()
