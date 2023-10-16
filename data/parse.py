"""Module for parsing, formatting, and validation of spreadsheet data."""
from collections import defaultdict
from collections.abc import Sequence
from typing import Any
from typing import Callable
from typing import Literal
from typing import TypedDict

import numpy as np
import pandas as pd

import data.model
import deck


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


def format_data(
    data: pd.DataFrame,
    converters: dict[str, Callable] | None = None,
    dtypes: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Helper function that applies converters to a dataframe.

    The converter functions are applied first, before each column has its data types set.

    Parameters
    ----------
    data : pd.DataFrame
        The data to be formatted
    converters : dict[str, Callable] | None, optional
        A dict which maps the name of a column to a function that should be applied to it.
        Does not apply any by default.
    dtypes : dict[str, Any] | None, optional
        A dict which maps name of a column to the dtype that it should be set to.
        Does not apply any by default.

    Returns
    -------
    pd.DataFrame
        _description_
    """
    if converters:
        for col, conv in converters.items():
            data[col] = data[col].apply(conv)

    if dtypes:
        for c, d in dtypes.items():
            data = data.astype({c: d})

    return data


def convert_names(name: str):
    """Helper function to standardize all the possible names."""
    return data.model.NAME_LOOKUP[name.strip().upper()]


def csv_url(sheet_id: str, sub_sheet: int | None = None):
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if sub_sheet:
        sheet_url += f"&gid={sub_sheet}"

    return sheet_url


def get_card_tracking_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Read the Shadeline's Card Tracking sheet.

    Reads, parse, and format the data from the google spreadsheet.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        A tuple containing the deck data and the run data.
    """
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
        "hermit": data.model.Hermit,
        "deck size": "u1",
    }
    # FIXME: figure out why getting error converting "deck size" col to in
    formatted_data = format_data(raw_sheet, converters, dtypes)

    deck_data = formatted_data.loc[
        :, ["hermit run number", "hermit", "deck size", "purchases", "deck"]
    ]
    run_data = formatted_data.loc[
        :, ["phase", "hermit", "phase run number", "hermit run number"]
    ]
    # TODO: split into deck data and run data
    return deck_data, run_data


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
        "level": data.model.DungeonLevel.from_str,
        # "result": data.Result.from_str,
        "purchases": deck.Deck.from_str,
        "phase": phase_to_int,
    }
    dtypes = {
        "hermit": data.model.Hermit,
        "difficulty": data.model.Difficulty.dtype,
        "level": pd.Int8Dtype(),
        "result": data.model.Result.dtype,
    }

    # apply type conversions
    for col_name, converter in converters.items():
        data_frame[col_name] = data_frame[col_name].apply(converter)

    # apply dtypes
    data_frame = data_frame.astype(dtypes)

    # set the index
    data_frame.set_index("run number", inplace=True)

    return data_frame


parsed_html_sheet = parse_deck_data(
    get_tracked_out_data(
        "1vQrXRcKhaXrVDsUs9rcnfCSTC3K-9Q_D8Cidl4IP4rUcPeiSSNxU2fv7eHce4F_EXHZM7RJCTcSbS_b",
        1,
        mode="HTML",
    )
)

DeckData = TypedDict(
    # TODO: convert from Sequence to pandas Series?
    "DeckData",
    {
        "hermit": Sequence[str],
        "hermit run number": Sequence[int],
        "ethereal cards": Sequence[deck.Deck],
        "purchases": Sequence[deck.Deck],
        "deck": Sequence[deck.Deck],
    },
)

RunData = TypedDict(
    # TODO: convert from Sequence to pandas Series?
    "RunData",
    {
        "hermit": Sequence[str],
        "run number": Sequence[int],
        "run reference": Sequence[str],
        "hermit run number": Sequence[int],
        "ethereal cards": Sequence[deck.Deck],
        "difficulty": Sequence[data.model.Difficulty],
        "level": Sequence[data.model.DungeonLevel],
        "result": Sequence[data.model.Result],
        "purchases": Sequence[deck.Deck],
        "phase": Sequence[int],
    },
)


def calculate_deck_stats(
    run_data: DeckData,
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

    # FIXME: remove "ethereal card column"
    # NOTE: ethereal cards should now be included in the deck column
    # add column if not present
    if "ethereal cards" not in run_data.columns:
        run_data["ethereal cards"] = None

    for player, run_num, eth_cards, bought_cards in zip(
        run_data["hermit"],
        run_data["hermit run number"],
        run_data["ethereal cards"],
        run_data["purchases"],
    ):
        # FIXME: use the "deck" column if present
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


# TODO: display which phase the marker represents when hovered over
def get_phase_run_number(
    run_data: pd.DataFrame, phase_run_index: int = 0
) -> dict[str, dict[int, int]]:
    """
    Gets the run number of each phase's first run, for each player.

    Parameters
    ----------
    run_data : pd.DataFrame
        The data frame containing run data for all of the players.

    Returns
    -------
    dict[str, dict[int, int]]
        Maps the phase number, to the run number of the specified run of that phase.
    """
    # add an extra value at the start to avoid having to offset by 1 when indexing runs
    data: dict[str, dict[int, int]] = defaultdict(dict)

    # get the lowest number for each phase
    for player, player_run_data in run_data.groupby("hermit"):
        for phase_num, phase_run_data in player_run_data.groupby("phase"):
            phase_run_num = (
                phase_run_data["hermit run number"].sort_values().iloc[phase_run_index]
            )
            data[player][phase_num] = phase_run_num

    return data
