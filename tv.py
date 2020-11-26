import datetime
import praw
import time
import threading
import logging
import json
import sys
import random
from pathlib import Path
from flask import Flask, render_template

"""Path to configuration file"""
CONFIG_PATH = Path("config.json")

"""Path to database file"""
DB_PATH = Path("db.json")


class Config:
    """Pulls from config.json"""

    def __init__(self):
        with open(CONFIG_PATH, "r") as json_in:
            _json = json.load(json_in)

            self.reddit_client_secret = _json["reddit"]["client_secret"]
            self.reddit_client_id = _json["reddit"]["client_id"]


config = Config()

#### REDDIT #####

reddit = praw.Reddit(
    client_id=config.reddit_client_id,
    client_secret=config.reddit_client_secret,
    user_agent="A lonely bot",
)
subreddit = reddit.subreddit("InterdimensionalCable")


class Posts:
    def __init__(self):
        """Creates a new "Posts" from scratch"""

        self.database = {}
        self.updated = str(datetime.datetime.utcnow())

    def from_path(self, path: Path):
        """Gets "Posts" from path (file)"""

        try:
            with open(path, "r") as f:
                self.database = json.loads(f.read())
                self.updated = str(datetime.datetime.utcnow())
        except:
            logging.error(f"Could not open {path}")
            sys.exit(1)

    def add_post(self, name: str, url: str):
        """Adds a single post already found"""

        if url in self.database:
            return

        self.database[url] = {"name": name, "added": str(datetime.datetime.utcnow())}

    def save_database(self):
        """Dumps database to json file"""

        json.dump(self.database, open(DB_PATH, "w+"))

    def add_batch(self):
        """Adds new batch of posts"""

        for submission in subreddit.hot(limit=15):
            if (
                not (
                    submission.url.startswith("https://youtu.be/")
                    or submission.url.startswith("https://www.youtube.com/")
                )
                or subreddit.over18
            ):
                continue

            logging.info(f"Adding post '{submission.title}' from {submission.url}")

            try:
                self.add_post(
                    submission.title,
                    submission.url.split("/")[-1]
                    .split("v=")[-1]
                    .split("?")[0]
                    .split("&")[0],
                )
            except:
                logging.error(
                    f"Could not add '{submission.title}' from {submission.url}'"
                )

        if len(self.database) > 50000:
            # cull if too large
            logging.warn(
                "Culling database to 25k (deleting oldest half) as it's over 50k entries long"
            )
            self.database = dict(list(self.database.items())[: len(self.database) // 2])

        self.save_database()

    def random(self):
        """Gets random post from database"""

        return random.choice(list(self.database.items()))


posts = Posts()

if DB_PATH.exists():
    logging.info(f"Pulling from {DB_PATH}..")
    posts.from_path(DB_PATH)


def batch_add_loop():
    """Loop for adding new batches of posts, creates a new thread to do this"""

    def inner_loop():
        """Inner thread loop for creating new batches of posts every x secs"""

        while True:
            logging.info("Adding post batch..")
            posts.add_batch()
            time.sleep(60 * 60 * 2)

    thread = threading.Thread(target=inner_loop)
    logging.info("Starting batch loop thread..")
    thread.start()


#### FLASK ####

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", post=posts.random())


if __name__ == "__main__":
    batch_add_loop()  # loop batch adder
    app.run()
