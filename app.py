import config
import json
import logging
import os
import requests
import sqlalchemy
import random
import time
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, flash, redirect, url_for
from google.cloud import pubsub_v1
from sqlalchemy import create_engine, exc, Table, Column, Integer, String, MetaData, ForeignKey, Sequence, BigInteger, DATETIME, func
from pymysql.err import IntegrityError

# Setup Flask Web App
app = Flask(__name__)
app.secret_key = "replace_this_if_you_care"

logger = logging.getLogger()
URL = 'http://imginn.com/'

# project_id = "serverless-ux-playground"
# topic_name = "instapuller-media-download-request"
# publisher = pubsub_v1.PublisherClient()
# topic_path = publisher.topic_path(project_id, topic_name)

futures = dict()  # What was this about?

# This defines and will create the posts table if needed in the database
metadata = MetaData()
posts = Table('posts', metadata,
              Column('username', String(255)),
              Column('post_id', BigInteger, primary_key=True),
              Column('shortcode', String(255)),
              Column('direct_link', String(2047)),
              Column('caption', String(8191)),
              Column('display_url', String(2047)),
              Column('thumbnail_src', String(2047)),
              Column('date_added', DATETIME(timezone=True),
                     server_default=func.now()),
              mysql_charset='utf8mb4')

media = Table('media', metadata,
              Column('post_id', BigInteger, primary_key=True),
              Column('display_url', String(255)),
              Column('path', String(2047)),
              Column('date_added', DATETIME(timezone=True),
                     server_default=func.now()),
              mysql_charset='utf8mb4')

# NOTE: the following command doesn't work for sqlite. not sure why.
# So, the database file ('misc/instapuller-local.db') has the tables already
# in place.
metadata.create_all(config.db)

@app.route('/')
def displayPosts():
    with config.db.connect() as conn:
        posts = conn.execute('''
            select *
            from posts
            order by date_added DESC;''')
        return render_template('index.html', data=posts)

@app.route('/addUser')
def processPosts():
    username = request.args.get('username')
    if (username == None):
        username = 'googlecloud'
    headers = {'user-agent': 'my-app/0.0.1'}
    page = requests.get(URL + username, headers=headers)
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

        return_string = (
            "added Instgram user: " + username 
            + " (" + str(len(collection)) + " items)")
    else:
        return_string = (
            "Problem retrieving results: "
            + URL + username + " returns "
            + str(page.status_code) + " " + str(page.reason))
    flash(return_string)
    return redirect(url_for('displayPosts'))


def dispatchMediaDownloadRequest(post):
    # Dispatch media request to pubsub topic
    # data must be a bytestring.
    logger.info("Dispatch request to pubsub: %s", post)
    # publisher.publish(topic_path, data=(json.dumps(post)).encode("utf-8"))


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

@app.route('/purgeall')
def purge_all():
    with config.db.connect() as conn:
        conn.execute('delete from posts;')
        conn.execute('delete from media;')
    flash('all gone.')
    return redirect(url_for('displayPosts'))
    
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
