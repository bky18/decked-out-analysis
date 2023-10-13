# %%
# %matplotlib widget
# NOTE: try `%matplotlib inline`` if this gives you problems


from collections import defaultdict
from collections.abc import Sequence
from typing import Any
from typing import Callable
from typing import Iterator
from typing import Literal
from typing import TypedDict

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event
from matplotlib.backend_bases import MouseButton
from matplotlib.backend_bases import MouseEvent
from matplotlib.backend_bases import PickEvent
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
) -> pd.DataFrame:
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
def get_tracked_out_data(
    sheet_id: str,
    sub_sheet: int | str | None = None,
    mode: Literal["HTML", "CSV"] = "HTML",
) -> pd.DataFrame:
    """Reads Tracked Out spread sheet"""
    if mode == "CSV":
        csv_sheet = read_url(sheet_id, sub_sheet, mode)

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
def format_data(
    data: pd.DataFrame,
    converters: dict[str, Callable] | None = None,
    dtypes: dict[str, Any] | None = None,
) -> pd.DataFrame:
    if converters:
        for col, conv in converters.items():
            data[col] = data[col].apply(conv)

    if dtypes:
        for c, d in dtypes.items():
            data = data.astype({c: d})

    return data


# %%
def convert_names(name: str):
    """Helper function to standardize all the possible names."""
    return data.NAME_LOOKUP[name.strip().upper()]


# %%
def csv_url(sheet_id: str, sub_sheet: int | None = None):
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if sub_sheet:
        sheet_url += f"&gid={sub_sheet}"

    return sheet_url


def get_card_tracking_data():
    """Read the Shadeline's Card Tracking sheet."""
    # get the raw sheet
    sheet_id = "14YoASmzAlYpnjPcoLe9rsc0SnieO_XsfWrRFrIcnGBo"
    sheets = []

    for gid in [0, 1470983131, 87401147, 1642273110]:
        cur_sheet = pd.read_csv(
            csv_url(sheet_id, gid), skiprows=[0], skip_blank_lines=True, header=None
        )
        sheets.append(cur_sheet)

    # add phase number column to the sheets
    for i, sheet in enumerate(sheets):
        sheet.insert(0, "phase", i + 1)
    raw_sheet = pd.concat(sheets, axis=0)

    # format the table
    raw_sheet = raw_sheet.iloc[:, :7]
    raw_sheet.columns = [
        "phase",
        "phase run number",
        "hermit run number",
        "hermit",
        "deck size",
        "purchases",
        "deck",
    ]

    # clean the data
    raw_sheet = raw_sheet.dropna(subset=["hermit", "deck", "deck size"])
    raw_sheet["purchases"].replace(["0", "??", np.nan], None, inplace=True)

    # FIXME: manual adjustments update after the data gets cleaned up
    raw_sheet["deck size"] = raw_sheet["deck size"].replace("10 or 11", "10")

    # format the data
    converters = {
        "hermit": convert_names,
        "purchases": deck.Deck.from_str,
        "deck": deck.Deck.from_str,
    }
    dtypes = {
        "phase": "u1",
        "phase run number": "u1",
        "hermit run number": "u1",
        "hermit": data.Hermit,
        "deck size": "u1",
    }
    # FIXME: figure out why getting error converting "deck size" col to in
    formatted_data = format_data(raw_sheet, converters, dtypes)

    return formatted_data


# %%
card_tracking_sheet = get_card_tracking_data()


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
        "purchases": "Cards Bought",
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

    # FIXME: manual adjustments
    data_frame.replace("4 MOC", "MOCx4", inplace=True)

    # convert using data types
    converters = {
        "run number": int,
        "hermit": convert_names,
        "run reference": str,
        "hermit run number": int,
        "ethereal cards": deck.Deck.from_str,
        # "difficulty": lambda x: print(f"difficulty str {x}") or data.Difficulty.from_str(x),
        "level": data.DungeonLevel.from_str,
        # "result": data.Result.from_str,
        "purchases": deck.Deck.from_str,
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
        data_frame[col_name] = data_frame[col_name].apply(converter)

    # apply dtypes
    data_frame = data_frame.astype(dtypes)

    # set the index
    data_frame.set_index("run number", inplace=True)

    return data_frame


# %%
parsed_html_sheet = parse_deck_data(
    get_tracked_out_data(
        "1vQrXRcKhaXrVDsUs9rcnfCSTC3K-9Q_D8Cidl4IP4rUcPeiSSNxU2fv7eHce4F_EXHZM7RJCTcSbS_b",
        1,
        mode="HTML",
    )
)

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
        "purchases": Sequence[deck.Deck],
        "phase": Sequence[int],
    },
)


def calculate_deck_stats(
    run_data: RunData,
    attr: Literal["size", "power", "efficiency"] | None = None,
    ignore_ethereal_cards: bool = False,
    replace_nan: bool = False,
):
    max_run_num = max(run_data["hermit run number"])

    # tracks the state of the player's deck on each run
    player_deck_data: defaultdict[str, list[deck.Deck]] = defaultdict(
        lambda: [None] * (max_run_num + 1)
    )
    # tracks the state of the player's deck after the most recent run was completed
    player_current_deck: defaultdict[str, deck.Deck] = defaultdict(
        lambda: deck.Deck.from_str("SNE,TRH")
    )

    # add column if not present
    if "ethereal cards" not in run_data.columns:
        run_data["ethereal cards"] = None

    for player, run_num, eth_cards, bought_cards in zip(
        run_data["hermit"],
        run_data["hermit run number"],
        run_data["ethereal cards"],
        run_data["purchases"],
    ):
        cur_deck: deck.Deck = player_current_deck[player] + eth_cards
        if ignore_ethereal_cards:
            cur_deck = cur_deck.strip_ethereal_cards()
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
                lambda cell: getattr(cell, attr) if cell else np.nan
            )

    if replace_nan:
        results.replace(np.nan, "—", inplace=True)

    return results


# %%
COLOR_MAP = {
    "Bdubs": "#66822d",
    "Cub": "#3086c8",
    "Doc": "#228b22",
    "Etho": "#68fdf6",
    "False": "#ff69b4",
    "Gem": "#00ff7f",
    "Grian": "#dc143c",
    "Hypno": "#000000",
    "Jevin": "#469ec5",
    "Impulse": "#f1c936",
    "Iskall": "#9acd32",
    "Joe": "#7cfc00",
    "Keralis": "#ecfb01",
    "Mumbo": "#ef6562",
    "Pearl": "#ff4500",
    "Ren": "#8b0024",
    "Scar": "#fe8705",
    "Stress": "#ff00ff",
    "Tango": "#00ffff",
    "Beef": "#562d19",
    # "Wels": "",
    "xB": "#008b8b",
    "Xisuma": "#7b68ee",
    "Zed": "#ff93bc",
    "Cleo": "#008b8b",
}


# %%
def add_annotation(ax: Axes, line: Line2D):
    # get coordinates where each line ends
    x = -1
    y = -1
    for x, y in zip(reversed(line.get_xdata()), reversed(line.get_ydata())):
        if np.isfinite(x) and np.isfinite(y):
            break

    player_label = line.get_label()
    assert isinstance(player_label, str)
    *prefix, player_label = player_label.split("-")
    line.set_color(COLOR_MAP[player_label])

    # don't annotate lines with a prefix
    if not prefix:
        ax.annotate(
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
    # create each figure
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

        for col in stripped_stats:
            player_series = stripped_stats[col]
            # matplotlib automatically interpolates intermediate values if they're missing and not set to NAN
            interpolated_values = player_series[np.isfinite(player_series)]

            # Iterate over the missing values series, and remove all consecutive points
            # so that the two plots don't overlap
            indices_to_drop = set()
            for idx_val in interpolated_values.index[1:-1]:
                # only keep values if one of the adjacent values are missing
                if (
                    idx_val + 1 in interpolated_values
                    and idx_val - 1 in interpolated_values
                ):
                    indices_to_drop.add(idx_val)

            # handle the first and last indices as special cases
            first_idx_val = interpolated_values.index[0]
            if first_idx_val + 1 in interpolated_values:
                indices_to_drop.add(first_idx_val)

            last_idx_val = interpolated_values.index[0]
            if last_idx_val - 1 in interpolated_values:
                indices_to_drop.add(last_idx_val)

            # replace the duplicate values with nan
            for idx in indices_to_drop:
                interpolated_values[idx] = np.nan

            ax.plot(
                interpolated_values.index,
                interpolated_values,
                label=f"interp-{col}",
                ls="--",
            )
            ax.plot(player_series.index, player_series, label=col)

        ax.set_title(title)
        ax.set_facecolor("#1b2032")

        for line in ax.lines:
            assert isinstance(line, Line2D)
            # skip over interpolated lines
            add_annotation(ax, line)

    return fig, axes


# %%
fig, sub_plots = plot(
    [
        calculate_deck_stats(card_tracking_sheet, "size"),
        calculate_deck_stats(card_tracking_sheet, "power"),
        calculate_deck_stats(card_tracking_sheet, "efficiency"),
    ],
    [
        "Deck Size",
        "Deck Power",
        "Deck Efficiency",
    ],
)


# %%
def iter_lines(e: MouseEvent) -> Iterator[tuple[Axes, str, list[Line2D], Annotation]]:
    """Helper function to iterate over all the axes, lables, lines and annotations from a MouseEvent"""
    for cur_plot in e.canvas.figure.axes:
        annotations = {
            a.get_text(): a
            for a in cur_plot.get_children()
            if isinstance(a, Annotation)
        }
        # stores all the lines that should be associated with a single label
        lines: defaultdict[str, list[Line2D]] = defaultdict(list)
        for line in cur_plot.lines:
            assert isinstance(line, Line2D)

            label = line.get_label()
            assert isinstance(label, str)
            *_, label = label.split("-")
            lines[label].append(line)

        for label, lines in lines.items():
            yield cur_plot, label, lines, annotations[label]


# %%
def on_hover(event: MouseEvent):
    def _bring_to_front(line):
        # bring line to the front
        line.set_zorder(1)
        line.set_linewidth(2)

    def _send_to_back(line):
        line.set_zorder(0)
        line.set_linewidth(1)

    # if any line in the group are hovered, bring them all to the front
    for _, _, lines, annotation in iter_lines(event):
        if any(line.contains(event)[0] for line in lines):
            handler = _bring_to_front
            annotation.set_zorder(1)
            annotation.set_fontweight("bold")
        else:
            handler = _send_to_back
            annotation.set_zorder(0)
            annotation.set_fontweight("normal")

        for line in lines:
            handler(line)


# %%
def set_visibility(event: MouseEvent, lines: set[str], visibility: bool):
    for _, label, ls, a in iter_lines(event):
        if label in lines:
            for l in ls:
                l.set_visible(visibility)
            a.set_visible(visibility)


def on_pick(event: PickEvent):
    lines_to_show: set[str] = set()
    lines_to_hide: set[str] = set()
    line_clicked = False
    for _, label, lines, _ in iter_lines(event.mouseevent):
        line_is_visible = any(line.get_visible() for line in lines)
        assert isinstance(label, str)
        # skip if we already have the info
        if label in lines_to_show:
            continue

        if event.mouseevent.button == MouseButton.RIGHT:
            if line_is_visible and any(
                line.contains(event.mouseevent)[0] for line in lines
            ):
                line_clicked = True
                lines_to_hide.add(label)

        elif event.mouseevent.button == MouseButton.LEFT:
            if line_is_visible:
                if any(line.contains(event.mouseevent)[0] for line in lines):
                    lines_to_show.add(label)
                    line_clicked = True
                elif any(line not in lines_to_show for line in lines):
                    lines_to_hide.add(label)
            else:
                lines_to_show.add(label)

    lines_to_hide -= lines_to_show
    if line_clicked and lines_to_hide:
        set_visibility(event.mouseevent, lines_to_hide, False)
    elif lines_to_show:
        set_visibility(event.mouseevent, lines_to_show, True)


# %%
for line in sub_plots:
    line.set_picker(5)

fig.canvas.mpl_connect("motion_notify_event", on_hover)
fig.canvas.mpl_connect("pick_event", on_pick)

plt.tight_layout()
