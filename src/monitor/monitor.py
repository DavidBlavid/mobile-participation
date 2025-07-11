import pika
import os
import sys
import gradio as gr
from threading import Thread

from src.db.model import Team, State
from src.db.build import connect_db, get_phase, set_phase, get_video

USE_AUTH = True                         # if True, requires authentication to access the server
AUTH_CREDENTIALS = ('admin', 'admin')   # credentials for authentication

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

def answer_to_emoji(answer) -> str:
    if answer == None or answer == '':
        return "❌"
    elif answer == "perfect":
        return "⭐"
    elif answer == "correct":
        return "✅"
    elif answer == "incorrect":
        return "❌"
    elif answer == "late":
        return "⏰"
    else:
        return "❗️"

def get_selected_years():
    """
    Get the selected years from the current state.
    """
    engine, session = connect_db()

    # get the current state
    current_state = session.query(State).first()

    if current_state is None:
        print("[state] No current state found")
        session.close()
        engine.dispose()
        return []

    if current_state.selected_years is None:
        # print("No selected years found")
        return []

    # split the selected years by comma and return them as a list
    selected_years = current_state.selected_years.split(',')

    # sort the years
    selected_years = sorted([int(year.strip()) for year in selected_years if year.strip().isdigit()])

    session.close()
    engine.dispose()

    return selected_years

if __name__ == '__main__':

    # get launch arguments
    arguments = sys.argv[1:]

    if len(arguments) < 1:
        print('Usage: python -m src.monitor.monitor <number of players>')
        sys.exit(1)

    # Number of players - this can be parameterized
    num_players = int(arguments[0])
    players = {"-" for i in range(num_players)}

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

        phase = get_phase()     # either 'show' or 'hide'
        is_show = (phase == 'show')

        # get the current video
        video = get_video()

        question_1 = video.question_1
        question_2 = video.question_2



        if question_1 is None or question_1 == '-' or question_1 == '':
            label_question_1 = gr.HTML(value="<h1>-</h1>", show_label=False, visible=False)
            label_answer_1 = gr.HTML(value=f"<h1>{video.answer_1}</h1>", show_label=False)
        else:
            label_question_1 = gr.HTML(value=f"<h1><b>Frage 1: {video.question_1}</b></h1>", show_label=False, visible=True)
            label_answer_1 = gr.HTML(value=f"<h1>{video.answer_1}</h1>", show_label=False, visible=is_show)

        if question_2 is None or question_2 == '-' or question_2 == '':
            label_question_2 = gr.HTML(value="<h1>-</h1>", show_label=False, visible=False)
            label_answer_2 = gr.HTML(value=f"<h1>{video.answer_2}</h1>", show_label=False)
        else:
            label_question_2 = gr.HTML(value=f"<h1><b>Frage 2: {video.question_2}</b></h1>", show_label=False, visible=True)
            label_answer_2 = gr.HTML(value=f"<h1>{video.answer_2}</h1>", show_label=False, visible=is_show)

        # True if there is a question 2
        q2_exists = (video.question_2 is not None) and (not video.question_2 == '-') and (not video.question_2 == '')

        # get all teams, ordered by name
        teams = session.query(Team).order_by(Team.name).all()

        session.close()
        engine.dispose()
        
        # build round result labels
        labels_team_names = [None for i in range(num_players)]
        labels_points     = [None for i in range(num_players)]
        labels_answers_1  = [None for i in range(num_players)]
        labels_answers_2  = [None for i in range(num_players)]
        
        for i in range(num_players):

            if i >= len(teams):
                current_team = None
            else:
                current_team = teams[i]

            if current_team is not None:

                string_correct_1 = answer_to_emoji(current_team.correct_1)
                string_correct_2 = answer_to_emoji(current_team.correct_2)

                team_color = TEAM_COLORS[i+1]

                if is_show:
                    text_answer_1 = f"{current_team.answer_1} {string_correct_1}"
                    text_answer_2 = f"{current_team.answer_2} {string_correct_2}"
                else:
                    text_answer_1 = f"{current_team.answer_1}  "
                    text_answer_2 = f"{current_team.answer_2}  "
                
                labels_team_names[i] = gr.Label(value=f"{current_team.name}", show_label=False, color=team_color)
                labels_answers_1[i] = gr.Label(value=text_answer_1, show_label=False)

                if q2_exists:
                    labels_answers_2[i] = gr.Label(value=text_answer_2, show_label=False, visible=True)
                else:
                    labels_answers_2[i] = gr.Label(value="-", show_label=False, visible=False)
                
                labels_points[i] = gr.Label(value=f"{current_team.points}", show_label=False, visible=is_show)
        
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

                labels_ranking[i] = gr.Label(value=label_string, show_label=False, color=team_color, visible=is_show)
        
        # combine the label lists
        all_labels = [label_question_1, label_answer_1, label_question_2, label_answer_2] + labels_team_names + labels_answers_1 + labels_answers_2 + labels_points + labels_ranking

        return all_labels
    
    def refresh_labels_vid():
        """
        Fetch the current video questions and answers from the database and return them.
        This returns a list of the labels that will be updated in the UI with the following order:
        - Video Question 1
        - Video Question 2
        """
        engine, session = connect_db()

        # get the current video
        video = get_video()

        if video.question_1 is None or video.question_1 == '-' or video.question_1 == '':
            label_vid_question_1 = gr.HTML(value="<h1>-</h1>", show_label=False, visible=False)
        else:
            label_vid_question_1 = gr.HTML(value=f"<h1>Frage 1: {video.question_1}</h1>", show_label=False, visible=True)

        if video.question_2 is None or video.question_2 == '-' or video.question_2 == '':
            label_vid_question_2 = gr.HTML(value="<h1>-</h1>", show_label=False, visible=False)
        else:
            label_vid_question_2 = gr.HTML(value=f"<h1>Frage 2: {video.question_2}</h1>", show_label=False, visible=True)

        session.close()
        engine.dispose()

        return [label_vid_question_1, label_vid_question_2]

    def refresh_years():
        years = set(get_selected_years())
        H_BG, N_BG, C_BG = "#bfa43a", "#cccccc", "#ffcc25"

        # get the current video
        video = get_video()
        if video.answer_1 is not None and video.answer_1 != '':
            video_year = int(video.answer_1)
            years.add(video_year)
        else:
            video_year = None
        
        is_show = get_phase() == 'show'

        update_list = []

        for i in range(7 * 10):
            year = 1960 + i
            if year > 2019:
                break
            elem_id = "year_" + str(year)

            is_current_year = (year == video_year)
            is_highlighted_year = (year in years)

            if is_current_year and is_show:
                color = C_BG
            elif is_highlighted_year and not (not is_show and is_current_year):
                color = H_BG
            else:
                color = N_BG

            update_list.append(gr.update(
                elem_id=elem_id,
                color=color,
            ))

        return update_list

    def play_video():

        # get the game state
        video = get_video()
        video_filename = video.filename

        video_path = f'{VIDEO_DIR}/clips/{video_filename}.mp4'

        return video_path
    
    labels_team = [None for i in range(num_players)]
    lables_answer_1 = [None for i in range(num_players)]
    labels_answer_2 = [None for i in range(num_players)]
    labels_points = [None for i in range(num_players)]

    labels_ranking = [None for i in range(num_players)]
    
    video = None

    css = """
    #label_team {padding: 0 !important; font-size: var(--text-xl) !important;}
    #label_points {padding: 0 !important; font-size: var(--text-xl) !important;}
    #label_answer {padding: 0 !important; font-size: var(--text-xl) !important;}
    .small_text .output-class {font-size: 20pt !important; padding: var(--size-1) var(--size-2) !important;}
    .big_text .output-class {font-size: 35pt !important}
    .left_margin {margin-left: 50px !important;}
    .no_padding {padding: 0 !important;}
    [data-testid="label-output-value"] {padding: 0 !important;}
    .center_text {text-align: center !important; min-height: 0 !important;}
    .prose .min {min-height: 0 !important;}
    .generating {border: 0 !important;}
    .invisible {visibility: hidden !important;}
    .default {
    background-color: #ccc !important;
    font-weight: normal !important;
    }

    .default [data-testid="label-output-value"],
    .default[data-testid="label-output-value"] {
    color: #000 !important;
    padding: 0 !important;
    }

    .highlight {
    background-color: rgb(191, 164, 58) !important;
    font-weight: bold !important;
    }

    .highlight [data-testid="label-output-value"],
    .highlight[data-testid="label-output-value"] {
    color: #000 !important;
    }

    /* kill wrapper padding */
    .container.svelte-1l15rn0,
    .block.big_text.default.svelte-au1olv > .svelte-1l15rn0 {      /* fallback */
        padding: 0 !important;
    }

    /* give the space back to the innermost child */
    .container.svelte-1l15rn0 > .output-class,
    .block.big_text.default.svelte-au1olv > .svelte-1l15rn0 > .output-class {
        padding: var(--size-1) var(--size-2) !important;            /* same gap you used elsewhere */
        font-weight: 700;                                           /* keeps the highlight look */
    }

    #year_grid {
        display: grid !important;
        grid-template-columns: repeat(10, 1fr) !important;
        gap: var(--size-2) !important;
    }
    #year_grid .output-class {
        min-width: 0 !important;          /* prevents wrap */
        text-align: center !important;
        padding: var(--size-2) !important;
    }

    """

    with gr.Blocks(css=css) as demo:

        with gr.Tab(label = "Video"):

            label_vid_question_1 = gr.HTML(value="[FRAGE 1]", elem_classes=["center_text"])
            label_vid_question_2 = gr.HTML(value="[FRAGE 2]", elem_classes=["center_text"])

            timer_vid_question = gr.Timer(5)  # periodic trigger
            timer_vid_question.tick(
                fn=lambda: refresh_labels_vid(),
                inputs=[],
                outputs=[label_vid_question_1, label_vid_question_2],
                show_progress="hidden",
            )

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
                # play the video
                button_play = gr.Button(value="▶️ Play")

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_play.click(fn=lambda: play_video(), inputs=[], outputs=[video])
        
        with gr.Tab(label = "Antworten"):

            label_question_1 = gr.HTML(value="", elem_classes=["center_text"])
            label_answer_1 = gr.HTML(value="", elem_classes=["center_text"])

            label_question_2 = gr.HTML(value="", elem_classes=["center_text"])
            label_answer_2 = gr.HTML(value="", elem_classes=["center_text"])

            with gr.Row():

                # the round results
                with gr.Column(scale=3):
                    for i in range(num_players):
                        with gr.Row():
                            labels_team[i]     = gr.Label(value=f"Refresh teams...", show_label=False, elem_id=f"label_team", scale=1, elem_classes=["small_text, no_padding"])
                            lables_answer_1[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_answer", scale=3, elem_classes=["small_text", "no_padding"])
                            labels_answer_2[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_answer", scale=3, elem_classes=["small_text", "no_padding"])
                            labels_points[i]   = gr.Label(value=f"-", show_label=False, elem_id=f"label_points", scale=2, elem_classes=["small_text", "no_padding"])
                
                # the ranking
                with gr.Column(scale=1, elem_classes=["left_margin"]):
                    for i in range(num_players):
                        with gr.Row():
                            labels_ranking[i] = gr.Label(value=f"-", show_label=False, elem_id=f"label_ranking", scale=1, elem_classes=["small_text", "no_padding"])
            
            # Create a button for refreshing the player labels
            button_refresh = gr.Button(value="Refresh")

            # create a list of all labels
            all_labels = [label_question_1, label_answer_1, label_question_2, label_answer_2] + labels_team + lables_answer_1 + labels_answer_2 + labels_points + labels_ranking

            # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
            button_refresh.click(fn=refresh_labels, inputs=[], outputs=all_labels, show_progress="hidden")

            timer_refresh = gr.Timer(5)
            timer_refresh.tick(
                fn=refresh_labels,
                inputs=[],
                outputs=all_labels,
                show_progress="hidden",
            )
        
        year_labels = []
        with gr.Tab(label = "Jahre"):

            # here we show the years from 1950 to 2020 in a 10x7 grid
            with gr.Row(elem_id="year_grid"):           # single grid container
                for year in range(1960, 2020):
                    year_labels.append(
                        gr.Label(
                            value=str(year),
                            elem_id=f"year_{year}",
                            elem_classes=["big_text", "default"],
                            show_label=False,
                        )
                    )
            # timer to refresh the label highlights
            timer_year = gr.Timer(1)
            timer_year.tick(
                fn=refresh_years,
                inputs=[],
                outputs=year_labels,
                show_progress="hidden",
            )

    print("Starting monitor on port 8000...")

    demo.launch(
        server_name='0.0.0.0',
        server_port=8000,
        debug=True,
        auth=AUTH_CREDENTIALS if USE_AUTH else None,
    )