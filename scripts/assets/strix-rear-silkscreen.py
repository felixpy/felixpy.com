from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageDraw


def reverse_print(board):
    source = Path(__file__).with_name("strix-prints") / "rear-silkscreen.svg"
    drawing = ElementTree.parse(source).getroot()
    _, _, width, height = map(int, drawing.attrib["viewBox"].split())
    mask = Image.new("L", (width, height))
    pen = ImageDraw.Draw(mask)
    for polygon in drawing.findall("{http://www.w3.org/2000/svg}polygon"):
        points = [tuple(map(int, pair.split(","))) for pair in polygon.get("points").split()]
        pen.polygon(points, fill=255 if polygon.get("fill") == "white" else 0)
    board.paste("#dadbdb", (0, 0), mask.resize(board.size, Image.Resampling.LANCZOS))
    draw = ImageDraw.Draw(board)
    sx, sy = board.width / 646, board.height / 805

    def at(x, y):
        return (round((x - 138) * sx), round((y - 75) * sy))

    for x, y, radius in [(644, 172, 17), (174, 684, 14), (679, 789, 26), (698, 758, 12)]:
        rays = [(0,-1),(.09,-.14),(.40,-.45),(.16,-.06),(1,0),(.15,.08),
                (.39,.4),(.07,.16),(0,1),(-.08,.15),(-.41,.43),(-.16,.07),
                (-1,0),(-.16,-.06),(-.37,-.40),(-.07,-.17)]
        draw.polygon([at(x+a*radius, y+b*radius) for a,b in rays], fill="#d9dcdb")

    audio_path = [(784,478),(775,468),(775,447),(769,439),(760,439),(753,446),
                  (753,469),(747,471),(739,466),(739,449),(732,449),(732,483),
                  (740,495),(765,495),(776,507),(776,732),(766,747),(745,747),
                  (737,755),(739,806),(729,806),(723,812),(723,826),(697,853),
                  (648,855),(640,863),(640,879)]
    line = [at(x,y) for x,y in audio_path]
    draw.line(line, fill="#b9a470", width=max(1, round(.64*sx)), joint="curve")
