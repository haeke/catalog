from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import User, Base, Catalog, Item

engine = create_engine('sqlite:///catalogwithusers.db')

DBSession = sessionmaker(bind=engine)

session = DBSession()

#create a test user

User1 = User(name="Edwin R.", id=1, email="234747@gmail.com")
session.add(User1)
session.commit()

#Catalog title
catalog1 = Catalog(user_id=1, name="Sports")
session.add(catalog1)
session.commit()

catalog2 = Catalog(user_id=2, name="Videogames")
session.add(catalog2)
session.commit()

catalog3 = Catalog(user_id=3, name="Movies")
session.add(catalog3)
session.commit()

catalog4 = Catalog(user_id=4, name="Television")
session.add(catalog4)
session.commit()

#item for catalog above
item1 = Item(name="Hockey", description="A game on ice with hockey sticks.", catalog=catalog1)
session.add(item1)
session.commit()

print "added catalog items"
