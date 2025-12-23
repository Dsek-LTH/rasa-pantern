# Råsa Pantern

Managed by UV

## Running standalone

1. Fill in example.env file and rename to .env

2. Set up database with:

    ```sh
    export DB_FILE=./db.sqlite
    uv run db_handler.py
    ```

3. Run with `uv run main.py`

## Running with podman/docker

1. Set up database like in standalone:

    ```sh
    export DB_FILE=./db.sqlite
    uv run db_handler.py
    ```

2. Make sure your db.sqlite file has the proper read and write permissions
   (group 1000 in the container)

   ```sh
   podman unshare chown 1000:1000 -R ./db
   ```

3. Bind mount db.sqlite into a reasonable directory (like /app/db.sqlite).

4. Run with evironment variables DB_FILE set to the binded location,
   and TOKEN set to your discord token.

example:

```sh
podman run -it -e DB_FILE="/app/sqlite" \
               -e TOKEN="<your token here>" \
               -v ./db:/app/db\
               rasa-pantern
```
