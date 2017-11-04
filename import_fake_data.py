from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catagory, CatagoryItem, User

engine = create_engine('sqlite:///Catagory.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

picture = "https://lh3.googleusercontent.com/-XdUIqdMkCWA/AAAAAAAAAAI/AAAAAAAAAAA/4252rscbv5M/photo.jpg"

user1 = User(name="Wei", email="engineer@gmai.com", picture = picture)
session.add(user1)
session.commit()

user2 = User(name="Jun", email="coder@gmai.com", picture = picture)
session.add(user2)
session.commit()



shop1 = Catagory(name="Lego Shop",description = "First shop", user_id = user1.id )
session.add(shop1)
session.commit()

shop2 = Catagory(name="SuperHero Shop",description = "Second shop", user_id = user2.id )
session.add(shop2)
session.commit()


Catagory1 = CatagoryItem(name="Lego 1 ",description = "plastic Catagorys.", user_id = user1.id, price = "11", shop_id = shop1.id)
session.add(Catagory1)
session.commit()

Catagory2 = CatagoryItem(name="Lego 2 ",description = "plastic Catagorys.", user_id = user1.id, price = "33", shop_id = shop1.id)
session.add(Catagory2)
session.commit()

Catagory3 = CatagoryItem(name="Superman",description = "1st super hero.", user_id = user2.id, price = "22", shop_id = shop2.id)
session.add(Catagory3)
session.commit()

Catagory4 = CatagoryItem(name="Spiderman",description = "2rd super hero.", user_id = user2.id, price = "33", shop_id = shop2.id)
session.add(Catagory4)
session.commit()
