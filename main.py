from flask import Flask, request, redirect, session, url_for
from constants import CONSUMER_ID, CONSUMER_SECRET, APP_SECRET
import requests

app = Flask(__name__)
# comment out when you're done testing
#app.debug = True
app.secret_key = APP_SECRET

@app.route('/')
def index():
#authenticates with venmo 
    if session.get('venmo_token'):
        return 'Your Venmo token is %s' % session.get('venmo_token')
    else:
        return redirect('https://api.venmo.com/v1/oauth/authorize?client_id=%s&scope=access_profile&response_type=code' % CONSUMER_ID)

@app.route('/oauth-authorized')
def oauth_authorized():
    AUTHORIZATION_CODE = request.args.get('code')
    data = {
        "client_id":CONSUMER_ID,
        "client_secret":CONSUMER_SECRET,
        "code":AUTHORIZATION_CODE
        }
#Gets information
    url = "https://api.venmo.com/v1/oauth/access_token"
    response = requests.post(url, data)
    response_dict = response.json()
    access_token = response_dict.get('access_token')
    user = response_dict.get('user')

    session['venmo_token'] = access_token
    session['venmo_username'] = user['username']
    

#returns id number
    return 'You were signed in as %s' % user['id']



if __name__ == '__main__':
    app.run()
