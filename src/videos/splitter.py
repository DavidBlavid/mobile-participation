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

    # create the video/clips folder
    if not os.path.exists(f'videos/clips'):
        os.makedirs(f'videos/clips')
    
    print(f"Splitting {len(videos)} videos...")

    for video in tqdm(videos):

        # get the video path
        video_path = f'./videos/original/{video.filename}.mp4'

        # get conversion parameters
        show_video = video.show_video
        video_start = video.video_start
        video_end = video.video_end

        duration = video_end - video_start

        # construct the ffmpeg command
        if show_video == 'ja':
            command = f'ffmpeg -i {video_path} -ss {video_start} -to {video_end} -y -c copy videos/clips/{video.filename}.mp4'
        else:
            command = f'ffmpeg -i {video_path} -ss {video_start} -to {video_end} -vf drawbox=color=black:t=fill -y -c:a copy videos/clips/{video.filename}.mp4'

        # execute the command
        os.system(command)
    
    print("Done!")