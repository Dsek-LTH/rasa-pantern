import asyncio

from db_handling.handler import DBHandler

if __name__ == "__main__":
    db = DBHandler("testing_db.sqlite")
    asyncio.run(db.create_tables())
    if not asyncio.run(db.get_drink_option_list(-1)) == []:
        print("drink list not empty testing might be fucked")

    asyncio.run(db.add_drink_option(-1, "testing_drink"))
    if not asyncio.run(db.get_drink_option_list(-1)) == ["testing_drink"]:
        print("add drink not working")

    try:
        asyncio.run(db.add_drink_option(-1, "testing_drink"))
    except ValueError:
        pass
    except Exception as e:
        print(
            f"Thing didn't error properly!\n\
            Expected ValueError, but instead got {e}"
        )

    asyncio.run(db.remove_drink_option(-1, "testing_drink"))
    if not asyncio.run(db.get_drink_option_list(-1)) == []:
        print("drink list not empty testing might be fucked")
