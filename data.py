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


NAMES = [
    "Bdubs",
    "Cub",
    "Doc",
    "Etho",
    "False",
    "Gem",
    "Grian",
    "Hypno",
    "Jevin",
    "Impulse",
    "Iskall",
    "Joe",
    "Keralis",
    "Mumbo",
    "Pearl",
    "Ren",
    "Scar",
    "Stress",
    "Tango",
    "Beef",
    "Wels",
    "xB",
    "Xisuma",
    "Zed",
    "Cleo",
]
Hermit = pd.CategoricalDtype(NAMES)

# maps hermit's nicknames to full names
_names = {
    ("Bdubs", "BdoubleO100", "BdoubleO"),
    ("Cub", "Cubfan135", "Cubfan"),
    ("Doc", "Docm77"),
    ("Etho", "Ethoslab"),
    ("False", "FalseSymmetry"),
    ("Gem", "GeminiTay"),
    ("Grian", "Grian"),
    ("Hypno", "Hypnotizd"),
    ("Jevin", "iJevin", "Jev"),
    ("Impulse", "impulseSV"),
    ("Iskall", "iskall85"),
    ("Joe", "JoeHills"),
    ("Keralis", "Keralis"),
    ("Mumbo", "MumboJumbo"),
    ("Pearl", "PearlescentMoon"),
    ("Ren", "Rendog"),
    ("Scar", "GoodTimesWithScar", "GoodTimeWithScar"),
    ("Stress", "Stressmonster", "Stressmonster101"),
    ("Tango", "TangoTek", "Dungeon Master", "Dungeon Lackey", "DM", "DL"),
    ("Beef", "VintageBeef"),
    ("Wels", "Welsknight"),
    ("xB", "xBCrafted"),
    ("Xisuma", "Xisumavoid", "X"),
    ("Zed", "Zedaph"),
    ("Cleo", "ZombieCleo"),
}

# parse all the possible names
NAME_LOOKUP: dict[str, str] = {}
for aliases in _names:
    name = aliases[0]
    for alias in aliases:
        NAME_LOOKUP[alias.upper()] = name


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
# TODO: de-clutter by removing inactive players
