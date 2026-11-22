import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def register_armour(source, photo):
    target = cv2.resize(source, (2440, 2440), interpolation=cv2.INTER_CUBIC)
    scale = np.array([photo.shape[1] / 537, photo.shape[0] / 725], np.float32)
    panels = [
        (
            [(169,80),(177,38),(183,58),(197,57),(222,35),(240,33),(238,74),(226,84),(213,133),(209,143),(187,140),(181,130),(174,95),(183,85),(211,83)],
            [(232,171),(237,133),(250,150),(264,148),(287,126),(312,124),(311,168),(302,181),(291,223),(286,237),(252,236),(245,222),(237,188),(249,181),(277,179)],
        ),
        (
            [(127,198),(148,185),(175,183),(201,202),(219,202),(252,177),(286,180),(303,202),(315,229),(318,251),(294,273),(269,288),(249,316),(232,322),(182,325),(162,310),(150,289),(126,266),(117,244),(184,236),(204,230),(222,232),(226,239),(211,276),(198,277)],
            [(184,305),(201,288),(231,277),(267,303),(283,305),(332,276),(359,289),(379,313),(390,335),(395,352),(364,380),(341,393),(318,420),(302,428),(248,428),(230,416),(217,395),(189,373),(176,349),(262,345),(280,340),(301,341),(308,348),(296,386),(276,387)],
        ),
    ]
    for destination, origin in panels:
        dst = (np.float32(destination) / 3 + [225, 105]).astype('f') * 4
        src = np.float32(origin) * scale
        x, y, w, h = cv2.boundingRect(dst)
        dst -= [x, y]
        warp = np.zeros((h, w, 2), dtype=np.float32)
        subdivision = cv2.Subdiv2D((0, 0, w, h))
        subdivision.insert([tuple(map(float, pt)) for pt in dst])
        for face in subdivision.getTriangleList().reshape(-1, 3, 2):
            triangle = np.linalg.norm(dst[None, :, :] - face[:, None, :], axis=2).argmin(axis=1)
            if not np.allclose(face, dst[triangle]):
                continue
            transform = cv2.getAffineTransform(face, src[triangle])
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillConvexPoly(mask, np.round(face).astype('i'), 1)
            iy, ix = np.where(mask)
            warp[iy, ix] = (np.column_stack([ix, iy]) @ transform[:, :2].T + transform[:, 2])
        sampled = cv2.remap(photo, warp, None, cv2.INTER_AREA)
        inside = (warp[..., 0] > 0).astype('uint8')
        distance = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        alpha = (np.clip(distance / 10, 0, 1) * 0.88)[..., None]
        paint = target[y:y+h, x:x+w].astype('f')
        detail = sampled.astype('f') - cv2.GaussianBlur(sampled.astype('f'), (0, 0), 4)
        local = paint - cv2.GaussianBlur(paint, (0, 0), 4)
        target[y:y+h, x:x+w] = np.clip(paint + alpha * (detail - local), 0, 255).astype('uint8')
    return target


def make_atlas(folder, slug):
    source = Image.open(folder / f'{slug}-surface.png').convert('RGB')
    if slug == 'mk85':
        official = Image.open(folder / 'mk85-manufacturer-a.jpg').convert('RGB')
        for name, box in {
            'faceplate': (226, 118, 330, 244),
            'arc-window': (248, 329, 314, 394),
        }.items():
            crop = official.crop(tuple(round(n * (official.width / 537 if i % 2 == 0 else official.height / 725)) for i,n in enumerate(box)))
            crop.save(folder / f'mk85-{name}-finish.jpg', quality=96, subsampling=0)
        source = Image.fromarray(register_armour(np.asarray(source), np.asarray(official)))
    fallback = Image.open(folder / f'{slug}-paint.jpg').convert('RGB')
    uv = np.load(folder / f'{slug}-casting.npz')['uv']
    pixels = uv * [source.width, -source.height] + [0, source.height]
    x0, y0 = np.maximum(np.floor(pixels.min(axis=0)).astype('i')-5, 0)
    x1, y1 = np.minimum(np.ceil(pixels.max(axis=0)).astype('i')+5, source.size)
    patch = source.crop((x0, y0, x1, y1))
    atlas = Image.new('RGB', (fallback.width + 8 + patch.width, max(fallback.height,patch.height)))
    atlas.paste(fallback, (0, atlas.height-fallback.height))
    atlas.paste(patch, (fallback.width+8, atlas.height-patch.height))
    atlas.save(folder / f'{slug}-registered-paint.jpg', quality=95, subsampling=0, optimize=True)
    print(json.dumps({
        'atlas': atlas.size, 'fallback': fallback.size, 'source': source.size,
        'offset': [int(fallback.width + 8 - x0), int(y1 - source.height)],
    }))


if __name__ == '__main__':
    make_atlas(Path(sys.argv[1]), sys.argv[2])
