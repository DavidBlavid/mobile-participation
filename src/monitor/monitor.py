import pika
import os
import sys
import gradio as gr
from threading import Thread

from src.db.model import Team
from src.db.build import connect_db, get_phase, set_phase, get_video

VIDEO_DIR = "videos"

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
        If there are n players, this returns 3n labels:
        `[team1, team2, ..., teamn, points1, points2, ..., pointsn, answer1, answer2, ..., answern]
        """
        engine, session = connect_db()

        phase = get_phase()

        # get all teams, ordered by name
        teams = session.query(Team).order_by(Team.name).all()

        session.close()
        engine.dispose()
        
        labels = [gr.Label(value="-", show_label=False) for i in range(num_players * 3)]

        for i in range(num_players):

            if i >= len(teams):
                current_team = None
            else:
                current_team = teams[i]

            if current_team is not None:

                labels[i] = gr.Label(value=f"{current_team.name}", show_label=False)
                labels[i + num_players] = gr.Label(value=f"{current_team.points} Punkte", show_label=False)

                if phase == 'hide':
                    labels[i + 2 * num_players] = gr.Label(value=f"???", show_label=False)
                elif phase == 'show':
                    if current_team.answer is None or current_team.answer == "":
                        labels[i + 2 * num_players] = gr.Label(value=f"-", show_label=False)
                    else:
                        labels[i + 2 * num_players] = gr.Label(value=f"{current_team.answer}", show_label=False)

        return labels
    
    def play_video():

        # get the game state
        video = get_video()
        video_filename = video.filename

        file_path = f'{VIDEO_DIR}/clips/{video_filename}.mp4'

        return file_path
    
    labels_team = [None for i in range(num_players)]
    labels_points = [None for i in range(num_players)]
    lables_answer = [None for i in range(num_players)]

    video = None

    css = """
    #label_team {padding: 0 !important; font-size: var(--text-xl) !important;}
    #label_points {padding: 0 !important; font-size: var(--text-xl) !important;}
    #label_answer {padding: 0 !important; font-size: var(--text-xl) !important;}
    .small_text .output-class {font-size: var(--text-xl) !important; padding: var(--size-3) var(--size-4) !important;}
    """

    with gr.Blocks(css=css) as demo:

        with gr.Row():
            with gr.Column(scale=2):
                for i in range(num_players):
                    with gr.Row():
                        labels_team[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_team", scale=1, elem_classes=["small_text"])
                        labels_points[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_points", scale=1, elem_classes=["small_text"])
                        lables_answer[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_answer", scale=3, elem_classes=["small_text"])

            with gr.Column(scale=3):
                video = gr.Video(
                    height=800,
                    width=800,
                    label="Video",
                    show_label=False,
                    interactive=False,
                    autoplay=True
                )
        
        with gr.Row():
            # Create a button for refreshing the player labels
            button_refresh = gr.Button(value="Refresh")

            # buttons to play 2s, 5s or 10s
            button_play = gr.Button(value="Play")

            # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
            button_play.click(fn=lambda: play_video(), inputs=[], outputs=[video])

            # create a list of all labels
            all_labels = labels_team + labels_points + lables_answer

            # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
            button_refresh.click(fn=refresh_labels, inputs=[], outputs=all_labels, every=0.5)
    
    print("Starting monitor on port 8000...")

    demo.launch(server_name='0.0.0.0', server_port=8000, debug=True)