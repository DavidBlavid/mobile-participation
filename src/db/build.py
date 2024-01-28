from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from src.db.model import Base, Team, State, Video

def build(verbose=False):
    """
    This function is called when the script is run from the command line.
    """
    if verbose: print("=========================")
    if verbose: print(" Rebuilding the database")
    if verbose: print("=========================")

    # connect to the database
    if verbose: print("Connecting to the database... ", end='')
    engine, session = connect_db()
    if verbose: print("Done!")

    # force drop all tables
    if verbose: print("Dropping existing tables... ", end='')
    Base.metadata.drop_all(engine)
    if verbose: print("Done!")

    # create the tables
    if verbose: print("Creating tables... ", end='')
    Base.metadata.create_all(engine)
    if verbose: print("Done!")

    # set the base state
    if verbose: print("Setting the base state... ", end='')
    set_phase('hide')
    if verbose: print("Done!")

    # close the database connection
    session.close()
    engine.dispose()

    if verbose: print("=========================")
    if verbose: print("Database rebuild finished")
    if verbose: print("=========================")

def set_phase(phase):
    """
    Set the phase of the game.
    """
    # connect to the database
    engine, session = connect_db()

    # get the state
    current_state = session.query(State).first()

    if current_state is None:
        # create a new state
        current_state = State(phase=phase, video_id=None)
        # add the state to the database
        session.add(current_state)
    else:
        # update the state
        current_state.phase = phase

    # commit the changes
    session.commit()

    # close the database connection
    session.close()
    engine.dispose()

def get_phase():
    """
    Get the state of the game.
    """
    # connect to the database
    engine, session = connect_db()

    # get the state
    current_state = session.query(State).first()
    phase = current_state.phase

    # close the database connection
    session.close()
    engine.dispose()

    return phase

def get_video() -> Video:
    """
    Get the current video.
    """
    # connect to the database
    engine, session = connect_db()

    # get the state
    current_state = session.query(State).first()
    video = current_state.video

    # close the database connection
    session.close()
    engine.dispose()

    return video

def connect_db(host="postgres", port=5432, user="postgres", password="postgres", echo=False):
    """
    Connect to the database. This function builds the database connection string and returns an engine and a session.

    returns ```(engine, session)```
    - `engine` [Engine] SQLAlchemy engine
    - `session` [Session] SQLAlchemy session
    """

    docker_env = os.environ.get('IN_DOCKER', False)
    host = 'rabbitmq' if docker_env else 'localhost'

    db_string = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    engine = create_engine(db_string, echo=echo)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    return (engine, session)

if __name__ == '__main__':
    build(verbose=True)