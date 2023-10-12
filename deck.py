"""Module for handling cards and decks."""
import re
from collections import defaultdict
from dataclasses import InitVar
from dataclasses import dataclass
from dataclasses import field
from enum import IntEnum
from typing import ClassVar
from typing import Self


class CardLevel(IntEnum):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    LEGENDARY = 4
    ETHEREAL = 5


# ETHEREAL_CARDS: dict[str, "EtherealCard"] = {}

CROWN_PRICE_POWER_FACTOR = 5
EMBER_PRICE_POWER_FACTOR = 1


@dataclass
class Card:
    # maps a short name to a card instance
    card_lookup: ClassVar[dict[str, "Card"]] = {}
    # maps all the possible names of a card to a short name
    name_map: ClassVar[dict[str, str]] = {"LOOT & SCOOT": "LAS", "LOOT N' SCOOT": "LAS"}

    name: str
    level: CardLevel
    price: int | None = None
    limit: int | None = 3
    crowns_purchase: bool = False
    # power will always be initialized to an int by __post_init__
    power: int = None  # type: ignore
    permanent: bool = False
    short_name: str = None  # type: ignore

    def __post_init__(self):
        # clean up card name
        self.name = self.name.strip()
        # skip if power is already set
        if self.power is None:
            # automatically infer the card's power
            if self.price is None:
                raise ValueError("card price and power cannot both be None.")

            self.power = self.price

            if self.crowns_purchase:
                self.power *= CROWN_PRICE_POWER_FACTOR
            else:
                self.power *= EMBER_PRICE_POWER_FACTOR

        # automatically generate the short name
        if self.short_name is None:
            words = self.name.split()
            num_words = len(words)
            if num_words == 1:
                name = words[0][:3]
            elif num_words == 2:
                name = words[0][:2] + words[1][0]
            else:
                # get the first letter of the first 2 words, plus the first letter of the last word
                name = words[0][0] + words[1][0] + words[-1][0]

            self.short_name = name.upper()

        if len(self.short_name) != 3:
            raise ValueError("Card's short name must be exactly 3 characters")

        # register the card by it's short name, short names must be unique
        if self.short_name in Card.card_lookup:
            c = Card.card_lookup[self.short_name]
            raise ValueError(f"{c.name} already has short name {self.short_name}")
        Card.card_lookup[self.short_name] = self

        # update the name map
        name = self.name.upper()
        if name in Card.name_map:
            raise ValueError(f"{name} is already mapped to {Card.name_map[name]}")
        Card.name_map[name] = self.short_name
        Card.name_map[self.short_name] = self.short_name


@dataclass
class EtherealCard(Card):
    level: CardLevel = CardLevel.ETHEREAL
    price: int | None = 3
    crowns_purchase: bool = True


@dataclass
class LegendaryCard(Card):
    level: CardLevel = CardLevel.LEGENDARY
    price: int | None = None
    limit: int = 1
    power: int = 999


@dataclass
class Deck:
    """
    Create a deck from a dict of cards, or a string

    Parameters
    ----------
    source : dict[str, int] | str | None
        The cards to populate the deck with.

        If `source` is a string, it can be in 2 formats
        - <short name>x<count>
        - <short name>[+-]<count>
    allow_negative : bool
        If False, raise an error when initializing a deck with negative card counts.

    Example
    -------
    >>> Deck(source="STAx2")

    Creates a deck with 2 stability

    >>> Deck(source="TRH+1, SNE-1")

    Create a deck with 1 Treasure Hunter, and -1 Sneak
    """

    source: InitVar[dict[str, int] | str | None]
    cards: dict[str, int] = field(default_factory=dict, init=False)
    allow_negative: bool = False

    def __post_init__(self, source: dict[str, int] | str | None):
        if isinstance(source, str):
            # parse from string
            return self.from_str(source)
        # by default, the count of a card is 0
        self.cards = defaultdict(lambda: 0, source or {})

    @classmethod
    def from_str(cls, s: str) -> Self:
        """
        Parse a string to construct a Deck.

        Supports 3 different patterns:
        - Runs tab format: <short name>[x<count>]
        - Cards Acquired tab format: <short name>[(+-)<count>]
        - Card Stats sheet: [<count> ]<name>

        Parameters
        ----------
        s : str
            _description_

        Returns
        -------
        Deck
            _description_
        """
        runs_pattern = re.compile(r"(?P<name>[A-Z\d]{3})(?:x(?P<count>\d+))?$")
        cards_acquired_pattern = re.compile(r"(?P<name>[A-Z\d]{3})(?P<count>[+-]\d+)$")
        do_card_stats_pattern = re.compile(
            r"(?:(?P<count>\d*) )?(?P<name>[ A-Za-z']{4,})$"
        )

        for pattern in (runs_pattern, cards_acquired_pattern, do_card_stats_pattern):
            deck: dict[str, int] | None = {}
            for token in re.split(r",\w*", s):
                m = re.match(pattern, token)

                # all tokens should match on the same pattern
                if not m:
                    deck = None
                    break

                card_str = m["name"].upper()
                # ignore victory tomes
                if any(t in card_str for t in ("VICTORY TOME", "VT")):
                    continue
                s_name = Card.name_map[card_str]

                count = m["count"]
                if count:
                    count = int(count)
                else:
                    count = 1

                deck[s_name] = count

            # go to next pattern if did not match
            if deck is not None:
                return cls(deck)

        raise ValueError(f'Could not create a deck from "{s}"')

    @property
    def power(self) -> int:
        """The cumulative power of all the cards in a deck."""
        p = sum(
            Card.card_lookup[s_name].power * count
            for s_name, count in self.cards.items()
        )

        # apply penalty for small decks
        # I estimate that the minimum successful run is about 5 minutes,
        # and that cards are going to played every 30 seconds.
        # This means that at a minimum, we can expect 10 cards to be played over the
        # course of a successful run. Any deck less than 10 cards, means that the
        # remaining cards played will be stumbles, which add 2 clank to the deck.
        # Sneak blocks 2 clank, which means that a stumble effectively negates the effect
        # of sneak. The power of sneak is 7, therefore we subtract 7 for each card under
        # 10 that the deck is.
        if self.size < 10:
            penalty = 7 * (10 - self.size)
            p -= penalty

        # add 40 to normalize the base deck to be 0 power
        return p + 40

    @property
    def size(self) -> int:
        """The total number of cards in a deck."""
        return sum(c for c in self.cards.values())

    @property
    def efficiency(self) -> float:
        """The ratio of power to deck size."""
        return round(self.power / self.size, 2)

    @property
    def is_valid(self) -> bool:
        """Checks if each card is under the allowed amount."""
        for s_name, count in self.cards.items():
            cur_limit = Card.card_lookup[s_name].limit
            if cur_limit is not None and count > cur_limit:
                return False

        return True

    def __add__(self, __o):
        if isinstance(__o, Deck):
            new_cards = self.cards
            for s_name, count in __o.cards.items():
                new_cards[s_name] += count

            return Deck(new_cards)

        # add a single card
        if isinstance(__o, Card):
            return self + Deck({__o.short_name: 1}, allow_negative=True)

        # try constructing a deck from the input and adding it
        try:
            return self + Deck(__o, allow_negative=True)
        except Exception:
            return NotImplemented

    def __iadd__(self, __o):
        new_deck = self + __o
        self.cards = new_deck.cards
        return self

    def __str__(self) -> str:
        card_str = ",".join(f"{s_name}x{count}" for s_name, count in self.cards.items())
        return card_str
        # return str(dict(self.cards))

    def strip_ethereal_cards(self) -> "Deck":
        """Return a new Deck with all the ethereal cards removed."""
        # add all cards that aren't ethereal
        stripped_cards = {
            s_name: count
            for s_name, count in self.cards.items()
            if not isinstance(Card.card_lookup[s_name], EtherealCard)
        }

        return Deck(stripped_cards)


## Card Definitions ##
# common cards
Card("Sneak", CardLevel.COMMON, 7, limit=5)
Card("Stability", CardLevel.COMMON, 8, limit=5)
Card("Treasure Hunter", CardLevel.COMMON, 9, limit=5)
Card("Ember Seeker", CardLevel.COMMON, 10, limit=5)
moc_power = (
    6
    + Card.card_lookup["SNE"].power
    + Card.card_lookup["STA"].power
    + Card.card_lookup["TRH"].power
    + Card.card_lookup["EMS"].power
)
# power is 40
EtherealCard("Moment of Clarity", CardLevel.COMMON, 6, limit=None, power=moc_power)

# uncommon cards
Card("Evasion", CardLevel.UNCOMMON, 16)
Card("Tread Lightly", CardLevel.UNCOMMON, 18)
Card("Frost Focus", CardLevel.UNCOMMON, 20)
Card("Loot and Scoot", CardLevel.UNCOMMON, 20)
Card("Second Wind", CardLevel.UNCOMMON, 22)
Card("Beast Sense", CardLevel.UNCOMMON, 24)
Card("Bounding Strides", CardLevel.UNCOMMON, 26, short_name="BST")
Card("Reckless Charge", CardLevel.UNCOMMON, 28)
Card("Sprint", CardLevel.UNCOMMON, 30, short_name="SPT")
Card("Nimble Looting", CardLevel.UNCOMMON, 32)
Card("Smash and Grab", CardLevel.UNCOMMON, 34)
Card("Quickstep", CardLevel.UNCOMMON, 36)
Card("Suit Up", CardLevel.UNCOMMON, 38, limit=1, permanent=True)
Card("Adrenaline Rush", CardLevel.UNCOMMON, 40)

#  rare cards
Card("Eerie Silence", CardLevel.RARE, 46)
Card("Dungeon Repairs", CardLevel.RARE, 48)
Card("Swagger", CardLevel.RARE, 50)
Card("Chill Step", CardLevel.RARE, 52)
Card("Speed Runner", CardLevel.RARE, 54, permanent=True)
Card("Eyes on the Prize", CardLevel.RARE, 56)
Card("Haste", CardLevel.RARE, 60)
Card("Cold Snap", CardLevel.RARE, 62)
Card("Silent Runner", CardLevel.RARE, 64, permanent=True)
Card("Fuzzy Bunny Slippers", CardLevel.RARE, 66, permanent=True)
Card("Deepfrost", CardLevel.RARE, 68, short_name="DEF")
Card("Brilliance", CardLevel.RARE, 70)

# legendary cards
LegendaryCard("Avalanche")
LegendaryCard("Glorious Moment", permanent=True)
LegendaryCard("Beast Master", permanent=True)
LegendaryCard("Cash Cow")
LegendaryCard("Boots of Swiftness", permanent=True)

# ethereal cards
p2w_power = (Card.card_lookup["EMS"].power * 5) + 8  # power is 58
taa_power = Card.card_lookup["EVA"].power + Card.card_lookup["TRH"].power + 2
EtherealCard("Pay to Win", power=p2w_power, short_name="P2W")
EtherealCard("Tactical Approach", limit=None, power=taa_power, permanent=True)
EtherealCard("Porkchop Power", limit=None, permanent=True)
