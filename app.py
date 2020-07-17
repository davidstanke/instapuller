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
from sqlalchemy.orm import sessionmaker
from pymysql.err import IntegrityError

# Classes for this application
from models import Post, Media, Base

# Setup Flask Web App
app = Flask(__name__)
app.secret_key = "replace_this_if_you_care"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

URL = 'http://imginn.com/'

# make a session factory
Session = sessionmaker(bind=config.db)

# project_id = "serverless-ux-playground"
# topic_name = "instapuller-media-download-request"
# publisher = pubsub_v1.PublisherClient()
# topic_path = publisher.topic_path(project_id, topic_name)

@app.route('/')
def displayPosts():
    session = Session()
    posts = session.query(Post).order_by(Post.date_added.desc())
    return render_template('index.html', data=posts)

@app.route('/addUser')
def processPosts():
    username = request.args.get('username')

    if (username == None):
        return_string = "dude, you gotta provide a username"
    else:
        headers = {'user-agent': 'my-app/0.0.1'}
        page = requests.get(URL + username, headers=headers)
        
        if (page.status_code == 200):
            soup = BeautifulSoup(page.content, 'html.parser')
            items = soup.find_all('div', class_='item')
            collection = getPosts(items, username)

            # commit to DB
            session = Session()
            for post in collection:
                logger.debug(post.shortcode)
                
                # check if post id already exists
                post_record = session.query(Post).filter(Post.post_id == post.post_id)
                
                if(post_record.count()):
                    logger.info("post already exits: " + str(post.post_id))
                else:
                    session.add(post)
        
                # dispatchMediaDownloadRequest(post)
                
            session.commit()

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
        thisPost = Post()
        thisPost.username = username
        thisPost.shortcode = post.find('a')['href'][3:-1] 
        thisPost.direct_link = "https://www.instagram.com/p/" + thisPost.shortcode
        try:
            thisPost.caption = post.find('img')["alt"]
        except:
            thisPost.caption = ""
        thisPost.display_url = post.find_all('a')[1]['href']
        thisPost.thumbnail_src = post.find('img')["data-src"]
        thisPost.post_id = convertShortCodeToPostID(thisPost.shortcode)
        postCollection.append(thisPost)
    return postCollection


@app.route('/stats')
def showStats():
    session = Session()
    result = session.query(Post.username, func.count(Post.post_id)).group_by(Post.username).all()
    stats = []

    for row in result:
        stats.append((row[0], row[1]))

    return render_template('stats.html', rows=stats)


@app.route('/usernames')
def get_usernames():
    session = Session()
    result = session.query(Post.username).group_by(Post.username).order_by(Post.username)
    users = []
    for row in result:
        users.append(row[0])
    return json.dumps(users)

@app.route('/purgeall')
def purge_all():
    session = Session()
    posts = session.query(Post).delete()
    media = session.query(Media).delete()
    session.commit()
    flash('All gone! Deleted ' + str(posts) + ' posts and ' + str(media) + ' media entries.')
    return redirect(url_for('displayPosts'))
    
if __name__ == "__main__":

    # create initial database tables (if not already present)
    Base.metadata.create_all(config.db)

    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
