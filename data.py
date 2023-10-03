import re
from enum import Enum
from enum import IntEnum
from enum import StrEnum
from typing import Type

import pandas as pd


# TODO: create class that combines the run ref info, and the absolute run numbers


def dtype(__enum: Type[Enum], /):
    __enum.dtype = pd.CategoricalDtype([e.name for e in __enum])
    return __enum


Hermit = pd.CategoricalDtype(
    [
        "BdoubleO100",
        "Cubfan135",
        "Docm77",
        "Ethoslab",
        "FalseSymmetry",
        "GeminiTay",
        "Grian",
        "Hypnotizd",
        "iJevin",
        "impulseSV",
        "iskall85",
        "JoeHills",
        "Keralis",
        "MumboJumbo",
        "Pearl",
        "Rendog",
        "Scar",
        "Stress",
        "TangoTek",
        "VintageBeef",
        "Welsknight",
        "xBCrafted",
        "Xisuma",
        "Zedaph",
        "ZombieCleo",
    ]
)

# maps hermit's nicknames to full names
FULL_NAMES = {
    "Bdubs": "BdoubleO100",
    "Cub": "Cubfan135",
    "Doc": "Docm77",
    "Etho": "Ethoslab",
    "False": "FalseSymmetry",
    "Gem": "GeminiTay",
    "Grian": "Grian",
    "Hypno": "Hypnotizd",
    "Jevin": "iJevin",
    "Impulse": "impulseSV",
    "Iskall": "iskall85",
    "Joe": "JoeHills",
    "Keralis": "Keralis",
    "Mumbo": "MumboJumbo",
    "Pearl": "Pearl",
    "Ren": "Rendog",
    "Scar": "Scar",
    "Stress": "Stress",
    "Tango": "TangoTek",
    "Beef": "VintageBeef",
    "Wels": "Welsknight",
    "xB": "xBCrafted",
    "X": "Xisuma",
    "Zed": "Zedaph",
    "Cleo": "ZombieCleo",
}


@dtype
class Difficulty(IntEnum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    DEADLY = 4
    DEEPFROST = 5

    @classmethod
    def from_str(cls, _s: str | None):
        if _s is None:
            return pd.NA
        try:
            return cls[_s]
        except KeyError:
            return None


@dtype
class Result(StrEnum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    REFUND = "REFUND"

    @classmethod
    def from_str(cls, _s: str | None):
        if _s is None:
            return
        try:
            return cls[_s]
        except KeyError:
            return None


@dtype
class DungeonLevel(IntEnum):
    FROZEN_CRYPT = 1
    CAVES_OF_CARNAGE = 2
    BLACK_MINES = 3
    BURNING_DARK = 4

    @classmethod
    def from_str(cls, _s: str | None):
        if _s is None:
            return

        try:
            level_num = int(re.match(r"^Lv(\d):.*", _s).group(1))
            return cls(level_num)
        except (ValueError, AttributeError):
            return None


# TODO: Add histograms to graph survival rates for grouped by each hermit,
# for each level/difficulty
# TODO: add markers on each for the first run of each phase
# TODO: generate titles for the graphs
# TODO: de-clutter by removing inactive players
# TODO: parse traced and other deck updates from the other sheet
