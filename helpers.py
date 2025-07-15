class TallyCount:
    def __init__(
        self, message_id: int, drunk_drinks: dict[str, list[int]] | None = None
    ) -> None:
        self._total_count = 0
        self._message_id: int = message_id
        self._drinks: dict[str, list[int]] = {}
        if drunk_drinks:
            self.set_drinks(drunk_drinks)

    @property
    def total_count(self) -> int:
        """The total amount of drinks drunk."""
        return self._total_count

    @property
    def drinks(self) -> dict[str, list[int]]:
        """
        Dict mapping the amount of drinks to the people who drank them.
        """
        return self._drinks

    @property
    def count(self) -> dict[str, int]:
        """
        A dict mapping the name of a drink to how many have been consumed.
        """
        count = {}
        for drink_name in self._drinks:
            count[drink_name] = len(self._drinks[drink_name])
        return count

    @property
    def message_id(self) -> int:
        """Message id of the tally that owns this data."""
        return self._message_id

    def set_drinks(self, drunk_drinks: dict[str, list[int]]) -> None:
        """
        Sets all fields of this object a list of drinks and who drank them.

        takes the drinks in drunk_drinks and counts how many times each was
        drunken, putting the values into this.total_count and this.drinks.

        Args:
            drunk_drinks (dict[str, list[int]]):
                    A dict on the form {drink_name: [<userId 1>, <userId 2>]}.
        """
        self._count = {}
        for drink_name in drunk_drinks.keys():
            self._total_count += len(drunk_drinks[drink_name])
            self._drinks[drink_name] = drunk_drinks[drink_name]
