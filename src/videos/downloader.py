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

    # manually create a tqdm bar
    with tqdm(total=len(lines)) as pbar:

        for i, line in enumerate(lines):

            line = line.strip()

            if line == '':
                continue

            tokens = line.split(';')

            if len(tokens) != 9:
                print(f'Warning: invalid line in {path_csv}: {line}')
                continue

            # get the entry information
            title = tokens[0]
            author = tokens[1]
            question_1 = tokens[2]
            answer_1 = tokens[3]
            question_2 = tokens[4]
            answer_2 = tokens[5]
            link = tokens[6]
            video_start = tokens[7]
            video_end = tokens[8]

            # create the filename
            # turn source lowercase, remove special characters and replace spaces with underscores
            replacements = {
                ' ': '_',
                'ä': 'ae',
                'ö': 'oe',
                'ü': 'ue',
                'ß': 'ss'
            }
            download_name = title.lower()
            for pre, post in replacements.items():
                download_name = download_name.replace(pre, post)

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
                title=title,
                author=author,
                question_1=question_1,
                answer_1=answer_1,
                question_2=question_2,
                answer_2=answer_2,
                link=link,
                video_start=video_start,
                video_end=video_end,
                filename=download_name
            )

            # add the video to the database
            session.add(video)

            # update the progress bar
            pbar.update(1)

    # commit the changes
    session.commit()

    # close the database connection
    session.close()
    engine.dispose()