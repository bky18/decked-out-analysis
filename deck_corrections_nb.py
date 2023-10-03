# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
# ---

# %%
# %matplotlib widget
# NOTE: try `%matplotlib inline`` if this gives you problems

import functools as ft
from collections import defaultdict
from collections.abc import Sequence
from typing import Literal
from typing import TypedDict

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event

import data
import deck
import analysis_nb
