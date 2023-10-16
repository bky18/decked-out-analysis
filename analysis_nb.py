# %%
# %matplotlib widget
# NOTE: try `%matplotlib inline`` if this gives you problems


import functools as ft
import itertools as it
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from typing import Iterator
from typing import Literal
from typing import TypedDict

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseButton
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from matplotlib.typing import ColorType

import data.model
import data.parse
import data.plot


# import deck


pd.set_option("display.max_rows", 50)
# %% [markdown]
# # Data Parsing
#
# Collect the data we need from the two spreadsheets
#

# %%
# %%
data.plot.DeckStatsFigure()
