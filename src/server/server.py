import pika
import os
import sys
import gradio as gr
import random
from threading import Thread

from src.db.model import Team, Video, State
from src.db.build import build, connect_db, set_phase, get_phase, get_video

START_VIDEO_INDEX = 13                  # index of the first video to show. set to 13 for day 2

POINTS_ON_CORRECT_ANSWER_1 = 10         # points for a correct answer to question 1
POINTS_ON_PERFECT_ANSWER_1 = 10         # additional points for a perfect answer to question 1
POINTS_ON_CORRECT_ANSWER_2 = 10         # points for a correct answer to question 2

ACCEPT_LATE_ANSWERS = False             # if False, does not accept answers during the show phase
ACCEPT_REDO_EMPTY_ANSWERS = True        # if True, allows teams to redo their answers if they have accidentally sent an empty answer

RESET_PHASE_ON_NEXT_VIDEO = True        # if True, resets the phase to 'hide' when the next video is shown

USE_AUTH = True                         # if True, requires authentication to access the server
AUTH_CREDENTIALS = ('admin', 'admin')   # credentials for authentication

def answer_to_emoji(answer) -> str:
    if answer == None or answer == '':
        return "❔"
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

if __name__ == '__main__':

    # get launch arguments
    arguments = sys.argv[1:]

    if len(arguments) < 1:
        print('Usage: python -m src.server.server <number of players>')
        sys.exit(1)

    # Number of players - this can be parameterized
    num_players = int(arguments[0])
    players = {"-" for i in range(num_players)}

    # rebuild
    if '-b' in arguments:
        build(verbose=True)
    
    # reset the game state
    if '-r' in arguments:
        engine, session = connect_db()

        # get the state
        current_state = session.query(State).first()

        if current_state is None:
            print("[state] No current state found. Creating a new state...")
            current_state = State(phase='hide', selected_years=None, video_id=START_VIDEO_INDEX)
            session.add(current_state)

        current_state.phase = 'hide'
        current_state.selected_years = None
        current_state.video_id = START_VIDEO_INDEX

        print(f"> Resetting phase to 'hide' and selected years to None...")

        # reset all team scores to 0
        teams = session.query(Team).all()

        for team in teams:
            team.points = 0
            team.answer_1 = ''
            team.answer_2 = ''
            team.correct_1 = ''
            team.correct_2 = ''

        print(f"> Resetting all teams' scores to 0 and answers to empty...")

        # commit and close
        session.commit()
        session.close()
        engine.dispose()

        print("> Done!")

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
        team_name, answer_1, answer_2 = body.decode().split('§')

        engine, session = connect_db()

        # get the team with the team name
        team = session.query(Team).filter_by(name=team_name).first()

        if team is None:
            print(f"[msg:{team_name}] Team {team_name} not found. Exiting callback...")
            session.close()
            engine.dispose()
            return False

        if ACCEPT_REDO_EMPTY_ANSWERS and (answer_1 == '' or answer_2 == ''):
            # if the team has already sent an answer, we do not accept empty answers
            if team.answer_1 != '' or team.answer_2 != '':
                print(f"[msg:{team_name}] sent empty answer. Exiting callback...")
                session.close()
                engine.dispose()
                return False        

        if get_phase() == 'show' and not ACCEPT_LATE_ANSWERS:
            print(f"[msg:{team_name}] sent late answer. Exiting callback...")
            team.correct_1 = "late"
            team.correct_2 = "late"
            session.commit()
            session.close()
            engine.dispose()
            return False
        
        # update the team's answer
        team.answer_1 = answer_1
        team.answer_2 = answer_2

        # calculate the points based on the answers
        # try to convert answer_1 to an integer
        # remove all non-numeric characters from answer_1
        answer_1 = ''.join(filter(str.isdigit, answer_1))
        answer_1 = int(answer_1) if answer_1 else None

        # get the current video
        video = get_video()
        if video is None:
            print("[video] No current video found. Exiting callback...")
            session.close()
            engine.dispose()
            return False
        
        # get the year of the video
        if video.answer_1 is None or video.answer_1 == '':
            print("[video] No answer_1 found for the video. Exiting callback...")
            session.close()
            engine.dispose()
            return False
        
        video_year = int(video.answer_1)

        # get the range of correct years
        # the correct year is the next smaller year to next larger year compared to the year of the video
        # you get the selected years from the current state
        selected_years = get_selected_years()

        min_year = 1960
        max_year = 2019

        # find the next smaller and next larger year
        next_smaller_year = None
        next_larger_year = None

        for year in selected_years:
            if year < video_year:
                if next_smaller_year is None or year > next_smaller_year:
                    next_smaller_year = year
            elif year > video_year:
                if next_larger_year is None or year < next_larger_year:
                    next_larger_year = year
        
        next_smaller_year = next_smaller_year if next_smaller_year is not None else min_year
        next_larger_year = next_larger_year if next_larger_year is not None else max_year

        # check if the answer is correct
        if answer_1 is not None and answer_1 == video_year:
            team.correct_1 = "perfect"
            team.points += POINTS_ON_PERFECT_ANSWER_1

            emoji = answer_to_emoji(team.correct_1)
            print(f"[msg:{team_name}] {emoji} answered perfectly for question 1: {answer_1}")
        
        elif answer_1 is not None and next_smaller_year <= answer_1 <= next_larger_year:
            team.correct_1 = "correct"
            team.points += POINTS_ON_CORRECT_ANSWER_1
            print(f"[msg:{team_name}] {team.correct_1} answered correctly for question 1: {answer_1}")
        
        else:
            team.correct_1 = "incorrect"
            print(f"[msg:{team_name}] {team.correct_1} answered incorrectly for question 1: {answer_1}")

        # commit the changes
        session.commit()

        # close the database connection
        session.close()
        engine.dispose()

        return True
    
    def get_selected_years():
        """
        Get the selected years from the current state.
        """
        engine, session = connect_db()

        # get the current state
        current_state = session.query(State).first()

        if current_state is None:
            print("[years] No current state found")
            session.close()
            engine.dispose()
            return []

        if current_state.selected_years is None:
            # print("[state] No selected years found") # quite spammy
            session.close()
            engine.dispose()
            return []

        # split the selected years by comma and return them as a list
        selected_years = current_state.selected_years.split(',')

        # sort the years
        selected_years = sorted([int(year.strip()) for year in selected_years if year.strip().isdigit()])

        session.close()
        engine.dispose()

        return selected_years
    
    def add_selected_year(year):
        """
        Add the given year to the current state.
        """
        engine, session = connect_db()

        # get the current state
        current_state = session.query(State).first()

        if current_state is None:
            print("[years] No current state found")

            session.close()
            engine.dispose()
            return False

        # do we have a selected years list?
        if current_state.selected_years is None:
            current_state.selected_years = str(year)
        else:
            # check if the year is already in the list
            current_years = get_selected_years()
            if year in current_years:
                print(f"[years] Year {year} is already in the selected years list")
                session.close()
                engine.dispose()
                return False
            
            # add the year to the selected years
            current_state.selected_years = f"{current_state.selected_years},{year}"

        # commit the changes
        session.commit()

        # close the database connection
        session.close()
        engine.dispose()

        return True

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
        player_labels_correct = [gr.Label(value="🔄️") for i in range(num_players)]

        for i in range(num_players):

            if i >= len(teams):
                current_team = None
            else:
                current_team = teams[i]

            if current_team is not None:
                player_labels[i] = gr.Label(value=f"{current_team.name}: {current_team.answer_1}; {current_team.answer_2} ({current_team.points})")

                label_correct_1 = answer_to_emoji(current_team.correct_1)
                label_correct_2 = answer_to_emoji(current_team.correct_2)

                player_labels_correct[i] = gr.Label(value=f"{label_correct_1} {label_correct_2}")
        
        # get video information
        video = get_video()

        label_video_id = gr.Label(value=video.id)

        label_video_question_1 = gr.Label(value=video.question_1)
        label_video_answer_1 = gr.Label(value=video.answer_1)

        label_video_question_2 = gr.Label(value=video.question_2)
        label_video_answer_2 = gr.Label(value=video.answer_2)

        return player_labels + player_labels_correct + [label_video_id, label_video_question_1, label_video_answer_1, label_video_question_2, label_video_answer_2]

    def update_score(team_name, increment):
        """
        Update the score of the given team by increment (can be 1 or -1).
        """
        engine, session = connect_db()

        # get the team with the team name
        team = session.query(Team).filter_by(name=team_name).first()

        if team:

            if team.correct_1 is None:
                # Update the team's score
                team.points += POINTS_ON_CORRECT_ANSWER_1
                team.correct_1 = True
                # commit the changes
                session.commit()
                print(f"[points] Updated {team_name} score to {team.points}")
            
            elif team.correct_2 is None:
                # Update the team's score
                team.points += POINTS_ON_CORRECT_ANSWER_2
                team.correct_2 = True
                # commit the changes
                session.commit()
                print(f"[points] Updated {team_name} score to {team.points}")

        else:
            print(f"[points] Team {team_name} not found")

        # close the database connection
        session.close()
        engine.dispose()


    def create_update_function(team_name, correct_answer: bool):
        """
        Create a closure that captures the team_index and increment.
        This function will be called when the button is clicked.
        - team_name: the name of the team
        - correct_answer: whether the answer is correct or not
        - increment: the amount to increment the score by
        """
        def update_function():
            engine, session = connect_db()
            # team names are "Team 1", "Team 2", etc.
            team = session.query(Team).filter_by(name=team_name).first()

            if team:
                if team.correct_2 is None:
                    # Update the team's score
                    added_points = POINTS_ON_CORRECT_ANSWER_2 if correct_answer else 0
                    team.points += added_points
                    team.correct_2 = "correct" if correct_answer else "incorrect"
                    # commit the changes
                    session.commit()

                    emoji = answer_to_emoji(team.correct_2)
                    print(f"[points] {emoji} Updated {team_name} score to {team.points} with answer 2")

            # close the database connection
            session.close()
            engine.dispose()

            # Return the updated labels after modifying the score
            return None
        return update_function

    def clear_round_state():
        # get all teams
        engine, session = connect_db()
        teams = session.query(Team).all()

        if RESET_PHASE_ON_NEXT_VIDEO:
            # reset the phase to 'hide'
            set_phase_hide()

        for team in teams:
            team.answer_1 = ''
            team.answer_2 = ''
            team.correct_1 = None
            team.correct_2 = None

        session.commit()

        # close the database connection
        session.close()
        engine.dispose()

        if RESET_PHASE_ON_NEXT_VIDEO:
            print("[state] Cleared round state and reset phase to 'hide'")
        else:
            print("[state] Cleared round state")
    
    def set_phase_hide():
        set_phase('hide')
    
    def set_phase_show():
        set_phase('show')

    def set_video():
        """
        Set the current video.
        """
        engine, session = connect_db()

        global video_index, videos

        if video_index >= len(videos):
            print("[video] No more videos available")
            session.close()
            engine.dispose()
            return

        # get the current video
        current_video: Video = videos[video_index]

        if current_video is None:
            print("[video] No current video found")
            session.close()
            engine.dispose()
            return
        
        # update the state
        current_state = session.query(State).first()
        current_state.video_id = current_video.id

        return_list = [
            gr.Label(value=current_video.id),
            gr.Label(current_video.question_1),
            gr.Label(current_video.answer_1),
            gr.Label(current_video.question_2),
            gr.Label(current_video.answer_2)
        ]

        # commit the changes
        session.commit()

        # close the database connection
        session.close()
        engine.dispose()

        print(f"[video] Set video to {current_video.filename} (ID {current_video.id})")

        return return_list
    
    def next_video():
        """
        Set the current video.
        """

        global video_index, videos

        if video_index == None:
            video_index = START_VIDEO_INDEX - 1
        
        if video_index >= 1:

            # check if in bounds
            if video_index >= len(videos):
                print("[video] No more videos available!")
                return []

            # add the current video to the selected years
            current_video = videos[video_index]
            currrent_year = int(current_video.answer_1)
            print(f"[years] Adding year {currrent_year} to selected years")
            add_selected_year(currrent_year)

        video_index += 1
        
        return_list = set_video()

        clear_round_state()

        return return_list
    
    # get all videos from the database
    engine, session = connect_db()
    videos = session.query(Video).all()
    video_index = None   # index of the current video

    # shuffle the videos
    # random.shuffle(videos)

    # close the database connection
    session.close()
    engine.dispose()
    
    Thread(target=consume_messages, daemon=True).start()

    player_labels = [None for i in range(num_players)]
    player_label_correct = [None for i in range(num_players)]

    player_button_correct_2 = {}
    player_button_incorrect_2 = {}

    with gr.Blocks() as demo:
        with gr.Column():

            for i in range(num_players):
                with gr.Row():
                    with gr.Column(scale=16):
                        player_labels[i] = gr.Label(value=f"No Team connected", label=f"Team {i + 1}")
                    with gr.Column(scale=1):
                        player_label_correct[i] = gr.Label(value="⚠️", label=f"1st Answer Correct/2nd Answer Correct")
                    with gr.Column(scale=1):
                        player_button_correct_2[i] = gr.Button(value="2️⃣✅")
                        player_button_incorrect_2[i] = gr.Button(value="2️⃣❌")
            
            with gr.Row():
                label_video_id = gr.Label(value=" ", label="Video ID")
                label_video_question_1 = gr.Label(value=" ", label="Question 1")
                label_video_answer_1 = gr.Label(value=" ", label="Answer 1")
                label_video_question_2 = gr.Label(value=" ", label="Question 2")
                label_video_answer_2 = gr.Label(value=" ", label="Answer 2")


            # we need to do this in a separate loop because the buttons need to be created first
            # otherwise, the update functions will not be able to find the buttons
            for i in range(num_players):
                player_name = f"Team {i + 1}"

                # Get the update functions to increment or decrement the score
                correct_fn_2 = create_update_function(player_name, True)     # question 2 correct
                incorrect_fn_2 = create_update_function(player_name, False)  # question 2 incorrect

                # Connect the buttons to their respective functions
                player_button_correct_2[i].click(fn=correct_fn_2, inputs=[], outputs=[])
                player_button_incorrect_2[i].click(fn=incorrect_fn_2, inputs=[], outputs=[])

            with gr.Row():

                # Create a button for refreshing the player labels
                button_refresh = gr.Button(value="Refresh")
                button_next = gr.Button(value="Next Video")
                # button_exit = gr.Button(value="Exit")

                # components to refresh
                video_refresh_components = [label_video_id, label_video_question_1, label_video_answer_1, label_video_question_2, label_video_answer_2]
                all_refresh_components = player_labels + player_label_correct + video_refresh_components

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_next.click(fn=next_video, inputs=[], outputs=video_refresh_components)
                # button_exit.click(fn=exit, inputs=[], outputs=[])

                timer_refresh = gr.Timer(0.5)
                timer_refresh.tick(
                    fn=refresh_labels,
                    inputs=[],
                    outputs=all_refresh_components,
                    show_progress="hidden",
                )
            
            with gr.Row():
                # Create a button for setting the phase to hide
                button_hide = gr.Button(value="Hide Answers")
                button_show = gr.Button(value="Show Answers")

                # When the button is clicked, set_phase_hide or set_phase_show will be called
                button_hide.click(fn=set_phase_hide, inputs=[], outputs=[])
                button_show.click(fn=set_phase_show, inputs=[], outputs=[])
            
            # with gr.Row():
# 
            #     # Create a button for refreshing the player labels
            #     button_hide = gr.Button(value="Hide Answers")
            #     button_show = gr.Button(value="Show Answers")
# 
            #     # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
            #     button_hide.click(fn=set_phase_hide, inputs=[], outputs=[])
            #     button_show.click(fn=set_phase_show, inputs=[], outputs=[])

    demo.launch(
        server_name='0.0.0.0',
        server_port=7999,
        debug=True,
        auth=AUTH_CREDENTIALS if USE_AUTH else None,
    )