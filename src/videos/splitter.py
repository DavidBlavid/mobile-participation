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
    if not os.path.exists(f'videos/clips'):
        os.makedirs(f'videos/clips')

    print(f"Splitting {len(videos)} videos...")

    for video in tqdm(videos):
        video_path = f'./videos/original/{video.filename}.mp4'

        # parse the time strings
        video_start = parse_time(video.video_start)
        video_end = parse_time(video.video_end)

        # extract the clip
        if not (video.video_start == '0' and video.video_end == '0'):

            command = (
                f"ffmpeg -i {video_path} -ss {video_start} -to {video_end} "
                f"-c:v libx264 -c:a aac -b:v 2500k -b:a 192k -vf scale=1280:720 -profile:v main -y "
                f"videos/clips/{video.filename}.mp4"
            )

            os.system(command)
    
    print("Done!")