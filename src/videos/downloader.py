import os
import sys
from tqdm import tqdm
from src.db.build import connect_db
from src.db.model import Video

# RUN WITH '-d' TO DOWNLOAD THE VIDEOS
# OTHERWISE THIS JUST ADDS ENTRIES TO THE DATABASE

path_csv = 'src/videos/videos.csv'

if __name__ == '__main__':

    # get launch arguments
    arguments = sys.argv[1:]

    with open(path_csv, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # if the folder /videos/original does not exist, create it
    if not os.path.exists('videos/original'):
        os.makedirs('videos/original')

    # connect to the database
    engine, session = connect_db()

    for line in tqdm(lines):
        line = line.strip()

        if line == '':
            continue

        tokens = line.split(';')

        if len(tokens) != 5:
            print(f'Warning: invalid line in {path_csv}: {line}')
            continue

        author = tokens[0]
        source = tokens[1]
        question = tokens[2]
        answer = tokens[3]
        link = tokens[4]

        # create the filename
        # turn source lowercase, remove special characters and replace spaces with underscores
        download_name = source.lower().replace(' ', '_').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')

        # remove all special characters, only keep alphanumeric characters and underscores
        download_name = ''.join(e for e in download_name if (e.isalnum() or e == '_'))

        # download if '-d' is in the arguments
        if '-d' in arguments:
            # download the video using yt-dlp to /videos/original
            # also convert to mp4
            download_string = f'yt-dlp {link} -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --quiet -o videos/original/{download_name}'
            os.system(download_string)

        # create a new database entry
        video = Video(
            author=author,
            source=source,
            question=question,
            answer=answer,
            link=link,
            filename=download_name
        )

        # add the video to the database
        session.add(video)

    # commit the changes
    session.commit()

    # close the database connection
    session.close()
    engine.dispose()