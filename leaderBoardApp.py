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
     render_template, abort, g, flash, send_from_directory, _app_ctx_stack
from markdown import markdown
import werkzeug
from werkzeug.security import check_password_hash, generate_password_hash

# configuration
DATABASE = 'dsLeaderboard.db'
DEBUG = True
SECRET_KEY = 'superSecretKeyGoesHere'

# contest specific variables
globalTitle = 'Modeling Contest'
usedPages = ['description', 'evaluation', 'rules', 'data', 'discussion']
# discussion navbar link will link to this forum-wiki-like resource
externalDiscussionLink = 'https://www.reddit.com/r/MachineLearning/'
# consider changing this, uploads can take a lot of drive space
UPLOAD_FOLDER = 'contest/submissions/'
ALLOWED_EXTENSIONS = ['csv', 'txt', 'zip', 'gz']
# order the score function by asc or desc
orderBy = 'asc'
# set the max number of submissions a user is able to submit for final contest 
# scoring against the private leaderboard, ie best of # selected submissions are considered
subNbr = 1
# max number of submissions a user is allowed to make in a rolling 24hr period
dailyLimit = 2
# set the contest deadline where users can no longer upload and private score is published
contestDeadline = time.mktime(datetime(2016, 10, 21, 0, 0).timetuple())
# debug variable that if True allows private leaderboard to be displayed before contest deadline
# normally should be False
showPrivate = False

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


def allowed_file(filename):
    # checks if extension in filename is allowed
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def contestEndBool():
    #return boolean if contest is over to change 'post' methods behavior
    return (contestDeadline - time.time()) < 0 or showPrivate


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
    #query the db and render the table used to display the leaderboard to users 
    if contestEndBool():
        #when evaluating for private score we take user selection table
        #or most recent submission if user didn't specify what submission was final
        board = query_db('''
            select username, max(public_score) public_score, 
                max(private_score) private_score, max(sub_cnt) sub_cnt
            from (
                select username, public_score, private_score, sub_cnt
                from submission sub
                left join (
                  select user_id, max(submit_date) max_submit_date
                  from submission 
                  where user_id not in (select distinct user_id from selection)
                  group by user_id
                ) max_sub
                on sub.user_id = max_sub.user_id
                inner join (
                  select user_id, count(*) sub_cnt 
                  from submission 
                  group by user_id
                ) cnt
                on sub.user_id = cnt.user_id
                inner join user
                on sub.user_id = user.user_id
                left join selection 
                on sub.submission_id = selection.submission_id
                where
                  case when select_date is not null then 1 else 
                    case when max_submit_date is not null then 1 else 0 end
                  end = 1
            ) temp
            group by username
            order by private_score %s''' % orderBy)
    else:
        #display the public leader board when contest hasn't ended yet
        board = query_db('''
            select username, public_score, '?' private_score, sub_cnt
            from submission sub
            inner join (
              select user_id, max(submit_date) max_submit_date, count(*) sub_cnt 
              from submission 
              group by user_id
            ) max_sub
            on sub.user_id = max_sub.user_id and
              sub.submit_date = max_sub.max_submit_date 
            inner join user
            on sub.user_id = user.user_id
            order by public_score %s''' % orderBy)
            
    #Debug: board = [{'public_score': 0.3276235370053617, 'username': 'test3', 'private_score': 0.32036252335937015}, {'public_score': 0.3276235370053617, 'username': 'test1', 'private_score': 0.32036252335937015}, {'public_score': 0.33944709256230005, 'username': 'test2', 'private_score': 0.32003513414185064}]
    board = [dict(row) for row in board]
    for rank, row in enumerate(board):
        row['rank'] = rank + 1
    
    colNames = ['Rank', 'Participant', 'Public Score', 'Private Score', 'Submission Count']
    deadlineStr = str(datetime.fromtimestamp(contestDeadline))
    hoursLeft = abs(round((contestDeadline - time.time()) / 3600, 2))
    
    return render_template('leaderboard.html',
                           title='Leaderboard',
                           colNames=colNames,
                           leaderboard=board,
                           deadlineStr=deadlineStr,
                           hoursLeft=hoursLeft)


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
    content = Markup(markdown(rawText, 
        extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables']))
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
    content = Markup(markdown(rawText, 
        extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables']))
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
    content = Markup(markdown(rawText, 
        extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables']))
    return render_template('markdowntemplate.html', 
                           title='Rules', 
                           content=content)
     
     
@app.route('/contest/download/<path:path>')
def send_dir(path):
    # this function is used to serve the train/test files linked to in data.md
    return send_from_directory('contest/download', path)
    

@app.route('/data')
def data():
    """Displays a markdown doc describing the predictive modeling contest.
    Note ./content/contest/<url calling path>.md must be modified for contest.
    """
    file = open('./contest/content/data.md', 'r')
    rawText = file.read()
    file.close()
    content = Markup(markdown(rawText, 
        extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables']))
    return render_template('markdowntemplate.html', 
                           title='Data', 
                           content=content)
                           

# in dev version of the app the prizes page isn't used due to overlap with description/rules                           
@app.route('/prizes')
def prizes():
    """Displays a markdown doc describing the predictive modeling contest.
    Note ./content/contest/<url calling path>.md must be modified for contest.
    """
    file = open('./contest/content/prizes.md', 'r')
    rawText = file.read()
    file.close()
    content = Markup(markdown(rawText, 
        extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables']))
    return render_template('markdowntemplate.html', 
                           title='Prizes', 
                           content=content)


@app.route('/discussion')
def discussion():
    return redirect(externalDiscussionLink)


@app.route('/selectmodel', methods=['POST'])
def select_model():
    """Allow user to select the upload they'd like to use for submission
    Default selection should be most recent submissions
    """
    try:
        #check if contest has ended
        if contestEndBool():
            flash("Error: contest has ended")
            raise Exception("contest has ended")
        input = request.form
        print(str(input))
        for count, x in enumerate(input): print(count, x)
        if len(input) != subNbr:
            flash("Error: Wrong number of submissions selected")
        else:
            db = get_db()
            db.execute("delete from selection where user_id = '%s'" % session['user_id'])
            db.commit()
            #upload user defined selections to database
            for count, submission_id in enumerate(input):
                db = get_db()
                db.execute('''insert into selection (user_id, select_nbr, submission_id,     
                           select_date) values (?, ?, ?, ?)''',                  
                           (session['user_id'], count + 1, int(submission_id), int(time.time())))
                db.commit()
                
            flash("Selection successful!")
    except:
        flash("Error: Your selection was not recorded")
    return redirect('/uploadsubmission')


@app.route('/uploadsubmission', methods=['GET', 'POST'])
def upload_file():
    """Allow users to upload submissions to modeling contest
    Users must be logged in."""
    
    #query the db and render the table used to display the leaderboard to users    
    userBoard = query_db('''
        select submission_id, submit_date, public_score
        from submission sub
        where user_id = '%s'
        order by public_score %s''' % (session['user_id'], orderBy))
    
    userBoard = [dict(row) for row in userBoard]
    for row in userBoard:
        row['score'] = row['public_score']
        row['str_time'] = str(datetime.fromtimestamp(row['submit_date']))
        
    colNames = ['Submission Time', 'Public Score']
    
    if request.method == 'POST':
        try:
            #check if contest has ended
            if contestEndBool():
                flash("Error: contest has ended")
                raise Exception("contest has ended")
            
            print("here")
            #ensure user hasn't exceeded daily submission limit
            dailyCnt = query_db('''select count(*) sub_cnt
                from submission sub
                where submit_date > %s
                and user_id = %s
                group by user_id''' % (time.time() - 60*60*24, session['user_id']))
            
            if len(dailyCnt) == 0:
                dailyCnt = 0
            else:
                dailyCnt = int(dict(dailyCnt[0])['sub_cnt'])
            
            if dailyCnt > dailyLimit:
                flash("Error: exceeded daily upload limit")
                raise Exception('Upload limit exceeded')
            
            file = request.files['file']
            #throw error if extension is not allowed
            if not allowed_file(file.filename):
                raise Exception('Invalid file extension')
                
            if file and allowed_file(file.filename):
                filename = werkzeug.secure_filename(file.filename)
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
                
                #inform user upload was a success
                flash('Your submission was recorded.')
                return redirect(url_for('leaderboard'))
        except:
            #if exception is thrown in process then flash user
            flash('File did not upload or score! Make sure the submission format is correct.')
    return render_template('uploadsubmission.html', 
                           title="Upload Submission", 
                           userBoard=userBoard,
                           subNbr=subNbr)


@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    return render_template('timeline.html', messages=query_db('''
        select message.*, user.* from message, user
        where message.author_id = user.user_id
        order by message.pub_date desc limit ?''', [PER_PAGE]))


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


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


#launch application for dev purposes when leaderBoardApp.py script is run
if __name__ == '__main__':
    #only re-run init_db() on initial launch if you want to truncate you're sql tables
    if not os.path.isfile('dsLeaderboard.db'):
        init_db()
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    app.run()
