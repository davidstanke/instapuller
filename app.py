try:
    import googleclouddebugger
    googleclouddebugger.enable()
except ImportError:
    pass

import config
import json
import logging
import os
import requests
import sqlalchemy
import random
import time
from bs4 import BeautifulSoup
from flask import Flask, request, render_template
from google.cloud import pubsub_v1
from sqlalchemy import exc, Table, Column, Integer, String, MetaData, ForeignKey, Sequence, BigInteger, DATETIME, func
from pymysql.err import IntegrityError

# Setup Flask Web App
app = Flask(__name__)

logger = logging.getLogger()
URL = 'http://imginn.com/'

project_id = "serverless-ux-playground"
topic_name = "instapuller-media-download-request"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

futures = dict()  # What was this about?

# This defines and will create the posts table if needed in the database
metadata = MetaData()
posts = Table('posts', metadata,
              Column('username', String(255)),
              Column('post_id', BigInteger, primary_key=True),
              Column('shortcode', String(255)),
              Column('direct_link', String(255)),
              Column('caption', String(5000)),
              Column('display_url', String(255)),
              Column('thumbnail_src', String(1200)),
              Column('date_added', DATETIME(timezone=True),
                     server_default=func.now()),
              mysql_charset='utf8mb4')

media = Table('media', metadata,
              Column('post_id', BigInteger, primary_key=True),
              Column('display_url', String(255)),
              Column('path', String(1200)),
              Column('date_added', DATETIME(timezone=True),
                     server_default=func.now()),
              mysql_charset='utf8mb4')

metadata.create_all(config.db)


@app.route('/')
def processPosts():
    username = request.args.get('username')
    if (username == None):
        username = 'googlecloud'
    page = requests.get(URL + username)
    if (page.status_code == 200):
        soup = BeautifulSoup(page.content, 'html.parser')
        items = soup.find_all('div', class_='item')
        collection = getPosts(items, username)
        with config.db.connect() as conn:
            for post in collection:
                insert = posts.insert().values(post)
                try:
                    conn.execute(insert)  # If the insert succeeds
                    # Dispatch media request to pubsub
                    dispatchMediaDownloadRequest(post)
                except exc.IntegrityError as err:
                    print(err.orig)

        return render_template('index.html', data=collection)
    else:
        return_string = (
            "Problem retrieving results: "
            + URL + username + " returns "
            + str(page.status_code) + " " + str(page.reason))
        return return_string


def dispatchMediaDownloadRequest(post):
    # Dispatch media request to pubsub topic
    # data must be a bytestring.
    logger.info("Dispatch request to pubsub: %s", post)
    publisher.publish(topic_path, data=(json.dumps(post)).encode("utf-8"))


def convertShortCodeToPostID(shortcode):
    return_code = []
    for char in shortcode:
        return_code.append(str(ord(char)))
    return ''.join(map(str, return_code[:7]))


def getPosts(postList, username):
    postCollection = []
    for post in postList:
        item = {}
        item["username"] = username
        item["shortcode"] = post.find('a')['href'][3:-1]
        item["direct_link"] = "https://www.instagram.com/p/" + \
            item["shortcode"]
        try:
            item["caption"] = post.find('img')["alt"]
        except:
            item["caption"] = ""
        item["display_url"] = post.find_all('a')[1]['href']
        item["thumbnail_src"] = post.find('img')["data-src"]
        item["post_id"] = convertShortCodeToPostID(item["shortcode"])
        postCollection.append(item)
    return postCollection


@app.route('/stats')
def showStats():
    with config.db.connect() as conn:
        result = conn.execute('''
            SELECT username, count(username) from posts
                GROUP BY username
                ORDER by count(username) desc;''')

    tableRows = []
    for row in result:
        tableRows.append((row[0], row[1]))

    return render_template('stats.html', rows=tableRows)


@app.route('/usernames')
def get_usernames():
    with config.db.connect() as conn:
        result = conn.execute('''
            select username from posts
                group by username
                order by username;''')
    users = []
    for row in result:
        users.append(row[0])
    return json.dumps(users)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))