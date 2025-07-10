import gradio as gr
import sys
from os import getenv
import pika

from src.db.model import Team
from src.db.build import connect_db

DEBUG_PRINT = False

# used for a gradio theme
TEAM_COLORS = {
    1: "red",
    2: "blue",
    3: "green",
    4: "orange",
    5: "purple",
    6: "cyan",
    7: "gray",
    8: "pink",
}

def connect_mq():
    # Connect to RabbitMQ
    in_docker = getenv('IN_DOCKER', False)
    rabbitmq_host = 'rabbitmq' if in_docker else 'localhost'

    connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host, port=5672))
    channel = connection.channel()

    channel.queue_declare(queue='game', durable=True)

    return channel, connection

if __name__ == '__main__':

    # command line arguments
    arguments = sys.argv[1:]

    if len(arguments) < 2:
        print('Usage: python -m src.client.host <port> <teamname>')
        sys.exit(1)

    if arguments[0] == '-e':
        team_name = f'Team {arguments[1]}'
        port = 8000 + int(arguments[1])
    else:
        port = int(arguments[1])

        # all other arguments are the team name
        team_name = ' '.join(arguments[1:])

    # so if arguments is empty, the default team name is 'Team 1'
    if team_name == '' or team_name == ' ' or team_name is None:
        team_name = 'Team 1'
    
    if arguments[0] == 'help':
        print('Usage: python -m src.client.host <port> <teamname>')
        print('Example: - python -m src.client.host 8080 "Team 1"')
        print('         - python -m src.client.host -e 1         ("Team 1" on port 8081)')
        sys.exit(0)

    print("==============")
    print(f'Name: {team_name}')
    print(f'Port: {port}')
    print("==============")
    
    # connect to the database
    engine, session = connect_db()

    # get the team with the team name
    team = session.query(Team).filter_by(name=team_name).first()

    if team is None:
        # create a new team
        team = Team(name=team_name,
                    points=0,
                    answer_1='',
                    answer_2='')
        
        if DEBUG_PRINT: print(f'Created new team {team_name}')
        
        # add the team to the database
        session.add(team)
        session.commit()

    # close the database connection
    session.close()
    engine.dispose()

    if DEBUG_PRINT: print(f'Starting mobile host on port {port} for team {team_name}...')

    # Function to be called when the button is pressed
    def send_text(answer1, answer2, team_name=team_name):

        # Connect to RabbitMQ
        channel, connection = connect_mq()

        message_text = f'{team_name}§{answer1}§{answer2}'

        channel.basic_publish(
            exchange='',
            routing_key='game',
            body=message_text,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )

        # close the connection
        connection.close()
        
        return ["", ""]  # Clear the text box after sending
    
    # color style based on team number
    team_number = int(team_name.split(' ')[1])
    team_color = TEAM_COLORS[team_number]

    # create a theme with the team color
    theme = gr.themes.Default(neutral_hue=team_color)

    # uses the theme for the demo
    with gr.Blocks(theme=theme) as demo:

        gr.HTML(f'<h1>{team_name}</h1>', elem_classes=[f'team-{team_number}'])

        gr.HTML(f'<b>Frage 1:</b>')
        input_field_1 = gr.Textbox(value='', placeholder='Antwort eingeben...', label='Input', show_label=False)

        gr.HTML(f'<b>Frage 2:</b>')
        input_field_2 = gr.Textbox(value='', placeholder='Antwort eingeben...', label='Input', show_label=False)


        button_send = gr.Button(value='Senden')

        # Connect the button to the send_text function with the text from input_field as an argument

        input_fields = [input_field_1, input_field_2]

        # send via button
        button_send.click(fn=send_text, inputs=input_fields, outputs=input_fields)

        # send via enter
        # input_field_1.submit(fn=send_text, inputs=input_fields, outputs=input_fields)
        # input_field_2.submit(fn=send_text, inputs=input_fields, outputs=input_fields)
        
    demo.launch(
        server_name='0.0.0.0',
        server_port=port
        )
