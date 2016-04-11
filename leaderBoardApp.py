# -*- coding: utf-8 -*-
"""
    DataScienceLeaderboardApp
    ~~~~~~~~

    A Leaderboard App for Data Science/Modeling competitions.

    :copyright: (c) 2016 by Josiah Olson (thenomemac@gmail.com).
    :license: MIT, see LICENSE for more details.
"""

import os
import time
from contest.helperfxns import loadAndScore
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from flask import Flask, Markup, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from markdown import markdown
from werkzeug import check_password_hash, generate_password_hash, \
     secure_filename


# configuration
DATABASE = 'dsLeaderboard.db'
DEBUG = True
SECRET_KEY = 'superSecretKeyGoesHere'

# contest specific variables
globalTitle = 'Data Modeling Contest App'
usedPages = ['description', 'evaluation', 'rules', 'prizes', 'discussion']
externalDiscussionLink = 'https://www.reddit.com/r/MachineLearning/'
# consider changing this, uploads can take a lot of drive space
UPLOAD_FOLDER = 'contest/submissions/'
ALLOWED_EXTENSIONS = ['csv', 'txt', 'zip', 'gz']
# order the score function by asc or desc
orderBy = 'asc'

# create app
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('LEADERBOARDAPP_SETTINGS', silent=True)


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db


@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = query_db('select user_id from user where username = ?',
                  [username], one=True)
    return rv[0] if rv else None


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.before_request
def before_request():
    g.usedPages = usedPages
    g.globalTitle = globalTitle
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)


@app.route('/')
def defaultlanding():
    """Shows a users leaderboard for modeling contest.
    If not logged in then forward user to contest description.
    """
    #send user to description page if not logged in
    if not g.user:
        return redirect(url_for('description'))
    #display leaderboard for competition if logged in
    return redirect(url_for('leaderboard'))

@app.route('/leaderboard')
def leaderboard():
    board = query_db('''
        select sub.* from submission sub
        inner join (select user_id, max(submit_date) max_submit_date 
          from submission group by user_id) max_sub
        on sub.user_id = max_sub.user_id and
          sub.submit_date = max_sub.max_submit_date 
        order by sub.submit_date %s''' % orderBy)
    return render_template('leaderboard.html',
                           title='Leaderboard',
                           leaderboard=board)

@app.route('/description')
def description():
    """Displays a markdown doc describing the predictive modeling contest.
    Note ./content/contest/<url calling path>.md must be modified for contest.
    """
    #rule = request.url_rule
    #print(rule)
    file = open('./contest/content/description.md', 'r')
    rawText = file.read()
    file.close()
    content = Markup(markdown(rawText))
    return render_template('markdowntemplate.html', 
                           title='Description', 
                           content=content)

@app.route('/evaluation')
def evaluation():
    """Displays a markdown doc describing the predictive modeling contest.
    Note ./content/contest/<url calling path>.md must be modified for contest.
    """
    file = open('./contest/content/evaluation.md', 'r')
    rawText = file.read()
    file.close()
    content = Markup(markdown(rawText))
    return render_template('markdowntemplate.html', 
                           title='Evaluation', 
                           content=content)
                           
@app.route('/rules')
def rules():
    """Displays a markdown doc describing the predictive modeling contest.
    Note ./content/contest/<url calling path>.md must be modified for contest.
    """
    file = open('./contest/content/rules.md', 'r')
    rawText = file.read()
    file.close()
    content = Markup(markdown(rawText))
    return render_template('markdowntemplate.html', 
                           title='Rules', 
                           content=content)
     
@app.route('/prizes')
def prizes():
    """Displays a markdown doc describing the predictive modeling contest.
    Note ./content/contest/<url calling path>.md must be modified for contest.
    """
    file = open('./contest/content/prizes.md', 'r')
    rawText = file.read()
    file.close()
    content = Markup(markdown(rawText))
    return render_template('markdowntemplate.html', 
                           title='Prizes', 
                           content=content)

@app.route('/discussion')
def discussion():
    return redirect(externalDiscussionLink)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/uploadsubmission', methods=['GET', 'POST'])
def upload_file():
    """Allow users to upload submissions to modeling contest
    Users must be logged in."""
    if request.method == 'POST':
        try:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                #append userid and date to file to avoid duplicates
                filename = str(session['user_id']) + '_' + \
                           str(int(time.time())) + '_' + filename
                fullPath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fullPath)
                model_score = loadAndScore(fullPath)
                #cache the filename and submission to database
                db = get_db()
                db.execute('''insert into submission (user_id, filename, submit_date,     
                           public_score, private_score, total_score) 
                           values (?, ?, ?, ?, ?, ?)''',                  
                           (session['user_id'], filename, int(time.time()), *model_score))
                db.commit()
                flash('Your submission was recorded.')
                return redirect(url_for('leaderboard'))
        except:
            flash('File did not upload or score correctly!')
    return render_template('uploadsubmission.html', 
                           title="Upload Submission")


@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    return render_template('timeline.html', messages=query_db('''
        select message.*, user.* from message, user
        where message.author_id = user.user_id
        order by message.pub_date desc limit ?''', [PER_PAGE]))


@app.route('/<username>')
def user_timeline(username):
    """Display's a users tweets."""
    profile_user = query_db('select * from user where username = ?',
                            [username], one=True)
    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = query_db('''select 1 from follower where
            follower.who_id = ? and follower.whom_id = ?''',
            [session['user_id'], profile_user['user_id']],
            one=True) is not None
    return render_template('timeline.html', messages=query_db('''
            select message.*, user.* from message, user where
            user.user_id = message.author_id and user.user_id = ?
            order by message.pub_date desc limit ?''',
            [profile_user['user_id'], PER_PAGE]), followed=followed,
            profile_user=profile_user)


@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    db = get_db()
    db.execute('insert into follower (who_id, whom_id) values (?, ?)',
              [session['user_id'], whom_id])
    db.commit()
    flash('You are now following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Removes the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    db = get_db()
    db.execute('delete from follower where who_id=? and whom_id=?',
              [session['user_id'], whom_id])
    db.commit()
    flash('You are no longer following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))




@app.route('/add_message', methods=['POST'])
def add_message():
    """Registers a new message for the user."""
    if 'user_id' not in session:
        abort(401)
    if request.form['text']:
        db = get_db()
        db.execute('''insert into message (author_id, text, pub_date)
          values (?, ?, ?)''', (session['user_id'], request.form['text'],
                                int(time.time())))
        db.commit()
        flash('Your message was recorded')
    return redirect(url_for('timeline'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('leaderboard'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('leaderboard'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute('''insert into user (
              username, email, pw_hash) values (?, ?, ?)''',
              [request.form['username'], request.form['email'],
               generate_password_hash(request.form['password'])])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('leaderboard'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url


if __name__ == '__main__':
    init_db()
    app.run()
