from pathlib import Path
from random import Random
from xml.etree import ElementTree

from PIL import Image, ImageChops, ImageDraw


def metal_finish(coat):
    if coat in ("screen-white", "screen-pearl"):
        return 141, 31
    if coat in ("silver", "platinum", "bright-engraving", "light-keyline", "white", "snow"):
        return 58, 211
    if coat in ("carbon", "charcoal", "lacquer-black", "graphite", "dark", "graphite-detail"):
        return 128, 43
    if coat == "smoked-silver":
        return 65, 219
    return 104, 143


def brushed_roughness(roughness, metallic):
    width, height = roughness.size
    grain = Image.new("L", roughness.size, 128)
    stylus = ImageDraw.Draw(grain)
    rng = Random(890)
    for diagonal in range(width + height):
        x = diagonal
        while x > diagonal - height:
            stroke = rng.randint(25, 80)
            y = diagonal - x
            stylus.line((x, y, x - stroke, y + stroke), fill=rng.randint(124, 132))
            x -= stroke
    brushed = ImageChops.add(roughness, grain, offset=-128)
    return Image.composite(brushed, roughness, metallic)


def silk_layers(source):
    vector = ElementTree.parse(Path(__file__).with_name("strix-prints") / source)
    _, _, width, height = map(int, vector.getroot().attrib["viewBox"].split())
    for separation in vector.findall(".//{*}g"):
        pigment = separation.get("fill")
        if pigment is None:
            continue
        stencil = Image.new("L", (width, height))
        draw = ImageDraw.Draw(stencil)
        for path in separation.findall("{*}path"):
            rings = [
                [tuple(map(int, vertex.split(","))) for vertex in ring.lstrip("M").split()]
                for ring in path.attrib["d"].strip("Z").split("ZM")
            ]
            if len(rings) == 1:
                draw.polygon(rings[0], fill=255)
                continue
            xs, ys = zip(*rings[0])
            left, top = min(xs), min(ys)
            coverage = Image.new("L", (max(xs) - left + 1, max(ys) - top + 1))
            contour = ImageDraw.Draw(coverage)
            for index, ring in enumerate(rings):
                contour.polygon([(x-left, y-top) for x, y in ring], fill=0 if index else 255)
            stencil.paste(255, (left, top, left+coverage.width, top+coverage.height), coverage)
        yield separation.attrib["id"], pigment, stencil


def front_silkscreen(image):
    for _, pigment, stencil in silk_layers("pcb-front-legends.svg"):
        image.paste(pigment, mask=stencil.resize(image.size, Image.Resampling.LANCZOS))


def engrave_heatsinks(artwork):
    aluminum = Image.new("RGB", (2430, 1040), "#e0e2e3")
    roughness = Image.new("L", aluminum.size, 119)
    metallic = Image.new("L", aluminum.size, 187)
    for coat, pigment, stencil in silk_layers("fubuki-ssd-armor.svg"):
        aluminum.paste(pigment, mask=stencil)
        rough, metal = metal_finish(coat)
        roughness.paste(rough, mask=stencil)
        metallic.paste(metal, mask=stencil)
    aluminum.resize((1944, 832), Image.Resampling.LANCZOS).save(artwork / "coolers.png", optimize=True)
    size = (972, 416)
    metal = metallic.resize(size, Image.Resampling.BOX)
    brush = brushed_roughness(roughness.resize(size, Image.Resampling.BOX), metal)
    Image.merge("RGB", (Image.new("L", size, 255), brush, metal)).save(
        artwork / "armor-finish.png", optimize=True
    )
