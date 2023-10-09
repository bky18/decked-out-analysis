# About
This is a personal project for tracking different statistics about the players in Decked Out.
Currently there are 3 statistics that are being tracked:
1. Deck Size
   The number of cards in a player's deck
2. Deck Power
   *Roughly* corresponds to the cumulative cost of each card in a deck in frost embers. Special exceptions are applied for for ethereal cards, cards purchased with crowns, and legendary cards. 
3. Deck Effienciency
   The ratio between deck power and effiencicy
I would like to add much more, but I only have so much time unfortunately.
Also please note that these stats so far only include card purchases.
It does not account for any trades, and so is not 100% accurate. 

# Usage
This work is done entirely through python and Jupyter notebooks.
To run this, you must have at least python 3.11.
To get all the dependencies, you can download the code and run `pip install -r requirements.txt` to get all the dependencies. 
There are also many [alternatives](https://jupyter.org/try) that allow you to run this online.
Do note that this repository stores the notebook with jupytext, as it allows for simpler versioning.
You can convert it back to a jupyter notebook by installing `jupytext` from pip, and running `jupytext --to ipynb -o analysis.ipynp analysis_nb.py`,
or by downloading a version from the [releases](https://github.com/bky18/decked-out-analysis/releases) page.

The data and charts can be quite cluttered, I tried to alleviate that with a couple of features.
If you hover over the chart, the hovered lines should be made bold and brought to the front.

If you click while hovering over any lines, all of the other lines will be hidden.
You can click again with the same lines hilighted to show the rest of the hidden lines.

# Acknowledgements
All of the information is pulled from the absolutely amazing community maintained spreadsheet [Tracked Out](https://docs.google.com/spreadsheets/d/e/2PACX-1vQrXRcKhaXrVDsUs9rcnfCSTC3K-9Q_D8Cidl4IP4rUcPeiSSNxU2fv7eHce4F_EXHZM7RJCTcSbS_b/pubhtml#).
I absolutely would not have been able to do this without their efforts in maintaining the data.
