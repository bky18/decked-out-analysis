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
@dataclass
class LineInfo:
    """
    Stores all of the Line2D artists and Annotations that should be associated together.
    """

    fig: "DeckStatsFigure" = field(repr=False)
    annotations: dict[Axes, list[Annotation]] = field(
        default_factory=lambda: defaultdict(list)
    )
    line_artists: dict[Axes, list[Line2D]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def iter_lines(self, plots: list[Axes] | None = None) -> Iterator[Line2D]:
        """Iterate over all the `Line2D`s in this object."""
        if plots:
            for ax in plots:
                yield from self.line_artists[ax]
        else:
            for lines in self.line_artists.values():
                yield from lines

    def iter_annotations(self, plots: list[Axes] | None = None) -> Iterator[Annotation]:
        """Iterate over all the `Annotation`s in this object."""
        if plots:
            for ax in plots:
                yield from self.annotations[ax]
        else:
            for lines in self.annotations.values():
                yield from lines

    def focus(self, plots: list[Axes] | None = None) -> bool:
        """
        Emphasize the line on a specific plot.

        Make the line and text bold, and bring to front.

        Parameters
        ----------
        plots : list[Axes] | None, optional
            The list of plots where the lines should be focused.
            Will apply to all plots by default.

        Returns
        -------
        bool
            False if the line's focus was not changed.
        """
        name = self.name
        # can't focus on hidden lines
        if name in self.fig.hidden_lines:
            return False
        # return false if no changes applies
        if name in self.fig.focused_lines:
            return False

        for line in self.iter_lines(plots):
            line.set_zorder(1)
            line.set_linewidth(2)

        for anno in self.iter_annotations(plots):
            anno.set_zorder(1)
            anno.set_fontweight("bold")

        # update the figure's state
        self.fig.unfocused_lines.remove(name)
        self.fig.focused_lines.add(name)
        return True

    def unfocus(self, plots: list[Axes] | None = None) -> bool:
        """
        Deemphasize the line on a specific plot.

        Make the line and text normal, and bring to back.

        Parameters
        ----------
        plots : list[Axes] | None, optional
            The list of plots where the lines should be unfocused.
            Will apply to all plots by default.

        Returns
        -------
        bool
            False if the line's focus was not changed.
        """
        name = self.name
        # can't focus on hidden lines
        if name in self.fig.hidden_lines:
            return False
        # return false if no changes applies
        if name in self.fig.unfocused_lines:
            return False

        for line in self.iter_lines(plots):
            line.set_zorder(0)
            line.set_linewidth(1)

        for anno in self.iter_annotations(plots):
            anno.set_zorder(0)
            anno.set_fontweight("normal")

        # update the figure's state
        self.fig.unfocused_lines.add(name)
        self.fig.focused_lines.remove(name)

        return True

    def show(self, plots: list[Axes] | None = None) -> bool:
        """
        Show the lines in the specified plots.

        Parameters
        ----------
        plots : list[Axes] | None, optional
            The list of plots where the lines should shown.
            Will apply to all plots by default.

        Returns
        -------
        bool
            False if the visibility was not changed.
        """
        # skip if visibility won't be changed
        name = self.name
        if name in self.fig.visible_lines:
            return False

        for a in self.iter_annotations(plots):
            a.set_visible(True)

        for l in self.iter_lines(plots):
            l.set_visible(True)

        # update the state
        self.fig.hidden_lines.remove(name)
        self.fig.visible_lines.add(name)
        self.fig.focused_lines.add(name)
        self.unfocus(plots)

        return True

    def hide(self, plots: list[Axes] | None = None) -> bool:
        """
        Hide the lines in the specified plots.

        Parameters
        ----------
        plots : list[Axes] | None, optional
            The list of plots where the lines should be hidden.
            Will apply to all plots by default.

        Returns
        -------
        bool
            False if the visibility was not changed.
        """
        # skip if visibility won't be changed
        name = self.name
        if name in self.fig.hidden_lines:
            return False

        for a in self.iter_annotations(plots):
            a.set_visible(False)

        for l in self.iter_lines(plots):
            l.set_visible(False)

        # update the state
        self.fig.hidden_lines.add(name)
        self.fig.visible_lines.remove(name)

        # hidden lines can't be focused
        self.unfocus(plots)
        if name in self.fig.unfocused_lines:
            self.fig.unfocused_lines.remove(name)
        return True

    @ft.cached_property
    def name(self) -> str:
        found_names: set[str] = set()

        for line in self.iter_lines():
            # strip any suffixes
            *_, label = line.get_label().split("-")

            found_names.add(label)

        num_names = len(found_names)
        if num_names == 0:
            raise ValueError(f"No names were found")
        elif num_names != 1:
            raise ValueError(f"Conflicting names were found: {', '.join(found_names)}")

        return found_names.pop()


# %%
class DeckStatsFigure(Figure):
    """
    Custom figure for plotting the deck data.

    Attributes
    ----------
    deck_data : dict[str, pd.DataFrame]
        A map of the data frames that should be plotted, and the titles of each plot.
    lines : dict[str, LineInfo]
        A map of all the Line2D artists, and annotations that should be associated with
        a player's name.
    """

    deck_data: dict[str, pd.DataFrame]
    lines_: defaultdict[str, LineInfo]
    focused_lines: set[str]
    unfocused_lines: set[str]
    hidden_lines: set[str]
    visible_lines: set[str]
    color_map: dict[str, ColorType]

    def __init__(
        self,
        deck_data: dict[str, pd.DataFrame],
        *args,
        color_map: dict[str, ColorType],
        figsize: tuple[int, int] | None = None,
        **kwargs,
    ):
        if not figsize:
            figsize = (16, 9)
        super().__init__(*args, **kwargs)
        self.color_map = color_map
        self.lines_ = defaultdict(lambda: LineInfo(fig=self))
        self.deck_data = deck_data
        rows = len(self.deck_data)

        # create each figure
        for i, (title, df) in enumerate(self.deck_data.items(), start=1):
            ax = self.add_subplot(rows, 1, i)
            self.plot_dataframe(ax, df, title)

        self.focused_lines = set()
        self.hidden_lines = set()
        self.unfocused_lines = set(self.lines_)
        self.visible_lines = set(self.lines_)

        self.set_figheight(figsize[0])
        self.set_figwidth(figsize[1])
        # add event handlers
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def plot_series(self, ax: Axes, s: pd.Series, label: str):
        """
        Plots the series in the given sub plot.

        Parameters
        ----------
        ax : Axes
            The subplot to plot the series in.
        s : pd.Series
            The series to be plotted
        label : str
            The name to be associated with the series.

        Returns
        -------
        LineInfo
            All of the associated information about the plotted line.
        """
        # matplotlib automatically interpolates intermediate values if they're missing and not set to NAN
        interpolated_s = s[np.isfinite(s)]

        # Iterate over the missing values series, and remove all consecutive points
        # so that the two plots don't overlap
        indices_to_drop = set()
        for idx_val in interpolated_s.index[1:-1]:
            # only keep values if one of the adjacent values are missing
            if idx_val + 1 in interpolated_s and idx_val - 1 in interpolated_s:
                indices_to_drop.add(idx_val)

        # handle the first and last indices as special cases
        first_idx_val = interpolated_s.index[0]
        if first_idx_val + 1 in interpolated_s:
            indices_to_drop.add(first_idx_val)

        last_idx_val = interpolated_s.index[0]
        if last_idx_val - 1 in interpolated_s:
            indices_to_drop.add(last_idx_val)

        # replace the duplicate values with nan
        for idx in indices_to_drop:
            interpolated_s[idx] = np.nan

        # plot the lines
        interp_line = ax.plot(
            interpolated_s.index,
            interpolated_s,
            label=f"interp-{label}",
            ls="--",
        )[0]
        main_line = ax.plot(s.index, s, label=label)[0]

        # set the line color
        interp_line.set_color(self.color_map[label])
        main_line.set_color(self.color_map[label])

        # get the coordinates of the end of the line
        reversed_coords = reversed(list(s.items()))
        (x, y) = (np.nan, np.nan)
        while np.isnan(y) or np.isnan(x):
            x, y = next(reversed_coords)

        # add annotation to the end of the main line
        annotation = ax.annotate(
            label,
            xy=(x, y),
            xytext=(0, 0),
            color=COLOR_MAP[label],
            xycoords=(ax.get_xaxis_transform(), ax.get_yaxis_transform()),
            textcoords="offset points",
        )

        # send all lines to the back
        main_line.set_zorder(0)
        interp_line.set_zorder(0)
        annotation.set_zorder(0)

        # save references to new lines and annotation
        if self.lines_[label] is None:
            self.lines_[label] = LineInfo(label, self)

        self.lines_[label].annotations[ax].append(annotation)
        self.lines_[label].line_artists[ax] += [main_line, interp_line]

    def plot_dataframe(self, ax: Axes, df: pd.DataFrame, title: str):
        """
        Plots the dataframe.

        Parameters
        ----------
        ax : Axes
            The subplot to plot the data frame in.
        df : pd.DataFrame
            The data to be plotted.
        title : str
            The title of the sub plot.
        """
        # drop the first row which is the "current stats" row
        df = df.iloc[1:, :]
        # Using Int8 means max of 255 runs
        df.index = df.index.astype(pd.UInt8Dtype())

        for col in df:
            df.loc[:, col] = pd.to_numeric(df[col])

            player_series = df[col]
            self.plot_series(ax, player_series, col)
        ax.set_title(title)
        ax.set_facecolor("#1b2032")

    def on_hover(self, event: MouseEvent):
        """Event handler for emphasizing lines when hovered over with the mouse."""
        # if any line in the group are hovered, bring them all to the front
        ax = event.inaxes
        if not ax:
            return

        lines_updated = False
        for cur_label, line_info in self.lines_.items():
            for cur_artist in it.chain(
                line_info.line_artists[ax], line_info.annotations[ax]
            ):
                is_hovered = cur_artist.contains(event)[0]
                # skip over line if not hovered over
                if is_hovered:
                    if line_info.focus(plots=[ax]):
                        lines_updated = True
                        break
                else:
                    if line_info.unfocus(plots=[ax]):
                        lines_updated = True
                        break

        if lines_updated:
            self.canvas.draw_idle()

    def on_click(self, event: MouseEvent):
        """Event handler for hiding/showing lines when they are clicked."""
        lines_to_hide = set()
        lines_to_show = set()

        if event.button == MouseButton.LEFT:
            if self.unfocused_lines:
                # hide unfocused lines if there are any
                lines_to_hide = self.unfocused_lines.copy()
            else:
                # else, show all hidden lines
                lines_to_show = self.hidden_lines.copy()
        elif event.button == MouseButton.RIGHT:
            # hide the focused lines
            lines_to_hide = self.focused_lines.copy()

        # update line visibility
        # only hide lines if it won't hide all the lines
        if lines_to_hide != self.visible_lines:
            for label in lines_to_hide:
                self.lines_[label].hide()

        for label in lines_to_show:
            self.lines_[label].show()


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
FIG = plt.figure(
    FigureClass=DeckStatsFigure,
    deck_data={
        "Deck Size": calculate_deck_stats(card_tracking_sheet, "size"),
        "Deck Power": calculate_deck_stats(card_tracking_sheet, "power"),
        "Deck Efficiency": calculate_deck_stats(card_tracking_sheet, "efficiency"),
    },
    color_map=COLOR_MAP,
    tight_layout=True,
)
