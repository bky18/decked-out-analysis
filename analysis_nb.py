# %%
# %matplotlib widget
# NOTE: try `%matplotlib inline`` if this gives you problems


from collections import defaultdict
from collections.abc import Sequence
from typing import Literal
from typing import TypedDict

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation

import data
import deck


pd.set_option("display.max_rows", 50)


# %%
def read_url(
    sheet_id: str,
    sub_sheet: int | str | None = None,
    mode: Literal["HTML", "CSV"] = "HTML",
):
    if mode == "CSV":
        sheet_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        )
        if sub_sheet:
            sheet_url += f"&gid={sub_sheet}"
        return pd.read_csv(sheet_url)
    else:
        sheet_url = (
            f"https://docs.google.com/spreadsheets/d/e/2PACX-{sheet_id}/pubhtml#"
        )
        return pd.read_html(sheet_url)[sub_sheet or 0]


# %%
def get_raw_data(
    sheet_id: str,
    sub_sheet: int | str | None = None,
    mode: Literal["HTML", "CSV"] = "HTML",
) -> str:
    # load a google sheet from the url using pandas
    # NOTE: parsing the csv gets NaN for the run numbers, possibly because that column is merged?
    if mode == "CSV":
        sheet_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        )
        if sub_sheet:
            sheet_url += f"&gid={sub_sheet}"
        csv_sheet = read_url(sheet_url, sub_sheet, mode)

        header = csv_sheet.iloc[0]
        raw_data = csv_sheet[2:]
    else:
        html_sheet = read_url(sheet_id, sub_sheet, mode).iloc[:, 1:]
        # drop one of the extra "Run No." Columns
        html_sheet.drop(html_sheet.columns[1], axis=1, inplace=True)
        header = html_sheet.iloc[1]
        raw_data = html_sheet.iloc[4:]

    raw_data.columns = header
    return raw_data


# %%
html_sheet = get_raw_data(
    "1vQrXRcKhaXrVDsUs9rcnfCSTC3K-9Q_D8Cidl4IP4rUcPeiSSNxU2fv7eHce4F_EXHZM7RJCTcSbS_b",
    1,
    mode="HTML",
)


# %%
def phase_to_int(_s: str | None):
    if _s is None:
        return None
    return int(_s.split()[1])


def parse_deck_data(data_frame: pd.DataFrame) -> pd.DataFrame:
    # read raw data into the data that we want
    # ignore all the notes and other random info at the end of the table
    data_frame = data_frame.iloc[:, :-11]
    name_map = {
        "run number": "Run No.",
        "hermit": "Hermit",
        "run reference": "Run Ref.",
        "hermit run number": "Hermits Run No.",
        "ethereal cards": "Ethereal Played",
        "difficulty": "Difficulty",
        "level": "Floor (Compass Goal)",
        "result": "Success/Fail",
        "cards bought": "Cards Bought",
        "phase": "Phase",
    }
    names, cols = zip(*name_map.items())

    ## extract the data we want
    # drop the first 3 rows, only copy get the columns we want
    data_frame: pd.DataFrame = data_frame.loc[:, cols].copy()
    # data_frame: pd.DataFrame = data_frame.iloc[3:, cols].copy().rename()
    # reassign the column names
    data_frame.columns = names

    # filter rows without a run number, or if the run is unaccounted for
    data_frame.dropna(subset={"run reference"}, inplace=True)

    data_frame.replace({np.nan: None}, inplace=True)

    # convert using data types
    converters = {
        "run number": int,
        "run reference": str,
        "hermit run number": int,
        "ethereal cards": deck.Deck,
        # "difficulty": lambda x: print(f"difficulty str {x}") or data.Difficulty.from_str(x),
        "level": data.DungeonLevel.from_str,
        # "result": data.Result.from_str,
        "cards bought": deck.Deck,
        "phase": phase_to_int,
    }
    dtypes = {
        "hermit": data.Hermit,
        "difficulty": data.Difficulty.dtype,
        "level": pd.Int8Dtype(),
        "result": data.Result.dtype,
    }

    # apply type conversions
    for col_name, converter in converters.items():
        # print for debugging
        # print(col_name, converter.__name__)
        data_frame[col_name] = data_frame[col_name].apply(converter)

    # apply dtypes
    data_frame = data_frame.astype(dtypes)
    # data_frame.dropna(how="any", inplace=True)

    # set the index
    data_frame.set_index("run number", inplace=True)

    return data_frame


# %%
parsed_html_sheet = parse_deck_data(html_sheet)

# %%
RunData = TypedDict(
    # TODO: convert from Sequence to pandas Series?
    "RunData",
    {
        "hermit": Sequence[str],
        "run number": Sequence[int],
        "run reference": Sequence[str],
        "hermit run number": Sequence[int],
        "ethereal cards": Sequence[deck.Deck],
        "difficulty": Sequence[data.Difficulty],
        "level": Sequence[data.DungeonLevel],
        "result": Sequence[data.Result],
        "cards bought": Sequence[deck.Deck],
        "phase": Sequence[int],
    },
)


def calculate_deck_stats(
    run_data: RunData,
    attr: Literal["size", "power", "efficiency"] | None = None,
):
    max_run_num = max(run_data["hermit run number"])

    # tracks the state of the player's deck on each run
    player_deck_data: defaultdict[str, list[deck.Deck]] = defaultdict(
        lambda: [None] * (max_run_num + 1)
    )
    # tracks the state of the player's deck after the most recent run was completed
    player_current_deck: defaultdict[str, deck.Deck] = defaultdict(
        lambda: deck.Deck("SNE,TRH")
    )
    for player, run_num, eth_cards, bought_cards in zip(
        run_data["hermit"],
        run_data["hermit run number"],
        run_data["ethereal cards"],
        run_data["cards bought"],
    ):
        cur_deck: deck.Deck = player_current_deck[player] + eth_cards
        player_deck_data[player][run_num] = cur_deck

        # update the player's deck
        player_current_deck[player] = cur_deck.strip_ethereal_cards() + bought_cards

    # add current deck, rename index
    col_name = f'Cur {attr or "deck"}'
    results = pd.DataFrame(player_deck_data).rename(index={0: col_name})
    results.index.name = "Run #"
    results.columns.name = "Player"

    for player in results:
        # add the "current" deck for each player
        results.loc[col_name, player] = player_current_deck[player]

        # convert deck to get the queried attribute
        if attr:
            results[player] = results[player].apply(
                lambda cell: getattr(cell, attr) if cell else "—"
            )

    return results


# %%
COLOR_MAP = {
    "BdoubleO100": "#66822d",
    "Cubfan135": "#3086c8",
    "Docm77": "#228b22",
    "Ethoslab": "#68fdf6",
    "FalseSymmetry": "#ff69b4",
    "GeminiTay": "#00ff7f",
    "Grian": "#dc143c",
    "Hypnotizd": "#000000",
    "iJevin": "#469ec5",
    "impulseSV": "#f1c936",
    "iskall85": "#9acd32",
    "JoeHills": "#7cfc00",
    "Keralis": "#a9a9a9",
    "MumboJumbo": "#ef6562",
    "Pearl": "#ff4500",
    "Rendog": "#8b0024",
    "Scar": "#fe8705",
    "Stress": "#ff00ff",
    "TangoTek": "#00ffff",
    "VintageBeef": "#562d19",
    # "Welsknight": "",
    "xBCrafted": "#008b8b",
    "Xisuma": "#7b68ee",
    "Zedaph": "#ff93bc",
    "ZombieCleo": "#008b8b",
}

# %%

ANNOTATIONS: dict[Line2D, Annotation] = {}


def add_annotation(ax, line):
    # get coordinates where each line ends
    for x, y in zip(reversed(line.get_xdata()), reversed(line.get_ydata())):
        if np.isfinite(x) and np.isfinite(y):
            break

    player_label = line.get_label()
    line.set_color(COLOR_MAP[player_label])
    ANNOTATIONS[line] = ax.annotate(
        player_label,
        xy=(x, y),
        xytext=(0, 0),
        color=line.get_color(),
        xycoords=(ax.get_xaxis_transform(), ax.get_yaxis_transform()),
        textcoords="offset points",
    )


def plot(
    data_frames: list[pd.DataFrame], titles: list[str]
) -> tuple[Figure, list[Axes]]:
    fig, axes = plt.subplots(nrows=len(data_frames), ncols=1, figsize=(9, 16))
    for df, ax, title in zip(data_frames, axes, titles):
        assert isinstance(ax, Axes)

        # replace the dashes with NaN, so that the data will be numerical
        # drop the first row which is the "current stats" row
        stripped_stats = df.iloc[1:, :].replace("—", np.NaN)
        # Using Int8 means max of 255 runs
        stripped_stats.index = stripped_stats.index.astype(pd.Int8Dtype())

        for col in stripped_stats:
            stripped_stats[col] = pd.to_numeric(stripped_stats[col])

        # stripped_stats.plot(figsize=(8, 4.5), title=stripped_stats.style.caption, ax=ax)
        stripped_stats.plot(ax=ax, legend=0)
        ax.set_title(title)
        ax.set_facecolor("#1b2032")

        for line in ax.lines:
            add_annotation(ax, line)

    return fig, axes


# %%
fig, sub_plots = plot(
    [
        calculate_deck_stats(parsed_html_sheet, "size"),
        calculate_deck_stats(parsed_html_sheet, "power"),
        calculate_deck_stats(parsed_html_sheet, "efficiency"),
    ],
    ["Deck Size", "Deck Power", "Deck Efficiency"],
)

LABEL_MAP: defaultdict[str, list[Line2D]] = defaultdict(list)

for cur_plot in sub_plots:
    for line in cur_plot.lines:
        LABEL_MAP[line.get_label()].append(line)


# %%
def on_hover(event: Event):
    for cur_plot in sub_plots:
        for line in cur_plot.lines:
            if line.contains(event)[0]:
                line.set_zorder(1)
                line.set_linewidth(2)
                ANNOTATIONS[line].set_zorder(1)
                ANNOTATIONS[line].set_fontweight("bold")
            else:
                line.set_zorder(0)
                ANNOTATIONS[line].set_zorder(0)
                line.set_linewidth(1)
                ANNOTATIONS[line].set_fontweight("normal")


# %%


def on_pick(event):
    num_visible = 0
    labels = set()
    active_line_names = set()
    toggle_lines = False

    for plot in sub_plots:
        for line in plot.lines:
            label = line.get_label()
            labels.add(label)
            num_visible += line.get_visible()
            if line.contains(event.mouseevent)[0]:
                # only want to toggle visibility if clicking on a visible line
                if line.get_visible():
                    toggle_lines = True
                    active_line_names.add(label)

    if not toggle_lines:
        return

    # set visible if num active == num visible
    # set invisible id num active < num visible
    # set visible if num active >= num visible

    # if there's only 1 line per plot, set the lines to all be visible, hidden otherwise
    visibility = num_visible <= (len(active_line_names) * 3)
    for name in labels - active_line_names:
        for line in LABEL_MAP[name]:
            # hide the line
            line.set_visible(visibility)
            # hide the annotations
            ANNOTATIONS[line].set_visible(visibility)


# %%
for line in sub_plots:
    line.set_picker(5)

fig.canvas.mpl_connect("motion_notify_event", on_hover)
fig.canvas.mpl_connect("pick_event", on_pick)

plt.tight_layout()

# %%
