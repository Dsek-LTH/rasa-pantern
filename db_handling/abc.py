from abc import ABC, abstractmethod


class Database(ABC):
    @abstractmethod
    async def execute_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> None:
        """Execute a query in the database.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.
        """
        ...

    @abstractmethod
    async def execute_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> dict[str, str | int] | None:
        """Execute a query in the database and parses the first found entry
        into a dictionary.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.

        Returns:
            dict: Key value pairs with data from the query results.
                  form: {field_name: value}
        """
        ...

    @abstractmethod
    async def execute_multiple_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> list[dict[str, str | int]] | None:
        """Execute a query in the database and parses all found entries into
        a list of dictionaries.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.

        Returns:
            list[dict]: list of key value pairs with data from the query
                        results. form: [{field_name: value}]
        """
