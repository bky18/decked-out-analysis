"""Module for interacting with Matplotlib to plot the data."""
import functools as ft
import itertools as it
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from typing import Iterator

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseButton
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from matplotlib.typing import ColorType

import data.model
import data.parse


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
            # bring to front, make line thicker
            line.set_zorder(1)
            line.set_linewidth(2)

            # make the markers bold
            line.set_markeredgewidth(2)

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
            # send to back, make lines normal width
            line.set_zorder(0)
            line.set_linewidth(1)

            # make the markers normal
            line.set_markeredgewidth(1)

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


# TODO: add option to rename figure?
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
    run_data: pd.DataFrame
    lines_: defaultdict[str, LineInfo]
    focused_lines: set[str]
    unfocused_lines: set[str]
    hidden_lines: set[str]
    visible_lines: set[str]
    color_map: dict[str, ColorType]

    def __init__(
        self,
        deck_data: dict[str, pd.DataFrame],
        run_data: pd.DataFrame,
        *args,
        color_map: dict[str, ColorType],
        figsize: tuple[int, int] | None = None,
        **kwargs,
    ):
        """
        Constructor

        Parameters
        ----------
        deck_data : dict[str, pd.DataFrame]
            A map of the data frames that should be plotted in the figure, and title of the plot.
        run_data : dict[str, pd.DataFrame]
            A map containing data for each player's runs.
        color_map : dict[str, ColorType]
            A map of the players, and the color that should be used to represent them in the plot.
        figsize : tuple[int, int] | None, optional
            A tuple of the size of the figure, height by width. 16x9 by default.

        Raises
        ------
        ValueError
            If the
        """
        # validate that we have run data for each of the players in the deck data sheet
        players = set()
        for d in deck_data.values():
            players |= set(d.columns)

        missing_players = players - set(run_data["hermit"])
        if missing_players:
            raise ValueError(
                "Missing run data for the following players: "
                + ", ".join(missing_players)
            )

        self.color_map = color_map
        missing_players = players - set(color_map.keys())
        if missing_players:
            raise ValueError(
                "No color provided for the following players: "
                + ", ".join(missing_players)
            )
        self.lines_ = defaultdict(lambda: LineInfo(fig=self))
        self.deck_data = deck_data
        self.run_data = run_data

        if not figsize:
            figsize = (16, 9)
        super().__init__(*args, **kwargs)

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

    def plot_series(
        self, ax: Axes, s: pd.Series, label: str, markevery: list[str] | None = None
    ):
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
        main_line = ax.plot(
            s.index,
            s,
            label=label,
            ls="-",
            marker="|",
            markevery=markevery or [],
        )[0]

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
            color=HERMIT_COLOR_MAP[label],
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

        phase_markers = data.parse.get_phase_run_number(self.run_data, -1)

        for col in df:
            df.loc[:, col] = pd.to_numeric(df[col])

            player_series = df[col]
            # have to subtract because markers use the index, not the x value?
            player_phase_run_markers = [i - 1 for i in phase_markers[col].values()]
            self.plot_series(ax, player_series, col, markevery=player_phase_run_markers)
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


HERMIT_COLOR_MAP = {
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
