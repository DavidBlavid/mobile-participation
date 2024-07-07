# this file splits videos from /videos/original into 2s, 5s and 10s clips with ffmpeg
# and saves them in /videos/2s, /videos/5s and /videos/10s respectively

import os
from tqdm import tqdm
from datetime import datetime, timedelta
from src.db.build import connect_db
from src.db.model import Video

def parse_time(time_str):
    """Parse time in HH:MM:SS or seconds format."""
    if ':' in time_str:
        if time_str.count(':') == 1:
            time_str = '00:' + time_str
        return datetime.strptime(time_str, "%H:%M:%S").time()
    else:
        return datetime.strptime(time_str, "%S").time()

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
        video_path = f'./videos/original/{video.filename}.mp4'

        # parse the time strings
        question_start = parse_time(video.question_start)
        question_end = parse_time(video.question_end)
        answer_start = parse_time(video.answer_start)
        answer_end = parse_time(video.answer_end)

        print(question_start, question_end, answer_start, answer_end)

        # extract the question clip
        if not (video.question_start == '0' and video.question_end == '0'):
            question_command = (
                f"ffmpeg -ss {question_start} -to {question_end} -i {video_path} "
                f"-f lavfi -i color=c=black:s=1280x720:r=30 -y "
                f"-map 0:a -map 1:v -c:v libx264 -c:a aac -b:v 2500k -b:a 192k -shortest "
                f"videos/questions/{video.filename}.mp4"
            )
            os.system(question_command)

        # extract the answer clip
        if not (video.answer_start == '0' and video.answer_end == '0'):
            answer_command = (
                f"ffmpeg -i {video_path} -ss {answer_start} -to {answer_end} "
                f"-c:v libx264 -c:a aac -b:v 2500k -b:a 192k -vf scale=1280:720 -profile:v main -y "
                f"videos/answers/{video.filename}.mp4"
            )
            os.system(answer_command)
    
    print("Done!")