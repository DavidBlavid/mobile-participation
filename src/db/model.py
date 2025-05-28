from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Team(Base):
    """
    A team in the game
    - id (int): unique identifier
    - name (str): name of the team
    - points (int): number of points the team has
    - answer_1 (str): answer to question 1
    - answer_2 (str): answer to question 2
    - correct_1 (bool): True if answer to question 1 is correct
    - correct_2 (bool): True if answer to question 2 is correct
    """
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    points = Column(Integer)
    answer_1 = Column(String, nullable=True)
    answer_2 = Column(String, nullable=True)
    correct_1 = Column(Boolean, nullable=True)
    correct_2 = Column(Boolean, nullable=True)

class State(Base):
    __tablename__ = 'state'
    id = Column(Integer, primary_key=True)
    phase = Column(String)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=True)
    video = relationship("Video", backref="state")

class Video(Base):
    """
    - title (str): title of the media
    - author (str): name of the author of the media
    - question_1 (str): question 1 for the media
    - answer_1 (str): answer for question_1
    - question_2 (str): question 2 for the media
    - answer_2 (str): answer for question_2
    - link (str): youtube link to the video
    - video_start (str): start time of the video
    - video_end (str): end time of the video
    - filename (str): filename of the saved video
    """
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    author = Column(String)
    question_1 = Column(String)
    answer_1 = Column(String)
    question_2 = Column(String)
    answer_2 = Column(String)
    link = Column(String)
    video_start = Column(String)
    video_end = Column(String)
    filename = Column(String)