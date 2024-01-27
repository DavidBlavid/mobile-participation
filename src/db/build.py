from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from src.db.model import Base, Team, State

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
    set_state('hide')
    if verbose: print("Done!")

    # close the database connection
    session.close()
    engine.dispose()

    if verbose: print("=========================")
    if verbose: print("Database rebuild finished")
    if verbose: print("=========================")

def set_state(state):
    """
    Set the state of the game.
    """
    # connect to the database
    engine, session = connect_db()

    # get the state
    current_state = session.query(State).first()

    if current_state is None:
        # create a new state
        current_state = State(state=state)
        # add the state to the database
        session.add(current_state)
    else:
        # update the state
        current_state.state = state

    # commit the changes
    session.commit()

    # close the database connection
    session.close()
    engine.dispose()

def get_state():
    """
    Get the state of the game.
    """
    # connect to the database
    engine, session = connect_db()

    # get the state
    current_state = session.query(State).first()
    state = current_state.state

    # close the database connection
    session.close()
    engine.dispose()

    return state

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