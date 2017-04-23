from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable = False)
    picture = Column(String(250))

class Catalog(Base):
    __tablename__ = 'catalog'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    #describe relationship with User
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    #describe relationship with Item

    @property
    def serialize(self):
        """"format for object data that is serilizable"""
        return {
            'name': self.name,
            'id': self.id,
        }

class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    #relationship with catalog
    catalog_id = Column(Integer, ForeignKey('catalog.id'))
    catalog = relationship(Catalog)

    @property
    def serialize(self):
        """return a seriliazble object """
        return {
            'name': self.name,
            'description': self.description,
            'item_id': self.id,
            'user_id': self.user_id,
            'user': self.user,
            'catalog_id': self.catalog_id,
        }

engine = create_engine('sqlite:///catalogwithusers.db')

Base.metadata.create_all(engine)
