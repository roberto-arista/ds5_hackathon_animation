from typing import Sequence

from drawBot import _drawBotDrawingTool as db
from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import Mutator, buildMutator

from roundedRect import roundedRect

# Constants
WHITE = 1, 1, 1
BLACK = 0, 0, 0
DEBUG = False

# Type aliases
Color = tuple[float, ...]
IntMatrix = list[list[int]]
IntNullableMatrix = list[list[int | None]]
FloatMatrix = list[list[float]]
PT = tuple[float, float]
Box = tuple[float, float, float, float]


# ------------
# Geometry
# ------------
def lerp(a: float, b: float, factor: float) -> float:
    return a + (b - a) * factor


def multiLerp(a: Sequence[float], b: Sequence[float], factor: float) -> list[float]:
    result = []
    for first, second in zip(a, b):
        result.append(lerp(first, second, factor))
    return result


def parametricBlend(t: float) -> float:
    sqt = t * t
    return sqt / (2.0 * (sqt - t) + 1.0)


# ---------------------
# Colors and position
# --------------------
class ColorManager:

    """
    Here we deal with colors
    Possibly overkilling, but I need some structure

    """

    def __init__(self):
        rawColors = [
            dict(r=1, g=0.8, b=0, x=0, y=1),
            dict(r=1, g=0.2, b=0, x=0, y=0),
            dict(r=1, g=0.2, b=0.75, x=1, y=1),
            dict(r=0.1, g=0.1, b=0.8, x=1, y=0),
        ]

        self.mutators: dict[str, Mutator] = {}
        for key in "rgb":
            items = []
            for eachRawColor in rawColors:
                items.append(
                    (
                        Location(x=eachRawColor["x"], y=eachRawColor["y"]),
                        eachRawColor[key],
                    )
                )
            _, self.mutators[key] = buildMutator(items)

    def __call__(self, x: float, y: float, opacity: float = 1) -> Color:
        clr = []
        for channel in "rgb":
            clr.append(self.mutators[channel].makeInstance(Location(x=x, y=y)))
        clr.append(opacity)
        return tuple(clr)


def position(xRatio: float, yRatio: float) -> tuple[float, float]:
    lft, btm = multiLerp([0, 0], [db.width(), db.height()], 0.22)
    rgt, top = multiLerp([0, 0], [db.width(), db.height()], 0.78)
    return lerp(lft, rgt, xRatio), lerp(btm, top, yRatio)


# -----------
# Sizes
# -----------
def diameter() -> float:
    return db.width() * 0.25


def radius() -> float:
    return diameter() / 2


# -----------
# Frames
# -----------
colorManager = ColorManager()


def initFrame():
    db.newPage(1200, 1200)
    db.frameDuration(1 / 24)
    assert db.width() == db.height()
    db.fill(*WHITE)
    db.rect(0, 0, db.width(), db.height())


def dots(opacity: float = 1, skip: set[int] = set()):
    for j, yRatio in enumerate([0, 0.5, 1]):
        for i, xRatio in enumerate([0, 0.5, 1]):
            overallIndex = j * 3 + i
            if overallIndex not in skip:
                db.fill(*colorManager(x=xRatio, y=yRatio, opacity=opacity))
                x, y = position(xRatio, yRatio)
                db.oval(x - radius(), y - radius(), diameter(), diameter())


def spring(box: Box, completion: float):
    x, y, w, h = box
    if completion < 0.5:
        ratio = parametricBlend(completion * 2)
        db.rect(x, y, w * ratio, h)
    else:
        ratio = parametricBlend((completion - 0.5) * 2)
        db.rect(x + w * ratio, y, w * (1 - ratio), h)


def blob(startPt, endPt, completion):
    if completion <= 0.5:
        ratio = parametricBlend(completion * 2)
        roundedRect(
            startPt[0] - radius(),
            startPt[1] - radius(),
            diameter(),
            diameter() + (endPt[1] - startPt[1]) * ratio,
            radius(),
        )
    else:
        ratio = parametricBlend((completion - 0.5) * 2)
        roundedRect(
            startPt[0] - radius(),
            startPt[1] - radius() + (endPt[1] - startPt[1]) * ratio,
            diameter(),
            diameter() + (endPt[1] - startPt[1]) * (1 - ratio),
            radius(),
        )


# ----------
# Timeline
# ----------
if __name__ == "__main__":
    fps = 24
    frames = fps * 12
    blobOpacity = 0.6

    rulesCycles = [
        # seconds off, seconds on, switch (False by default)
        [[4, 2, False], [3, 2, False], [4, 3, False]],
        [[2, 2, False], [4, 2, False], [1, 3, False]],
        [[3, 1, False], [3, 3, False], [4, 2, False]],
    ]

    with db.drawing():
        initFrame()
        positionToParameters = {
            "lft": {
                "cycle": 24 * 2,
                "x": 0,
                "y": 0.75,
                "nextY": 0.25,
                "range": (position(0, 0.5), position(0, 1)),
                "nextRange": (position(0, 0), position(0, 0.5)),
            },
            "mid": {
                "cycle": 24 * 3,
                "x": 0.5,
                "y": 0.75,
                "nextY": 0.25,
                "range": (position(0.5, 0.5), position(0.5, 1)),
                "nextRange": (position(0.5, 0), position(0.5, 0.5)),
            },
            "rgt": {
                "cycle": 24,
                "x": 1,
                "y": 0.75,
                "nextY": 0.25,
                "range": (position(1, 0.5), position(1, 1)),
                "nextRange": (position(1, 0), position(1, 0.5)),
            },
        }

    with db.drawing():
        for eachFrame in range(frames):
            initFrame()

            # blobs
            for pos, param in positionToParameters.items():
                db.fill(*colorManager(x=param["x"], y=param["y"], opacity=blobOpacity))
                lftStartPt, lftEndPt = param["range"]
                blob(
                    lftStartPt,
                    lftEndPt,
                    (eachFrame % param["cycle"]) / param["cycle"],
                )
                if eachFrame % param["cycle"] == 0:
                    param["y"], param["nextY"] = (
                        param["nextY"],
                        param["y"],
                    )
                    param["range"], param["nextRange"] = (
                        param["nextRange"],
                        param["range"],
                    )

            # dots
            dots(opacity=1)

            # rules
            ruleSide = 80

            for j, yRatio in enumerate([0, 0.5, 1]):
                for i, xRatio in enumerate([0, 0.5, 1]):
                    cycleOff, cycleOn, switch = rulesCycles[j][i]
                    cycleOff *= fps
                    cycleOn *= fps

                    if switch:
                        db.fill(*WHITE)
                        x, y = position(xRatio, yRatio)
                        spring(
                            (x - ruleSide / 2, y - ruleSide / 2, ruleSide, ruleSide),
                            (eachFrame % cycleOn) / cycleOn,
                        )

                    if switch and ((eachFrame % cycleOn) / (cycleOn - 1)) == 1:
                        switch = not switch
                        rulesCycles[j][i][2] = switch
                    if not switch and ((eachFrame % cycleOff) / (cycleOff - 1)) == 1:
                        switch = not switch
                        rulesCycles[j][i][2] = switch

        db.saveImage("animation.mp4")
