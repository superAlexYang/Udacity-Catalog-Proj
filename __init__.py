
from flask import Flask, jsonify,render_template, request, redirect, jsonify, url_for, flash
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catagory, CatagoryItem, User
from functions_helper import *
import random, string

from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

import os

path = os.path.dirname(__file__)

app = Flask(__name__)
CLIENT_ID = json.loads(open(path+'/client_secrets.json', 'r').read())['web']['client_id']

engine = create_engine('postgresql://catalog:catalog123@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
@app.route('/index/')
def showShops():
	Catagorys = session.query(Catagory).all()
	return render_template("main.html",Catagorys = Catagorys, login_session = login_session )


@app.route('/index/<string:shop_ID>/')
def showItems(shop_ID):
	Catagory = session.query(Catagory).filter_by(id=shop_ID).one()
	user_id = Catagory.user_id
	user = session.query(User).filter_by(id = user_id).one()
	Catagorys = session.query(CatagoryItem).filter_by(shop_id=shop_ID).all()
	return render_template('Catagorys.html', Catagorys=Catagorys, Catagory=Catagory, user = user, login_session = login_session)


@app.route('/login/')
def login():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html',STATE=state, login_session = login_session)

		
@app.route('/gconnect', methods=['POST'])
def gconnect():
    print 'received state of %s' % request.args.get('state')
    print 'login_sesion["state"] = %s' % login_session['state']
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = request.args.get('gplus_id')
    print "request.args.get('gplus_id') = %s" % request.args.get('gplus_id')
    code = request.data
    print "received code of %s " % code

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(path+'/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        
    except FlowExchangeError:
        response = make_response(json.dumps(
            'Failed to upgrade the authorization code.'
            ), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    credentials = credentials.to_json()            
    credentials = json.loads(credentials)         
    access_token = credentials['token_response']['access_token']     
    url = (
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
        % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials['id_token']['sub']
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
            'Current user is already connected.'
            ), 200)
        response.headers['Content-Type'] = 'application/json'

    # Store the access token in the session for later use.
    login_session['provider'] = 'google'
    response = make_response(json.dumps('Successfully connected user.', 200))

    print "#Get user info"
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials['token_response']['access_token'], 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    print login_session['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    # dimensions of the picture at login:
    output += ' " style = "width: 300px; height: \
        300px;border-radius: \
        50px;-webkit-border-radius: \
        150px;-moz-border-radius: 50px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route("/gdisconnect")
def gdisconnect():
    credentials = login_session.get('credentials')
    # Only disconnect a connected user.
    if not checkLogin(login_session):
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials['token_response']['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's session.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash('Successfully disconnected.')
        return redirect(url_for('showShops'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(json.dumps(
            'Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        flash('Failed to revoke token for given user.')
        return redirect(url_for('showShops'))


# Create a new shop
@app.route('/new/', methods=['GET', 'POST'])
def newShop():
	if not checkLogin(login_session):
		flash('You must login to create a Catagory shop')
		return redirect(url_for('showShops'))
	
	if request.method == 'POST':
		
		newShop = Catagory(name=request.form['name'],description = request.form['description'], user_id = login_session.get('user_id') )
		session.add(newShop)
		flash('New Catagory shop %s Successfully Created' % newShop.name)
		session.commit()
		return redirect(url_for('showShops'))
	else:
		return render_template('newshop.html',login_session = login_session)

# add a new Catagory to shop
@app.route('/index/<string:shop_ID>/add', methods=['GET', 'POST'])
def addNewCatagory(shop_ID):
	if not checkLogin(login_session):
		flash('You must login to create a Catagory shop')
		return redirect(url_for('showShops'))
	if request.method == 'POST':
		newCatagory = CatagoryItem(name=request.form['name'],
						description = request.form['description'], 
						user_id = login_session.get('user_id'), 
						price = request.form['price'], 
						shop_id = shop_ID)
		session.add(newCatagory)
		session.commit()
		flash('New Catagory %s has been successfully Created' % newCatagory.name)
		return redirect(url_for('showItems',shop_ID = shop_ID))
	else:
		return render_template('newCatagory.html',shop_ID = shop_ID,login_session = login_session)

# delete a Catagory from shop
@app.route('/index/<string:shop_ID>/<string:Catagory_ID>/delete')
def deleteCatagory(shop_ID,Catagory_ID):
	if not checkLogin(login_session):
		flash('You must login to manage a Catagory shop.')
		return redirect(url_for('showItems',shop_ID = shop_ID))
	login_user_id = getUserID(login_session['email'])
	CatagoryToDelete = session.query(CatagoryItem).filter_by(id=Catagory_ID).one()
	if CatagoryToDelete.user_id != login_user_id:
		flash("You can only manage your own shop.")
		return redirect(url_for('showItems',shop_ID = shop_ID))
	session.delete(CatagoryToDelete)
	session.commit()
	flash("You have managed your shop successfully.")
	return redirect(url_for('showItems',shop_ID = shop_ID))

# edit a Catagory
@app.route('/index/<string:shop_ID>/<string:Catagory_ID>/edit', methods=['GET', 'POST'])
def editCatagory(shop_ID,Catagory_ID):
	if not checkLogin(login_session):
		flash('You must login to manage a Catagory shop.')
		return redirect(url_for('showItems',shop_ID = shop_ID))
	login_user_id = getUserID(login_session['email'])
	CatagoryToEdite = session.query(CatagoryItem).filter_by(id=Catagory_ID).one()
	if CatagoryToEdite.user_id != login_user_id:
		flash("You can only manage your own shop.")
		return redirect(url_for('showItems',shop_ID = shop_ID))
	if request.method == 'POST':
		CatagoryToEdite.name = request.form['name']
		CatagoryToEdite.description = request.form['description']
		CatagoryToEdite.price = request.form['price']
		flash('%s has been successfully edited' % CatagoryToEdite.name)
		return redirect(url_for('showItems',shop_ID = shop_ID))
	else:
		return render_template('editCatagory.html',Catagory = CatagoryToEdite,login_session = login_session)

# edit a Catagory shop
@app.route('/index/<string:shop_ID>/edit', methods=['GET', 'POST'])
def editCatagory(shop_ID):
	if not checkLogin(login_session):
		flash('You must login to manage a Catagory shop.')
		return redirect(url_for('showItems',shop_ID = shop_ID))
	login_user_id = getUserID(login_session['email'])
	shopToEdit = session.query(Catagory).filter_by(id=shop_ID).one()
	if shopToEdit.user_id != login_user_id:
		flash("You can only manage your own shop.")
		return redirect(url_for('showItems',shop_ID = shop_ID))
	if request.method == 'POST':
		shopToEdit.name = request.form['name']
		shopToEdit.description = request.form['description']
		flash('%s has been successfully edited' % shopToEdit.name)
		return redirect(url_for('showItems',shop_ID = shop_ID))
	else:
		return render_template('editShop.html',Catagory = shopToEdit,login_session = login_session)

# delete a Catagory shop
@app.route('/index/<string:shop_ID>/delete/')
def deleteCatagory(shop_ID):
	if not checkLogin(login_session):
		flash('You must login to manage a Catagory shop.')
		return redirect(url_for('showItems',shop_ID = shop_ID))
	login_user_id = getUserID(login_session['email'])
	ShopToDelete = session.query(Catagory).filter_by(id=shop_ID).one()
	if ShopToDelete.user_id != login_user_id:
		flash("You can only delete your own shop.")
		return redirect(url_for('showShops'))
	session.delete(ShopToDelete)
	session.commit()
	flash("You have deleted your shop successfully.")
	return redirect(url_for('showShops'))


@app.route('/help/')
def help():
	return render_template("help.html")

#json APIs
@app.route('/index/<string:shop_ID>/JSON/')
def shopJSON(shop_ID):
    shops = session.query(Catagory).filter_by(id=shop_ID).one()
    Catagorys = session.query(CatagoryItem).filter_by(shop_id = shop_ID).all()
    return jsonify(Shop=shops.serialize, Catagorys = [g.serialize for g in Catagorys])


@app.route('/index/<string:shop_ID>/<string:Catagory_ID>/JSON/')
def CatagoryJSON(shop_ID,Catagory_ID):
    Catagory = session.query(CatagoryItem).filter_by(id=Catagory_ID).one()
    return jsonify(Catagory = Catagory.serialize)

if __name__ == '__main__':
	app.secret_key = 'super secret key'
	app.debug = True
	app.run(host = 'localhost', port = 5000)
