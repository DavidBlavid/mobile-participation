import pika
import os
import sys
import gradio as gr
import random
from threading import Thread

from src.db.model import Team, Video, State
from src.db.build import build, connect_db, set_phase, get_phase, get_video

POINTS_ON_CORRECT_ANSWER = 10

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

        # get the first video
        video = session.query(Video).first()

        current_state.video_id = video.id

        # reset all team scores to 0
        teams = session.query(Team).all()

        for team in teams:
            team.points = 0
            team.answer = ''
            team.correct = None
        
        # commit and close
        session.commit()
        session.close()
        engine.dispose()

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
        player_labels_correct = [gr.Label(value="🔄️") for i in range(num_players)]

        for i in range(num_players):

            if i >= len(teams):
                current_team = None
            else:
                current_team = teams[i]

            if current_team is not None:
                player_labels[i] = gr.Label(value=f"{current_team.name}: {current_team.answer} ({current_team.points})")

                current_team_correct = current_team.correct

                match current_team_correct:
                    case None:
                        player_labels_correct[i] = gr.Label(value=f"🔄️")
                    
                    case True:
                        player_labels_correct[i] = gr.Label(value=f"✅")
                    
                    case False:
                        player_labels_correct[i] = gr.Label(value=f"❌")
        
        # get video information
        video = get_video()

        label_video_id = gr.Label(value=video.id)
        label_video_question = gr.Label(value=video.question)
        label_video_answer = gr.Label(value=video.answer)

        return player_labels + player_labels_correct + [label_video_id, label_video_question, label_video_answer]

    def update_score(team_name, increment):
        """
        Update the score of the given team by increment (can be 1 or -1).
        """
        engine, session = connect_db()

        # get the team with the team name
        team = session.query(Team).filter_by(name=team_name).first()

        if team:

            if team.correct is None:
                # Update the team's score
                team.points += POINTS_ON_CORRECT_ANSWER
                team.correct = True
                # commit the changes
                session.commit()
                print(f"Updated {team_name} score to {team.points}")

        else:
            print(f"Team {team_name} not found")

        # close the database connection
        session.close()
        engine.dispose()


    def create_update_function(team_name, correct_answer: bool):
        """
        Create a closure that captures the team_index and increment.
        This function will be called when the button is clicked.
        - team_name: the name of the team
        - correct_answer: whether the answer is correct or not
        """
        def update_function():
            engine, session = connect_db()
            # Assuming the team names are "Team 1", "Team 2", etc.
            team = session.query(Team).filter_by(name=team_name).first()

            if team:

                if team.correct is None:

                    # Update the team's score
                    added_points = POINTS_ON_CORRECT_ANSWER if correct_answer else 0
                    team.points += added_points
                    team.correct = correct_answer

                    # commit the changes
                    session.commit()
                    print(f"Updated {team_name} score to {team.points}")
                else:
                    print(f"Team {team_name} was already rated")
            else:
                print(f"Team {team_name} not found")

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

        for team in teams:
            team.answer = ''
            team.correct = None

        session.commit()

        # close the database connection
        session.close()
        engine.dispose()
    
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
            print("No video found")
            return

        # get the current video
        current_video = videos[video_index]

        if current_video is None:
            print("No video found")
            return
        
        # update the state
        current_state = session.query(State).first()
        current_state.video_id = current_video.id

        return_list = [
            gr.Label(value=current_video.id),
            gr.Label(current_video.question),
            gr.Label(current_video.answer)
        ]

        # commit the changes
        session.commit()

        # close the database connection
        session.close()
        engine.dispose()

        return return_list
    
    def next_video():
        """
        Set the current video.
        """
        global video_index, videos
        if video_index == None:
            video_index = -1
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

    player_button_correct = {}
    player_button_incorrect = {}

    with gr.Blocks() as demo:
        with gr.Column():

            for i in range(num_players):
                with gr.Row():
                    with gr.Column(scale=16):
                        player_labels[i] = gr.Label(value=f"No Team connected")
                    with gr.Column(scale=1):
                        player_label_correct[i] = gr.Label(value="⚠️")
                    with gr.Column(scale=2):
                        player_button_correct[i] = gr.Button(value="True")
                        player_button_incorrect[i] = gr.Button(value="False")
            
            with gr.Row():
                label_video_id = gr.Label(value=" ")
                label_video_question = gr.Label(value=" ")
                label_video_answer = gr.Label(value=" ")


            # we need to do this in a separate loop because the buttons need to be created first
            # otherwise, the update functions will not be able to find the buttons
            for i in range(num_players):
                player_name = f"Team {i + 1}"

                # Get the update functions for increment and decrement
                correct_answer_function = create_update_function(player_name, True)
                incorrect_answer_function = create_update_function(player_name, False)

                # Connect the buttons to their respective functions
                player_button_correct[i].click(fn=correct_answer_function, inputs=[], outputs=[])
                player_button_incorrect[i].click(fn=incorrect_answer_function, inputs=[], outputs=[])

            with gr.Row():

                # Create a button for refreshing the player labels
                button_refresh = gr.Button(value="Refresh")
                button_next = gr.Button(value="Next Video")
                # button_exit = gr.Button(value="Exit")

                # components to refresh
                video_refresh_components = [label_video_id, label_video_question, label_video_answer]
                all_refresh_components = player_labels + player_label_correct + video_refresh_components

                # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
                button_refresh.click(fn=refresh_labels, inputs=[], outputs=all_refresh_components, every=0.5)
                button_next.click(fn=next_video, inputs=[], outputs=video_refresh_components)
                # button_exit.click(fn=exit, inputs=[], outputs=[])
            
            # with gr.Row():
# 
            #     # Create a button for refreshing the player labels
            #     button_hide = gr.Button(value="Hide Answers")
            #     button_show = gr.Button(value="Show Answers")
# 
            #     # When the button is clicked, refresh_labels will be called and its outputs will update the player_labels
            #     button_hide.click(fn=set_phase_hide, inputs=[], outputs=[])
            #     button_show.click(fn=set_phase_show, inputs=[], outputs=[])

    demo.launch(server_name='0.0.0.0', server_port=7999, debug=True)