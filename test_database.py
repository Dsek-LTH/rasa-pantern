import asyncio

from db_handler import DBHandler

if __name__ == "__main__":
    db = DBHandler("testing_db.sqlite")
    asyncio.run(db._create_tables())
    if not asyncio.run(db.get_drink_list(-1)) == []:
        print("drink list not empty testing might be fucked")

    asyncio.run(db.add_drink(-1, "testing_drink"))
    if not asyncio.run(db.get_drink_list(-1)) == ["testing_drink"]:
        print("add drink not working")

    asyncio.run(db.add_drink(-1, "testing_drink"))
    # TODO: This should give an error / warning

    asyncio.run(db.remove_drink(-1, "testing_drink"))
    if not asyncio.run(db.get_drink_list(-1)) == []:
        print("drink list not empty testing might be fucked")
