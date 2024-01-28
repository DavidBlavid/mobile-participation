# this file splits videos from /videos/original into 2s, 5s and 10s clips with ffmpeg
# and saves them in /videos/2s, /videos/5s and /videos/10s respectively

import os
from tqdm import tqdm

if __name__ == '__main__':

    # get all files in /videos/original
    files = os.listdir('videos/original')

    # make /videos/2s, /videos/5s and /videos/10s if they don't exist
    for folder in ['2s', '5s', '10s']:
        if not os.path.exists(f'videos/{folder}'):
            os.makedirs(f'videos/{folder}')
    
    print(f"Splitting {len(files)} videos...")

    # split each file into 2s, 5s and 10s clips
    # only take the first 2s, 5s and 10s of each video
    for file in tqdm(files):
        os.system(f'ffmpeg -i "videos/original/{file}" -ss 00:00:00 -t 00:00:02 -loglevel error "videos/2s/{file}"')
        os.system(f'ffmpeg -i "videos/original/{file}" -ss 00:00:00 -t 00:00:05 -loglevel error "videos/5s/{file}"')
        os.system(f'ffmpeg -i "videos/original/{file}" -ss 00:00:00 -t 00:00:10 -loglevel error "videos/10s/{file}"')