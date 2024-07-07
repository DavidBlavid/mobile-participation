import pika
import os
import sys
import gradio as gr
from threading import Thread

from src.db.model import Team
from src.db.build import connect_db, get_phase, set_phase, get_video

VIDEO_DIR = "videos"

TEAM_COLORS = {
    1: "#b5100a",
    2: "#0d19ff",
    3: "#129a00",
    4: "#c46d00",
    5: "#7e15ff",
    6: "#00b2b5",
    7: "#000000",
    8: "#cd21bd",
}

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
        This returns a list of the labels that will be updated in the UI with the following order:
        - Last Question
        - Last Answer
        - Team Names
        - Team Correct/Incorrect Answers
        - Team Answers
        - Team Points
        - Team Rankings
        """
        engine, session = connect_db()

        phase = get_phase()

        # get the current video
        video = get_video()

        label_question = gr.HTML(value=f"<h1>{video.question}</h1>", show_label=False)
        label_answer = gr.HTML(value=f"<h1>{video.answer}</h1>", show_label=False)

        # get all teams, ordered by name
        teams = session.query(Team).order_by(Team.name).all()

        session.close()
        engine.dispose()
        
        # build round result labels
        labels_team_names = [None for i in range(num_players)]
        labels_correct_answers = [None for i in range(num_players)]
        labels_answers = [None for i in range(num_players)]
        labels_points = [None for i in range(num_players)]
        
        for i in range(num_players):

            if i >= len(teams):
                current_team = None
            else:
                current_team = teams[i]

            if current_team is not None:

                match current_team.correct:
                    case None:
                        string_correct = "❔"
                    case True:
                        string_correct = "✅"
                    case False:
                        string_correct = "❌"

                team_color = TEAM_COLORS[i+1]

                labels_team_names[i] = gr.Label(value=f"{current_team.name}", show_label=False, color=team_color)
                labels_correct_answers[i] = gr.Label(value=f"{string_correct}", show_label=False)
                labels_answers[i] = gr.Label(value=f"{current_team.answer}", show_label=False)
                labels_points[i] = gr.Label(value=f"{current_team.points}", show_label=False)
        
        # build ranking labels
        scores = {team.name: team.points for team in teams}

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        labels_ranking = [None for i in range(num_players)]

        for i in range(num_players):
            if i < len(sorted_scores):
                team_name, team_points = sorted_scores[i]

                team_number = team_name.split(" ")[1]
                team_color = TEAM_COLORS[int(team_number)]

                label_string = f"{team_name}  {team_points}"

                if i == 0:
                    label_string = f"🥇 {label_string}"
                elif i == 1:
                    label_string = f"🥈 {label_string}"
                elif i == 2:
                    label_string = f"🥉 {label_string}"
                else:
                    label_string = f"{label_string}"

                labels_ranking[i] = gr.Label(value=label_string, show_label=False, color=team_color)
        
        # combine the label lists
        all_labels = [label_question, label_answer] + labels_team_names + labels_correct_answers + labels_answers + labels_points + labels_ranking

        return all_labels
    
    def play_video_question():

        # get the game state
        video = get_video()
        video_filename = video.filename

        question_video_path = f'{VIDEO_DIR}/questions/{video_filename}.mp4'

        return question_video_path
    
    def play_video_answer():
            
        # get the game state
        video = get_video()
        video_filename = video.filename
    
        answer_video_path = f'{VIDEO_DIR}/answers/{video_filename}.mp4'
    
        return answer_video_path
    

    
    labels_team = [None for i in range(num_players)]
    labels_correct_answers = [None for i in range(num_players)]
    lables_answer = [None for i in range(num_players)]
    labels_points = [None for i in range(num_players)]

    labels_ranking = [None for i in range(num_players)]
    
    video = None

    css = """
    #label_team {padding: 0 !important; font-size: var(--text-xl) !important;}
    #label_points {padding: 0 !important; font-size: var(--text-xl) !important;}
    #label_answer {padding: 0 !important; font-size: var(--text-xl) !important;}
    .small_text .output-class {font-size: var(--text-xl) !important; padding: var(--size-3) var(--size-4) !important;}
    .left_margin {margin-left: 50px !important;}
    .no_padding {padding: 0 !important;}
    [data-testid="label-output-value"] {padding: 0 !important;}
    .center_text {text-align: center !important; min-height: 0 !important;}
    .prose .min {min-height: 0 !important;}
    .generating {border: 0 !important;}
    """

    with gr.Blocks(css=css) as demo:

        with gr.Tab(label = "Antworten"):

            label_question = gr.HTML(value="[FRAGE]", elem_classes=["center_text"])
            label_answer = gr.HTML(value="[ANTWORT]", elem_classes=["center_text"])

            with gr.Row():

                # the round results
                with gr.Column(scale=3):
                    for i in range(num_players):
                        with gr.Row():
                            labels_team[i] = gr.Label(value=f"Refresh teams...", show_label=False, elem_id=f"label_team", scale=1, elem_classes=["small_text, no_padding"])
                            labels_correct_answers[i] = gr.Label(value=f"⚠️", show_label=False, elem_id=f"label_correct_answer", scale=1, elem_classes=["no_padding"])
                            lables_answer[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_answer", scale=3, elem_classes=["small_text", "no_padding"])
                            labels_points[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_points", scale=2, elem_classes=["small_text", "no_padding"])
                
                # the ranking
                with gr.Column(scale=1, elem_classes=["left_margin"]):
                    for i in range(num_players):
                        with gr.Row():
                            labels_ranking[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_ranking", scale=1, elem_classes=["small_text", "no_padding"])
            
            # Create a button for refreshing the player labels
            button_refresh = gr.Button(value="Refresh")

            # create a list of all labels
            all_labels = [label_question, label_answer] + labels_team + labels_correct_answers + lables_answer + labels_points + labels_ranking

            # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
            button_refresh.click(fn=refresh_labels, inputs=[], outputs=all_labels, every=0.5)


        with gr.Tab(label = "Spiel"):
            with gr.Column():
                video = gr.Video(
                    height=720,
                    width=1280,
                    label="Video",
                    show_label=False,
                    interactive=True,
                    autoplay=True
                )
        
            with gr.Row():
                # buttons to play the question and answer videos
                button_play_question = gr.Button(value="▶️ Frage")
                button_play_answer = gr.Button(value="▶️ Antwort")

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_play_question.click(fn=lambda: play_video_question(), inputs=[], outputs=[video])
                button_play_answer.click(fn=lambda: play_video_answer(), inputs=[], outputs=[video])

    print("Starting monitor on port 8000...")

    demo.launch(server_name='0.0.0.0', server_port=8000, debug=True)