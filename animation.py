from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

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

    def __init__(self, rawColors: list[dict[str, float]]):
        self.rawColors = rawColors
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


# -----------
# Frames
# -----------
CANVAS_SIZE = 1200
FPS = 24
FRAMES = FPS * 12
BASE_OPACITY = 0.6


def coordinates(xRatio: float, yRatio: float) -> tuple[float, float]:
    lft, btm = multiLerp([0, 0], [CANVAS_SIZE, CANVAS_SIZE], 0.22)
    rgt, top = multiLerp([0, 0], [CANVAS_SIZE, CANVAS_SIZE], 0.78)
    return lerp(lft, rgt, xRatio), lerp(btm, top, yRatio)


def positionToLocationFactory():
    return {
        "lft": {
            "x": 0,
            "y": 0.75,
            "nextY": 0.25,
            "range": (coordinates(0, 0.5), coordinates(0, 1)),
            "nextRange": (coordinates(0, 0), coordinates(0, 0.5)),
        },
        "mid": {
            "x": 0.5,
            "y": 0.75,
            "nextY": 0.25,
            "range": (coordinates(0.5, 0.5), coordinates(0.5, 1)),
            "nextRange": (coordinates(0.5, 0), coordinates(0.5, 0.5)),
        },
        "rgt": {
            "x": 1,
            "y": 0.75,
            "nextY": 0.25,
            "range": (coordinates(1, 0.5), coordinates(1, 1)),
            "nextRange": (coordinates(1, 0), coordinates(1, 0.5)),
        },
    }


@dataclass
class AnimationManager:
    colorManager: ColorManager
    rulesCycles: list[list[list[float | bool]]]
    locationToCycle: dict[str, float]
    positionToLocation: dict[str, dict[str, Any]] = field(default_factory=positionToLocationFactory)

    @property
    def diameter(self) -> float:
        return db.width() * 0.25

    @property
    def radius(self) -> float:
        return self.diameter / 2

    def initFrame(self):
        db.newPage(CANVAS_SIZE, CANVAS_SIZE)
        db.frameDuration(1 / FPS)
        assert db.width() == db.height()
        db.fill(*WHITE)
        db.rect(0, 0, db.width(), db.height())

    def dots(self, opacity: float = 1, skip: set[int] = set()):
        for j, yRatio in enumerate([0, 0.5, 1]):
            for i, xRatio in enumerate([0, 0.5, 1]):
                overallIndex = j * 3 + i
                if overallIndex not in skip:
                    db.fill(*self.colorManager(x=xRatio, y=yRatio, opacity=opacity))
                    x, y = coordinates(xRatio, yRatio)
                    db.oval(x - self.radius, y - self.radius, self.diameter, self.diameter)

    def spring(self, box: Box, completion: float):
        x, y, w, h = box
        if completion < 0.5:
            ratio = parametricBlend(completion * 2)
            db.rect(x, y, w * ratio, h)
        else:
            ratio = parametricBlend((completion - 0.5) * 2)
            db.rect(x + w * ratio, y, w * (1 - ratio), h)

    def blob(self, startPt, endPt, completion):
        if completion <= 0.5:
            ratio = parametricBlend(completion * 2)
            roundedRect(
                startPt[0] - self.radius,
                startPt[1] - self.radius,
                self.diameter,
                self.diameter + (endPt[1] - startPt[1]) * ratio,
                self.radius,
            )
        else:
            ratio = parametricBlend((completion - 0.5) * 2)
            roundedRect(
                startPt[0] - self.radius,
                startPt[1] - self.radius + (endPt[1] - startPt[1]) * ratio,
                self.diameter,
                self.diameter + (endPt[1] - startPt[1]) * (1 - ratio),
                self.radius,
            )

    def draw(self, path: Path):
        with db.drawing():  # type: ignore
            for eachFrame in range(FRAMES):
                self.initFrame()

                # blobs
                for pos, cycle in self.locationToCycle.items():
                    locations = self.positionToLocation[pos]
                    db.fill(*self.colorManager(x=locations["x"], y=locations["y"], opacity=BASE_OPACITY))
                    lftStartPt, lftEndPt = locations["range"]
                    self.blob(
                        lftStartPt,
                        lftEndPt,
                        (eachFrame % cycle) / cycle,
                    )
                    if eachFrame % cycle == 0:
                        locations["y"], locations["nextY"] = (
                            locations["nextY"],
                            locations["y"],
                        )
                        locations["range"], locations["nextRange"] = (
                            locations["nextRange"],
                            locations["range"],
                        )

                # dots
                self.dots(opacity=1)

                # rules
                ruleSide = 80

                for j, yRatio in enumerate([0, 0.5, 1]):
                    for i, xRatio in enumerate([0, 0.5, 1]):
                        cycleOff, cycleOn, switch = self.rulesCycles[j][i]
                        cycleOff *= FPS
                        cycleOn *= FPS

                        if switch:
                            db.fill(*WHITE)
                            x, y = coordinates(xRatio, yRatio)
                            self.spring(
                                (x - ruleSide / 2, y - ruleSide / 2, ruleSide, ruleSide),
                                (eachFrame % cycleOn) / cycleOn,
                            )

                        if switch and ((eachFrame % cycleOn) / (cycleOn - 1)) == 1:
                            switch = not switch
                            self.rulesCycles[j][i][2] = switch
                        if not switch and ((eachFrame % cycleOff) / (cycleOff - 1)) == 1:
                            switch = not switch
                            self.rulesCycles[j][i][2] = switch

            db.saveImage(path)


# ----------
# Timeline
# ----------
if __name__ == "__main__":
    cm = ColorManager(
        rawColors=[
            dict(r=1, g=0.8, b=0, x=0, y=1),
            dict(r=1, g=0.2, b=0, x=0, y=0),
            dict(r=1, g=0.2, b=0.75, x=1, y=1),
            dict(r=0.1, g=0.1, b=0.8, x=1, y=0),
        ]
    )
    am = AnimationManager(
        colorManager=cm,
        rulesCycles=[
            # seconds off, seconds on, switch (False by default)
            [[4, 2, False], [3, 2, False], [4, 3, False]],
            [[2, 2, False], [4, 2, False], [1, 3, False]],
            [[3, 1, False], [3, 3, False], [4, 2, False]],
        ],
        locationToCycle={"lft": 24 * 2, "mid": 24 * 3, "rgt": 24},
    )
    am.draw(Path("output/1.mp4"))

    cm = ColorManager(
        rawColors=[
            dict(r=1, g=0.8, b=0, x=1, y=1),
            dict(r=1, g=0.2, b=0, x=0, y=1),
            dict(r=1, g=0.2, b=0.75, x=1, y=0),
            dict(r=0.1, g=0.1, b=0.8, x=0, y=0),
        ]
    )

    am = AnimationManager(
        colorManager=cm,
        rulesCycles=[
            # seconds off, seconds on, switch (False by default)
            [[3, 1, False], [3, 3, False], [4, 2, False]],
            [[2, 2, False], [4, 2, False], [1, 3, False]],
            [[4, 2, False], [3, 2, False], [4, 3, False]],
        ],
        locationToCycle={"lft": 24 * 1, "mid": 24 * 4, "rgt": 24},
    )
    am.draw(Path("output/2.mp4"))

    cm = ColorManager(
        rawColors=[
            dict(r=1, g=0.8, b=0, x=1, y=1),
            dict(r=1, g=0.2, b=0, x=1, y=0),
            dict(r=1, g=0.2, b=0.75, x=0, y=1),
            dict(r=0.1, g=0.1, b=0.8, x=0, y=0),
        ]
    )
    am = AnimationManager(
        colorManager=cm,
        rulesCycles=[
            # seconds off, seconds on, switch (False by default)
            [[3, 2, False], [4, 2, False], [4, 2, False]],
            [[3, 3, False], [4, 3, False], [4, 2, False]],
            [[2, 2, False], [3, 3, False], [1, 3, False]],
        ],
        locationToCycle={"lft": 24 * 2, "mid": 24 * 3, "rgt": 24 * 4},
    )
    am.draw(Path("output/3.mp4"))
