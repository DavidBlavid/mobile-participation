# this file splits videos from /videos/original into 2s, 5s and 10s clips with ffmpeg
# and saves them in /videos/2s, /videos/5s and /videos/10s respectively

import os
from tqdm import tqdm
from src.db.build import connect_db
from src.db.model import Video

if __name__ == '__main__':

    # connect to the database
    engine, session = connect_db()

    # get all videos from the database
    videos = session.query(Video).all()

    # create the folders if they do not exist
    if not os.path.exists(f'videos/questions'):
        os.makedirs(f'videos/questions')
    
    if not os.path.exists(f'videos/answers'):
        os.makedirs(f'videos/answers')

    print(f"Splitting {len(videos)} videos...")

    for video in tqdm(videos):

        # get the video path
        video_path = f'./videos/original/{video.filename}.mp4'

        # get conversion parameters
        question_start = video.question_start
        question_end = video.question_end
        answer_start = video.answer_start
        answer_end = video.answer_end

        # extract the question clip
        command = f'ffmpeg -i {video_path} -ss {question_start} -to {question_end} -vf drawbox=color=black:t=fill -y -c:a copy videos/questions/{video.filename}.mp4'
        os.system(command)

        # extract the answer clip
        if answer_start == '-' or answer_end == '-':
            continue
        
        command = f'ffmpeg -i {video_path} -ss {answer_start} -to {answer_end} -y -c copy videos/answers/{video.filename}.mp4'
        os.system(command)
    
    print("Done!")