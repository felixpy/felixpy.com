from pathlib import Path
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

original, output = map(Path, sys.argv[1:3])
family = sys.argv[3] if len(sys.argv) > 3 else "Studio Han"
files = [Path(sys.argv[4])] if len(sys.argv) > 4 else [p for p in Path("src").rglob("*") if p.suffix in {".ts", ".tsx", ".css"}]
characters = {ord(c) for p in files for c in p.read_text(encoding="utf-8-sig") if ord(c) > 127}
characters.update(range(32, 127))

options = subset.Options()
options.name_IDs = ["*"]
font = TTFont(original)
subsetter = subset.Subsetter(options=options)
subsetter.populate(unicodes=characters)
subsetter.subset(font)
postscript_name = family.replace(" ", "")
names = {1: family, 2: "Regular", 3: f"FelixStudio-{postscript_name}", 4: family,
         6: postscript_name, 16: family, 17: "Regular"}
for record in font["name"].names[:]:
    value = names.get(record.nameID)
    if value:
        font["name"].setName(value, record.nameID, record.platformID, record.platEncID, record.langID)
font.flavor = "woff2"
font.save(output)
