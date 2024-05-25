from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
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
    phase = Column(String)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=True)
    video = relationship("Video", backref="state")

class Video(Base):
    """
    - author (str): name of the author of the video
    - source (str): source of the video (advert, show, song...)
    - question (str): question for the video
    - answer (str): correct answer to the video
    - link (str): youtube link to the video
    - filename (str): filename of the saved video
    """
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    author = Column(String)
    source = Column(String)
    question = Column(String)
    answer = Column(String)
    link = Column(String)
    show_video = Column(String)
    video_start = Column(Integer)
    video_end = Column(Integer)
    filename = Column(String)