# %%
# %matplotlib widget
# NOTE: try `%matplotlib inline` if this gives you problems

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

import data.model
import data.parse
import data.plot


pd.set_option("display.max_rows", 50)
# %% [markdown]
# # Data Parsing
#
# Collect the data we need from the two spreadsheets
#

# %%
raw_deck_data, raw_run_data  = data.parse.get_card_tracking_data()
deck_size_data = data.parse.calculate_deck_stats(raw_deck_data, "size")
deck_power_data = data.parse.calculate_deck_stats(raw_deck_data, "power")
deck_efficiency_data = data.parse.calculate_deck_stats(raw_deck_data, "efficiency")
deck_data={
    "Deck Size": deck_size_data,
    "Deck Power": deck_power_data,
    "Deck Efficiency": deck_efficiency_data,
}

# %%
FIG = plt.figure(
    FigureClass=data.plot.DeckStatsFigure,
    deck_data=deck_data,
    run_data=raw_run_data,
    color_map=data.plot.HERMIT_COLOR_MAP,
    tight_layout=True,
)
