import pika
import os
import sys
import gradio as gr
from threading import Thread

from src.db.model import Team
from src.db.build import build, connect_db, set_state, get_state

if __name__ == '__main__':

    # get launch arguments
    arguments = sys.argv[1:]

    if len(arguments) < 1:
        print('Usage: python -m src.server.server <number of players>')
        sys.exit(1)

    # Number of players - this can be parameterized
    num_players = int(arguments[0])
    players = {"-" for i in range(num_players)}

    if '-b' in arguments:
        build(verbose=True)

    def get_players():
        """
        Get the list of players in the game.
        """
        engine, session = connect_db()
        teams = session.query(Team).all()
        session.close()
        engine.dispose()

        global players
        players = {team.name: team.answer for team in teams}

        return players

    def callback(ch, method, properties, body):

        # messages have the format team:answer
        # split the message into the team and the message
        team_name, answer = body.decode().split(':', 1)

        engine, session = connect_db()

        # get the team with the team name
        team = session.query(Team).filter_by(name=team_name).first()

        if team is None:
            print("Warning: received message from unknown team. Exiting callback...")
            return

        if team.answer != '':
            print(f"{team_name} sent a duplicate answer: {answer}. Discarding and exiting callback...")
            return

        # update the team's answer
        team.answer = answer

        # commit the changes
        session.commit()

        # close the database connection
        session.close()
        engine.dispose()

        print(f"Received {team_name}: {answer}")

    def consume_messages():
        # get the hostname, based on whether we're in docker or not
        docker_env = os.environ.get('IN_DOCKER', False)
        host = 'rabbitmq' if docker_env else 'localhost'

        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=5672))
        channel = connection.channel()
        channel.queue_declare(queue='game', durable=True)
        channel.basic_consume(queue='game', on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    def refresh_labels():
        """
        Fetch current players' answers and points from the database and return them.
        """
        engine, session = connect_db()

        # get all teams, ordered by name
        teams = session.query(Team).order_by(Team.name).all()

        session.close()
        engine.dispose()

        player_labels = [gr.Label(value="No Team connected") for i in range(num_players)]

        for i in range(num_players):

            if i >= len(teams):
                current_team = None
            else:
                current_team = teams[i]

            if current_team is not None:
                player_labels[i] = gr.Label(value=f"{current_team.name}: {current_team.answer} ({current_team.points})")

        return player_labels

    def update_score(team_name, increment):
        """
        Update the score of the given team by increment (can be 1 or -1).
        """
        engine, session = connect_db()

        # get the team with the team name
        team = session.query(Team).filter_by(name=team_name).first()

        if team:
            # Update the team's score
            team.points += increment
            # commit the changes
            session.commit()
            print(f"Updated {team_name} score to {team.points}")
        else:
            print(f"Team {team_name} not found")

        # close the database connection
        session.close()
        engine.dispose()


    def create_update_function(team_name, increment):
        """
        Create a closure that captures the team_index and increment.
        """
        def update_function():
            engine, session = connect_db()
            # Assuming the team names are "Team 1", "Team 2", etc.
            team = session.query(Team).filter_by(name=team_name).first()

            if team:
                # Update the team's score
                team.points += increment
                # commit the changes
                session.commit()
                print(f"Updated {team_name} score to {team.points}")
            else:
                print(f"Team {team_name} not found")

            # close the database connection
            session.close()
            engine.dispose()

            # Return the updated labels after modifying the score
            return None
        return update_function

    def clear_answers():

        # get all teams
        engine, session = connect_db()
        teams = session.query(Team).all()

        for team in teams:
            team.answer = ''

        session.commit()

        # close the database connection
        session.close()
        engine.dispose()
    
    def set_state_hide():
        set_state('hide')
    
    def set_state_show():
        set_state('show')

    Thread(target=consume_messages, daemon=True).start()

    player_labels = [None for i in range(num_players)]
    player_point_up = {}
    player_point_down = {}

    with gr.Blocks() as demo:
        with gr.Column():

            for i in range(num_players):
                with gr.Row():
                    with gr.Column(scale=10):
                        player_labels[i] = gr.Label(value=f"No Team connected")
                    with gr.Column(scale=1):
                        player_point_up[i] = gr.Button(value="+1")
                        player_point_down[i] = gr.Button(value="-1")

            # we need to do this in a separate loop because the buttons need to be created first
            # otherwise, the update functions will not be able to find the buttons
            for i in range(num_players):
                player_name = f"Team {i + 1}"

                # Get the update functions for increment and decrement
                increment_function = create_update_function(player_name, 1)
                decrement_function = create_update_function(player_name, -1)

                # Connect the buttons to their respective functions
                player_point_up[i].click(fn=increment_function, inputs=[], outputs=[])
                player_point_down[i].click(fn=decrement_function, inputs=[], outputs=[])

            with gr.Row():

                # Create a button for refreshing the player labels
                button_refresh = gr.Button(value="Refresh")
                button_next = gr.Button(value="Clear Answers")
                button_exit = gr.Button(value="Exit")

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_refresh.click(fn=refresh_labels, inputs=[], outputs=player_labels, every=0.5)
                button_next.click(fn=clear_answers, inputs=[], outputs=[])
                button_exit.click(fn=exit, inputs=[], outputs=[])
            
            with gr.Row():

                # Create a button for refreshing the player labels
                button_hide = gr.Button(value="Hide Answers")
                button_show = gr.Button(value="Show Answers")

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_hide.click(fn=set_state_hide, inputs=[], outputs=[])
                button_show.click(fn=set_state_show, inputs=[], outputs=[])

    demo.launch(server_name='0.0.0.0', server_port=7999, debug=True)