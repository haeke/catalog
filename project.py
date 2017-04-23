from flask import Flask, render_template, \
    request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Catalog, Item

from flask import session as login_session
import random
import string
# imports for oauth2
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r')
                       .read())['web']['client_id']

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Item Menu"

# connect to the database and create database session
engine = create_engine('sqlite:///catalogwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# connect with facebook
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url =
    'https://graph.facebook.com/oauth/access_token?grant_type='
    + 'fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s'
    % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access tokent
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print url sent for api access:%s" % url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # store token in the login_session in order to logout correctly
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture'
    + '?%s&redirect=0&height=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # check that the user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;'
    + '"border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session.get('facebook_id')
    # ['facebook_id']
    # the access token must be included to successfully logout
    access_token = login_session.get('access_token')
    # ['access_token']
    url = 'https://graph.facebook.com/%s/'
    + 'permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')

    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesnt make a new user
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;"'
    + '"border-radius: 150px;-webkit-border-radius: 150px;"'
    + '"-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# disconnect a user and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('credentials')
    print 'In gdisconnect access token is %s', access_token
    print 'username is :'
    print login_session.get('ame')
    if access_token is None:
        print 'Access token is none'
        response = make_response(
            json.dumps('current user is not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/'
    + 'revoke?token=%s' % login_session.get('credentials')
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'the result is'
    print result
    if result['status'] == '200':

        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_sesssion['email']
        del login_session['picture']
        response = make_response(json.dumps('successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('successfully disconncted'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON API to view catalog information
@app.route('/catalog/<int:catalog_id>/item/JSON')
def catalogItemsJSON(catalog_id):
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    items = session.query(Item).filter_by(catalog_id=catalog_id).all()
    return jsonify(CatalogItems=[i.serialize for i in items])


# list the catalog items by catalog
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/JSON')
def catalogItemJSON(catalog_id, item_id):
    catalogitem = session.query(Item).filter_by(id=item_id).one()
    return jsonify(catalogitem=catalogitem.serialize)


# list all the catalogs in the database
@app.route('/catalog/JSON')
def catalogJSON():
    catalogs = session.query(Catalog).all()
    return jsonify(catalogs=[i.serialize for i in catalogs])


# show the catalog list
@app.route('/')
@app.route('/catalog')
def main_page():
    # query the catalog names
    catalog = session.query(Catalog).order_by(asc(Catalog.name))
    if 'username' not in login_session:
        return render_template('publicindex.html', catalog=catalog)
    else:
        return render_template('index.html', catalog=catalog)


# create a new catalog
@app.route('/catalog/new', methods=['GET', 'POST'])
def newCatalogItem():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Catalog(
            name=request.form['name'], user_id=login_session.get('user_id'))
        session.add(newItem)
        flash('New Catalog %s added successfully' % newItem.name)
        session.commit()
        return redirect(url_for('main_page'))
    else:
        return render_template('newcatalog.html')


# edit an existing catalog
@app.route('/catalog/<int:catalog_id>/edit', methods=['GET', 'POST'])
def editCatalog(catalog_id):
    editedCatalog = session.query(Catalog).filter_by(id=catalog_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedCatalog.user_id != login_session['user_id']:
        flash('Not allowed to edit this itemn!')
        return redirect(url_for('main_page'))
    if request.method == 'POST':
        if request.form['name']:
            editedCatalog.name = request.form['name']
            flash('Catalog successfully edited %s' % editedCatalog.name)
            return redirect(url_for('main_page'))
    else:
        return render_template('editcatalog.html', catalog=editedCatalog)


# delete a catalog
@app.route('/catalog/<int:catalog_id>/delete', methods=['GET', 'POST'])
def deleteCatalog(catalog_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalogtoDelete = session.query(Catalog).filter_by(id=catalog_id).one()
    if catalogtoDelete.user_id != login_session['user_id']:
        return redirect(url_for('main_page', catalog_id=catalogtoDelete))
    if request.method == 'POST':
        session.delete(catalogtoDelete)
        flash('%s was successfully deleted' % catalogtoDelete.name)
        session.commit()
        return redirect(url_for('main_page', catalog_id=catalog_id))
    else:
        return render_template('deletecatalog.html', catalog=catalogtoDelete)


# display a catalog item
@app.route('/catalog/<int:catalog_id>')
@app.route('/catalog/<int:catalog_id>/item')
def item_page(catalog_id):
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    creator = getUserInfo(catalog.user_id)
    items = session.query(Item).filter_by(catalog_id=catalog_id).all()
    # render the items list
    return render_template
    ('items.html', catalog=catalog, items=items, creator=creator)


# create a item for a catagory
@app.route('/catalog/<int:catalog_id>/item/new', methods=['GET', 'POST'])
def newitem_page(catalog_id):
    # catagory it belongs to
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':
        newItem = Item(
            name=request.form['name'], description=request.form['description'],
            catalog_id=catalog_id)
        session.add(newItem)
        session.commit()
        flash('New catalog item %s added!', (newItem.name))
        # return redirect(url_for('main_page'))
        return redirect(url_for('item_page', catalog_id=catalog_id))
    else:
        return render_template('newitem.html', catalog_id=catalog_id)


# edit catalog item
@app.route(
    '/catalog/<int:catalog_id>/item/<int:item_id>/edit',
    methods=['GET', 'POST'])
def edititem_page(catalog_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    if catalog.user_id != login_session['user_id']:
        flash('Not allowed to edit this itemn!')
        return (redirect(url_for('main_page')))
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash('Menu Items Added')
        return redirect(url_for('item_page', catalog_id=catalog_id))
    else:
        return render_template(
            'edititem.html', catalog_id=catalog_id,
            item_id=item_id, item=editedItem)


# delete catalog item
@app.route(
    '/catalog/<int:catalog_id>/item/<int:item_id>/delete',
    methods=['GET', 'POST'])
def deleteitem_page(catalog_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if catalog.user_id != login_session['user_id']:
        flash('Not allowed to edit this itemn!')
        return (redirect(url_for('main_page')))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('menu item deleted')
        return redirect(url_for('item_page', catalog_id=catalog_id))
    else:
        return render_template('deleteitem.html', item=itemToDelete)


# disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']

        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("you have successfully logged out")
        return redirect(url_for('main_page'))
    else:
        flash("you were logged out")
        return redirect(url_for('main_page'))


# helper method create a user if they do not exist
def createUser(login_session):
    newUser = User(
        name=login_session.get('username'), email=login_session.get('email'),
        picture=login_session.get('picture'))
    session.add(newUser)
    session.commit()
    return newUser.id


# get user information for a logged in user
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# get the users email
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        print "user: %s" % user
        return user.id
    except:
        return None


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0')
