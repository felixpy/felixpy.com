import sys
from pathlib import Path

import zxingcpp
from PIL import Image, ImageDraw, ImageFont, ImageOps


def identification(path):
    background = (98, 97, 102)
    ink = (191, 191, 193)
    label = Image.new("RGB", (1536, 180), background)
    pen = ImageDraw.Draw(label)
    fonts = ["arialbd.ttf", "DejaVuSans-Bold.ttf"]
    for family in fonts:
        try:
            font = ImageFont.truetype(family, 160)
            break
        except OSError:
            continue
    else:
        raise FileNotFoundError("A bold sans serif font is required for the label")

    def letter(text, box):
        mask = Image.new("L", (max(300, len(text) * 170), 210))
        ImageDraw.Draw(mask).text((0, 0), text, fill=255, font=font, stroke_width=0)
        mask = mask.crop(mask.getbbox()).resize(box[2:], Image.Resampling.LANCZOS)
        label.paste(ink, box[:2], mask)

    for left in (25, 146):
        pen.arc((left, 19, left + 136, 155), 90, 270, fill=ink, width=19)
    pen.rectangle((148, 78, 208, 96), fill=ink)
    letter("UK", (214, 20, 125, 62))
    letter("CA", (214, 92, 125, 63))
    letter("KC", (354, 28, 105, 115))
    pen.line(
        [
            (476, 86),
            (518, 21),
            (526, 21),
            (568, 86),
            (567, 95),
            (475, 95),
            (472, 90),
            (476, 86),
        ],
        fill=ink,
        width=7,
        joint="curve",
    )
    pen.line([(495, 67), (509, 79), (543, 43)], fill=ink, width=6)
    pen.rounded_rectangle((486, 109, 558, 143), 5, outline=ink, width=3)
    letter("VCCI", (494, 116, 57, 19))
    letter("IS 13252 (Part 1)", (584, 20, 139, 21))
    letter("IEC 60950-1", (592, 46, 124, 20))
    letter("R-41168050", (584, 114, 137, 17))
    letter("www.bis.gov.in", (580, 138, 145, 16))
    code = zxingcpp.create_barcode(
        "FELIX-STUDIO-T7-01", zxingcpp.BarcodeFormat.DataMatrix
    )
    symbol = Image.frombuffer(
        "L",
        (code.to_image().shape[1], code.to_image().shape[0]),
        code.to_image(),
        "raw",
        "L",
        0,
        1,
    )
    symbol = ImageOps.invert(symbol).resize((128, 128), Image.Resampling.NEAREST)
    label.paste(ink, (747, 26), symbol)
    letter("MODEL  MU-PC2T0T     R-R-SEC-MU-PC2T0", (897, 26, 543, 29))
    letter("S/N  STUDIO-T7-01", (897, 68, 254, 25))
    letter("RATED  DC +5V", (897, 104, 205, 24))
    pen.rectangle((1108, 108, 1135, 111), fill=ink)
    for x in (1108, 1118, 1128):
        pen.rectangle((x, 116, x + 6, 119), fill=ink)
    letter("1.5A", (1140, 104, 64, 24))
    letter("SAMSUNG ELECTRONICS CO., LTD.", (897, 142, 417, 17))
    letter("2 TB", (1390, 74, 109, 47))
    label.save(path)


if __name__ == "__main__":
    identification(Path(sys.argv[1]))
