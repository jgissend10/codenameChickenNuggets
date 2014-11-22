import flask
from flask import Flask, request, g, session, redirect, url_for
from flask import render_template_string
from flask.ext.github import GitHub

import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URI = 'sqlite:////tmp/flask.db'
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = False

# Set these values
GITHUB_CLIENT_ID = os.environ['GITHUB_CLIENT_ID']
GITHUB_CLIENT_SECRET = os.environ['GITHUB_CLIENT_SECRET']

# setup flask
app = Flask(__name__)
app.config.from_object(__name__)

# setup github-flask
github = GitHub(app)

# setup sqlalchemy
engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    Base.metadata.create_all(bind=engine)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    github_access_token = Column(String(200))

    def __init__(self, github_access_token):
        self.github_access_token = github_access_token


@app.route('/static/<path:path>')
def static_proxy(path):
    # send_static_file will guess the correct MIME type
    return app.send_static_file(os.path.join('static', path))

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@app.after_request
def after_request(response):
    ##db_session.remove()
    return response

@app.route('/')
def index():
    if g.user:
        t = 'Hello! <a href="{{ url_for("user") }}">Get user</a> ' \
            '<a href="{{ url_for("logout") }}">Logout</a>'
        return render_template_string(t)
    else:
        return app.send_static_file('index.html')

@github.access_token_getter
def token_getter():
    user = g.user
    if user is not None:
        return user.github_access_token


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        return redirect(next_url)

    user = User.query.filter_by(github_access_token=access_token).first()
    if user is None:
        user = User(access_token)
        db_session.add(user)
    user.github_access_token = access_token
    db_session.commit()

    session['user_id'] = user.id
    return redirect(url_for('index'))


@app.route('/login')
def login():
    if session.get('user_id', None) is None:
        return github.authorize()
    else:
        return 'Already logged in'


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/user')
def user():
    return flask.jsonify(github.get('user'))

@app.route('/repos')
def repos():
	return flask.jsonify(repos = [{'name': repo['full_name']} for repo in github.get('user/repos')])

@app.route('/repo/<owner>/<repo>')
def repo(owner, repo):
    return flask.jsonify(github.get("repos/%(owner)s/%(repo)s" % {'owner': owner, 'repo': repo}))


#Sha functions as branch/commit revision.
@app.route('/repo/<owner>/<repo>/tree')
@app.route('/repo/<owner>/<repo>/tree/<sha>')
def repo_tree(owner, repo, sha='master'):
    return flask.jsonify(github.get("repos/%(owner)s/%(repo)s/git/trees/%(sha)s" % {'owner': owner, 'repo': repo, 'sha': sha}))

#Sha functions as branch/commit revision.
@app.route('/resource/<owner>/<repo>/contents/<path>')
def contents(owner, repo, path):
    return flask.jsonify(github.get("repos/%(owner)s/%(repo)s/contents/%(path)s" % {'owner': owner, 'repo': repo, 'path': path}))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)