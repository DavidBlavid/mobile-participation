import pika
import os
import sys
import gradio as gr
from threading import Thread

from src.db.model import Team
from src.db.build import connect_db, get_state, set_state

if __name__ == '__main__':

    # get launch arguments
    arguments = sys.argv[1:]

    if len(arguments) < 1:
        print('Usage: python -m src.monitor.monitor <number of players>')
        sys.exit(1)

    # Number of players - this can be parameterized
    num_players = int(arguments[0])
    players = {"-" for i in range(num_players)}

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

    def refresh_labels():
        """
        Fetch current players' answers and points from the database and return them.
        """
        engine, session = connect_db()

        state = get_state()

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

                if state == 'hide':
                    player_labels[i] = gr.Label(value=f"{current_team.name}: ??? ({current_team.points})")
                elif state == 'show':
                    player_labels[i] = gr.Label(value=f"{current_team.name}: {current_team.answer} ({current_team.points})")

        return player_labels
    
    player_labels = [None for i in range(num_players)]

    with gr.Blocks() as demo:
        with gr.Column():

            for i in range(num_players):
                with gr.Row():
                    with gr.Column(scale=10):
                        player_labels[i] = gr.Label(value=f"No Team connected")

            with gr.Row():

                # Create a button for refreshing the player labels
                button_refresh = gr.Button(value="Refresh")

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_refresh.click(fn=refresh_labels, inputs=[], outputs=player_labels, every=0.5)
    
    print("Starting monitor on port 8000...")

    demo.launch(server_name='0.0.0.0', server_port=8000, debug=True)