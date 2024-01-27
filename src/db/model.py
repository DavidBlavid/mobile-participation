from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Team(Base):
    """
    A team in the game
    - id (int): unique identifier
    - name (str): name of the team
    - points (int): number of points the team has
    - answer (str): the current answer the team has given
    """
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    points = Column(Integer)
    answer = Column(String)

class State(Base):
    __tablename__ = 'state'
    id = Column(Integer, primary_key=True)
    state = Column(String)