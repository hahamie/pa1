######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Mona Jalal (jalal@bu.edu), Baichuan Zhou (baichuan@bu.edu) and Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://g
# ithub.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask.ext.login as flask_login
import datetime
from werkzeug.utils import secure_filename
# for image uploading
# from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__,static_url_path = "/static", static_folder = "static")
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'PHOTOSHARESOLUTION'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT EMAIL FROM USER")
users = cursor.fetchall()

def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT EMAIL FROM USER")
    return cursor.fetchall()


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()

    cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL = %s", email)
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
    # The request method is POST (page is recieving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    # check if email is registered
    if cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL= %s", email):
        data = cursor.fetchall()
        pwd = str(data[0][0])
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user)  # okay login in user
            return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

    # information did not match
    return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
    flask_login.logout_user()
    users = getTopTen()
    return render_template('hello.html',users=users, message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        f_name =  request.form.get('first_name')
        l_name = request.form.get('last_name')
        hometown = request.form.get('hometown')
        dob = request.form.get('birthday')
        gender = request.form.get('gender')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        #print(cursor.execute("INSERT INTO USER (email, PASSWORD) VALUES ('email', 'password')"))

        #cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption) VALUES (%s, %s, %s)",
        #               (photo_data, uid, caption))

        L = "L";
        F = "F";
        print(cursor.execute("INSERT INTO USER (GENDER, EMAIL, PASSWORD, DOB, HOMETOWN, FNAME, LNAME) VALUES (%s , %s, %s, %s, %s, %s, %s)", (gender, email, password, dob, hometown, f_name, l_name)))
        conn.commit()
        # log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        users = getTopTen()
        return render_template('hello.html', users=users,name=(email.split("@"))[0], message='Account Created!')
    else:
        print("couldn't find all tokens")
        return flask.redirect(flask.url_for('register'))


def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT PID, CAPTION FROM PHOTO WHERE AID IN (SELECT AID FROM ALBUM WHERE UID = %s)", uid)
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]

def getAlbumPhotos(aid):
    cursor = conn.cursor()
    cursor.execute("SELECT PID, CAPTION FROM PHOTO WHERE AID = %s", (aid))
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]

def getTagPhotos(tag):
    cursor = conn.cursor()
    cursor.execute("SELECT PID, CAPTION FROM PHOTO WHERE PID IN (SELECT PID FROM ASSOCIATE WHERE HASHTAG = %s)", (tag))
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]

def getUserTagPhotos(uid,tag):
    cursor = conn.cursor()
    cursor.execute("SELECT PID, CAPTION FROM PHOTO AS P1 WHERE P1.PID IN (SELECT P.PID FROM ASSOCIATE AS A,ALBUM AS AL,PHOTO AS P WHERE HASHTAG = %s AND AL.UID = %s AND P.AID=AL.AID AND P.PID=A.AID)", (tag,uid))
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]

def getMayLikePhoto(uid):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT A1.PID,P1.CAPTION,COUNT(A1.PID) AS CON FROM PHOTO AS P1,ASSOCIATE AS A1,ALBUM AS AL1 WHERE A1.PID=P1.PID AND P1.AID=AL1.AID AND AL1.UID<> %s AND A1.HASHTAG IN(SELECT A.HASHTAG FROM (SELECT A.HASHTAG,COUNT(A.HASHTAG) AS CON FROM PHOTO AS P,ASSOCIATE AS A,ALBUM AS AL WHERE AL.UID= %s AND P.PID =A.PID AND P.AID=AL.AID GROUP BY A.HASHTAG ORDER BY CON DESC LIMIT 5) A) GROUP BY A1.PID ORDER BY CON DESC LIMIT 5;",(uid,uid))
    return cursor.fetchall()


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT UID  FROM USER WHERE EMAIL = %s", email)
    return cursor.fetchone()[0]


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT EMAIL  FROM USER WHERE EMAIL = %s", email):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True

# end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    users = getTopTen()
    return render_template('hello.html', users=users,name=flask_login.current_user.id.split('@')[0], message="Here's your profile")


# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def tagExist(tag):
    cursor = conn.cursor()
    if cursor.execute("SELECT HASHTAG  FROM TAG WHERE HASHTAG = %s", tag):
        # this means there are greater than zero entries with that email
        return True
    else:
        return False

def getTag(tag):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO TAG (HASHTAG) VALUES (%s)", tag)
    conn.commit()

def addAssociate(tag,pid):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ASSOCIATE (HASHTAG,PID) VALUES (%s,%s)", (tag,pid))
    conn.commit()


def getTopTen():
    cursor = conn.cursor()
    cursor.execute("SELECT B.UID,SUM(B.CON) AS S FROM (SELECT U.UID,COUNT(P.PID) AS CON FROM PHOTO AS P, ALBUM AS AL,USER AS U WHERE AL.AID = P.AID AND U.UID=AL.UID GROUP BY U.UID UNION SELECT U.UID,COUNT(C.CONTENT) AS CON FROM COMMENT AS C, USER AS U WHERE U.UID = C.UID GROUP BY U.UID) B GROUP BY B.UID ORDER BY S DESC LIMIT 10")
    return cursor.fetchall()


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        app.config['UPLOAD_FOLDER'] = 'static/'
        imgfile = request.files['photo']
        caption = request.form.get('caption')
        tag = request.form.get('tag')
        tags = tag.split(' ')
        for hashtag in tags:
            if not (tagExist(hashtag)):
                getTag(hashtag)
        #photo_data = base64.standard_b64encode(imgfile.read())
        cursor = conn.cursor()
        aid = request.form.get('album')
        #cursor.execute(
        #    "INSERT INTO Pictures (imgdata, user_id, caption) VALUES ('photo_data', 'uid', 'caption')")
        cursor.execute("INSERT INTO PHOTO (CAPTION, AID) VALUES (%s, %s)",
                       (caption,aid))
        pid = cursor.lastrowid
        conn.commit()
        file = secure_filename(imgfile.filename)

        suffix = file.split('.')[1]
        filename =  str(pid) +'.'+suffix
        imgfile.save(os.path.join(app.config['UPLOAD_FOLDER'], file))
        os.rename('static/'+ file, 'static/' + filename)
        #cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption) VALUES (?, ?, ?)", (photo_data, uid, caption))
        conn.commit()
        for hashtag in tags:
            addAssociate(hashtag, pid)
        return render_template('my_photo.html', message='Photo uploaded!',modify='yes', login='yes',photos=getUsersPhotos(uid),)
    # The method is GET so we return a  HTML form to upload the a photo.
    else:
        cursor = conn.cursor()
        uid = getUserIdFromEmail(flask_login.current_user.id)
        cursor.execute("SELECT NAME,AID FROM ALBUM WHERE UID = %s", uid)
        album = cursor.fetchall()
        return render_template('upload.html',albums = album)


# end photo uploading code


# default page
@app.route("/", methods=['GET'])
def hello():
    users = getTopTen()
    return render_template('hello.html', users=users, message='Welecome to Photoshare')

@app.route("/", methods=['POST'])
def hello1():
    comment = request.form.get('search')
    cursor = conn.cursor()
    cursor.execute("SELECT U.EMAIL, COUNT(C.CONTENT) AS CON FROM USER AS U,COMMENT AS C WHERE CONTENT = %s AND U.UID=C.UID GROUP BY U.EMAIL ORDER BY CON DESC ", comment)
    emails = cursor.fetchall()
    users = getTopTen()
    if len(emails) == 0:
        return render_template('hello.html',users=users, message='No user found')
    else:
        names=[]
        for email in emails:
            name=email[0].split('@')[0] + ': ' + str(email[1])
            print(name)
            names.append(name)
        return render_template('hello.html', users=users, names=names, message='User found')

def getAlbumName(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT NAME, AID FROM ALBUM WHERE UID = %s", uid)
    return cursor.fetchall()

def getPubAlbum():
    cursor = conn.cursor()
    cursor.execute("SELECT NAME,AID FROM ALBUM")
    return cursor.fetchall()

def deletePhoto(aid):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PHOTO WHERE AID = %s",aid)
    conn.commit()

def deleteSelectPhoto(pid):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PHOTO WHERE PID = %s",pid)
    conn.commit()

def deleteAlbum(aid):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ALBUM WHERE AID = %s",aid)
    conn.commit()


def deleteAssociate(pid):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ASSOCIATE WHERE PID = %s",pid)
    conn.commit()

def deleteAllAssociate(aid):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ASSOCIATE WHERE PID IN (SELECT PID FROM PHOTO WHERE AID = %s)",aid)
    conn.commit()

def isAlbumUnique(name,uid):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT NAME FROM ALBUM WHERE NAME = %s AND UID = %s", (name,uid)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True
#album page
@app.route('/album',methods=['GET','POST'])
#@flask_login.login_required
def album():
    if request.method == 'GET':
        albums = getPubAlbum()
        if flask_login.current_user.is_authenticated:
            return render_template('album.html',albums = albums, login =flask_login.current_user.is_authenticated,view = 'yes',  message= 'Here is albums')
        else:
            return render_template('album.html',albums = albums, message= 'Here is albums')

@app.route('/my_album',methods=['GET','POST'])
@flask_login.login_required
def my_album():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    if request.method == 'POST':
        list = request.form.getlist('list')
        if request.form['submit'] == 'Delete':
            for aid in list:
                deleteAllAssociate(aid)
                deletePhoto(aid)
                deleteAlbum(aid)
            album = getAlbumName(uid)
            return render_template('album.html',albums=album, modify = 'yes',login = 'yes',message='Here is your albums')
        else:
            if(len(list)>1):
                album = getAlbumName(uid)
                return render_template('album.html', albums=album, modify='yes', login='yes',
                                       message='You can only modify one album each time')
            else:
                aid = list[0]
                return render_template('modify_album.html', aid=aid, message='Modify album')
    else:
        album = getAlbumName(uid)
        print(album)
        return render_template('album.html', albums=album, modify = 'yes',login = 'yes',message='Here is your albums')

@app.route('/create_album',methods=['GET','POST'])
def new_album():
    if request.method == 'POST':
        name = request.form.get('name')
        uid = getUserIdFromEmail(flask_login.current_user.id)
        if not isAlbumUnique(name,uid):
            return render_template('create_album.html',message ='Album name has been used')
        time = datetime.datetime.now()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ALBUM (NAME, DOC, UID) VALUES (%s, %s, %s)",
                       (name, time,uid))
        conn.commit()
        album = getAlbumName(uid)
        return render_template('/album.html',albums = album, modify = 'yes',login = 'yes',message='Album created!')
    else:
        return render_template('create_album.html')

@app.route('/modify_album/<int:a_aid>', methods=['GET', 'POST'])
def modify_album(a_aid):
    if request.method == 'POST':
        name = request.form.get('name')
        uid = getUserIdFromEmail(flask_login.current_user.id)
        aid=a_aid
        if not isAlbumUnique(name, uid):
            return render_template('modify_album.html', aid=aid, message='Album name has been used')
        cursor = conn.cursor()
        cursor.execute("UPDATE ALBUM SET NAME = %s where AID = %s", (name,aid))
        conn.commit()
        album = getAlbumName(uid)
        return render_template('/album.html', albums=album,modify = 'yes',login = 'yes', message='Album modified!')
    else:
        return render_template('create_album.html')


# Test Showing Photos
@app.route("/show_photos", methods=['GET'])
def showPhotos():
    cursor = conn.cursor()
    cursor.execute("SELECT PID, CAPTION FROM PHOTO")
    photos = cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]
    lists = []
    for photo in photos:
        lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
    if flask_login.current_user.is_authenticated:
        return render_template('show_photos.html', login =flask_login.current_user.is_authenticated, com = 'yes',view = 'yes', photos=lists,message = 'show all photos')
    else:
        return render_template('show_photos.html', photos=lists,com = 'yes',message='show photos')

def getUidByPid(pid):
    cursor = conn.cursor()
    cursor.execute("SELECT A.UID FROM (PHOTO AS P,ALBUM AS A) WHERE p.PID = %s AND A.AID=P.AID", pid)
    return cursor.fetchone()[0]

def getGuestUid():
    cursor = conn.cursor()
    guest = ' '
    cursor.execute("SELECT UID FROM USER WHERE PASSWORD = %s AND FNAME= %s AND LNAME = %s", (guest,guest,guest))
    return cursor.fetchone()[0]

def alreadyLiked(uid,pid):
    cursor = conn.cursor()
    if cursor.execute("SELECT DOC  FROM LIKETABLE WHERE UID = %s AND PID = %s", (uid,pid)):
        # this means there are greater than zero entries with that email
        return True
    else:
        return False


@app.route("/show_photos/<int:p_pid>", methods=['POST'])
def show_Photos(p_pid):
    pid = p_pid
    time = datetime.datetime.now()
    if request.form['submit'] == 'Comment':
        comment = request.form.get('comment')

        c_uid = getUidByPid(pid)
        if flask_login.current_user.is_authenticated:
            uid = getUserIdFromEmail(flask_login.current_user.id)
            if uid==c_uid:
                cursor = conn.cursor()
                cursor.execute("SELECT PID, CAPTION FROM PHOTO")
                photos = cursor.fetchall()
                lists=[]
                for photo in photos:
                    lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
                return render_template('show_photos.html',login =flask_login.current_user.is_authenticated, com = 'yes',view = 'yes', photos=lists,message = 'cannot comment on own photo')
            else:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO COMMENT (CONTENT, DOC, UID, PID) VALUES (%s, %s, %s, %s)",(comment, time, uid, pid))
                conn.commit()
                cursor.execute("SELECT PID, CAPTION FROM PHOTO")
                photos = cursor.fetchall()
                lists=[]
                for photo in photos:
                    lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
                return render_template('show_photos.html',login =flask_login.current_user.is_authenticated, com = 'yes',view = 'yes', photos=lists,message = 'Comment posted')
        else:
            uid = getGuestUid()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO COMMENT (CONTENT, DOC, UID, PID) VALUES (%s, %s, %s, %s)",(comment, time, uid, pid))
            conn.commit()
            cursor.execute("SELECT PID, CAPTION FROM PHOTO")
            photos = cursor.fetchall()
            lists=[]
            for photo in photos:
                lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
            return render_template('show_photos.html',com='yes', photos=lists, message='Comment posted')
    else:
        if flask_login.current_user.is_authenticated:
            uid = getUserIdFromEmail(flask_login.current_user.id)
            if alreadyLiked(uid,pid):
                cursor = conn.cursor()
                cursor.execute("SELECT PID, CAPTION FROM PHOTO")
                photos = cursor.fetchall()
                lists = []
                for photo in photos:
                    lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
                mayLikePhotos = getMayLikePhoto(uid)
                likelists = []
                for photo in mayLikePhotos:
                    likelists.append(list((photo[0], photo[1],photo[2], tuple([str(photo[0])])[0])))
                return render_template('show_photos.html', com='yes', login='yes',photos=lists, view='yes',maylike = likelists,message='You have already liked photo')
            else:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO LIKETABLE (DOC, UID, PID) VALUES (%s, %s, %s)",
                               (time, uid, pid))
                conn.commit()
                cursor.execute("SELECT PID, CAPTION FROM PHOTO")
                photos = cursor.fetchall()
                lists=[]
                for photo in photos:
                    lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
                mayLikePhotos = getMayLikePhoto(uid)
                likelists = []
                for photo in mayLikePhotos:
                    likelists.append(list((photo[0], photo[1], photo[2], tuple([str(photo[0])])[0])))
                return render_template('show_photos.html', com='yes', login='yes',photos=lists, view='yes',maylike = likelists, message='Liked')
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT PID, CAPTION FROM PHOTO")
            photos = cursor.fetchall()
            lists=[]
            for photo in photos:
                lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
            return render_template('show_photos.html', com='yes', photos=lists, message='You have to log in first')

@app.route("/my_photos", methods=['GET','POST'])
@flask_login.login_required
def my_photos():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    if request.method == 'POST':
        l = request.form.getlist('l')
        if request.form['submit'] == 'Delete':
            for pid in l:
                deleteSelectPhoto(pid)
                deleteAssociate(pid)
            photos = getUsersPhotos(uid)
            lists = []
            for photo in photos:
                lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
            return render_template('my_photo.html',login='yes',modify = 'yes', photos=lists,message = 'get own photo')
        else:
            if (len(l) > 1):
                photos = getUsersPhotos(uid)
                lists = []
                for photo in photos:
                    lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
                return render_template('my_photo.html', photos=lists, modify='yes', login='yes',
                                       message='You can only modify one photo each time')
            else:
                pid = list[0]
                return render_template('modify_photo.html', pid=pid, message='Modify photo')

    else:
        photos = getUsersPhotos(uid)
        lists = []
        for photo in photos:
            lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
        return render_template('my_photo.html',login='yes',modify = 'yes', photos=lists, message = 'View photos')

@app.route("/album_photos/<a_name>/<int:a_aid>", methods=['GET'])
def albumPhotos(a_name,a_aid):
    aid = a_aid
    photos = getAlbumPhotos(aid)
    lists = []
    for photo in photos:
        lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
    return render_template('show_photos.html',  photos=lists,message = 'View album photo')

def getPopulartags():
    cursor = conn.cursor()
    cursor.execute("SELECT HASHTAG,COUNT(HASHTAG) AS CON FROM ASSOCIATE GROUP BY HASHTAG ORDER BY CON DESC LIMIT 5; ")
    return cursor.fetchall()

@app.route('/modify_photo/<int:p_pid>', methods=['GET', 'POST'])
def modify_photo(p_pid):
    if request.method == 'POST':
        caption = request.form.get('caption')
        uid = getUserIdFromEmail(flask_login.current_user.id)
        pid=p_pid
        cursor = conn.cursor()
        cursor.execute("UPDATE PHOTO SET CAPTION = %s where PID = %s", (caption,pid))
        conn.commit()
        photos = getUsersPhotos(uid)
        lists = []
        for photo in photos:
            lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
        return render_template('/my_photo.html', photos=lists,modify = 'yes',login = 'yes', message='Photo modified!')
    else:
        return render_template('modify_photo.html')

@app.route("/tag", methods=['GET','POST'])
def tags():
    if request.method == 'POST':
        tags = request.form.get('search')
        taglist = tags.split(' ')
        photo=()
        for tag in taglist:
            tag='#'+tag
            photo = photo + getTagPhotos(tag)
        lists = []
        for p in photo:
            lists.append(list((p[0], p[1], tuple([str(p[0])])[0])))
        return render_template('show_photos.html', photos=lists, message = 'Show all tag photo')
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT HASHTAG FROM TAG")
        tags = cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]
        if flask_login.current_user.is_authenticated:
            return render_template('show_tags.html',  tags=tags,pt =getPopulartags(), login = 'yes', message = 'View photos by tag')
        else:
            return render_template('show_tags.html', tags=tags, message='View photos by tag')

@app.route("/tag_photos/<tag_name>", methods=['GET'])
def tagPhotos(tag_name):
    tag = tag_name
    photos = getTagPhotos(tag)
    lists = []
    for photo in photos:
        lists.append(list((photo[0], photo[1], tuple([str(photo[0])])[0])))
    return render_template('show_photos.html',  photos=lists,message = 'show photo by tag')

@app.route("/my_tag", methods=['GET','POST'])
@flask_login.login_required
def myTags():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    if request.method == 'POST':
        tags = request.form.get('search')
        taglist = tags.split(' ')
        photo=()
        for tag in taglist:
            tag='#'+tag
            photo = photo + getUserTagPhotos(tag,uid)
        lists = []
        for p in photo:
            lists.append(list((p[0], p[1], tuple([str(p[0])])[0])))
        return render_template('my_photo.html', photos=list,message='show my tag photo')
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT (A.HASHTAG) FROM ASSOCIATE AS A WHERE A.PID IN (SELECT P.PID FROM (PHOTO AS P,ALBUM AS A) WHERE (A.UID = %s AND P.AID = A.AID))",uid)
        tags = cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]
        return render_template('show_tags.html', tags=tags,  message='My tag')


@app.route("/comment/<int:p_pid>", methods=['GET'])
def comment(p_pid):
    pid = p_pid;
    cursor = conn.cursor()
    cursor.execute("SELECT CONTENT FROM COMMENT WHERE PID = %s",pid)
    comment = cursor.fetchall()
    cursor.execute("SELECT CAPTION FROM PHOTO WHERE PID = %s", pid)
    photo = cursor.fetchone()
    return render_template('comment.html', pid = str(pid), comments=comment,photo=photo)

@app.route("/like/<int:p_pid>", methods=['GET'])
def like(p_pid):
    pid = p_pid;
    cursor = conn.cursor()
    cursor.execute("SELECT UID FROM LIKETABLE WHERE PID = %s",pid)
    uids = cursor.fetchall()
    names=[]
    for uid in uids:
        cursor.execute("SELECT EMAIL FROM USER WHERE UID = %s", uid)
        name = cursor.fetchone()[0]
        name = name.split('@')[0]
        names.append(name)
    cursor.execute("SELECT CAPTION FROM PHOTO WHERE PID = %s", pid)
    photo = cursor.fetchone()
    cursor.execute("SELECT COUNT(PID) FROM LIKETABLE WHERE PID = %s", pid)
    num_like = cursor.fetchone()
    return render_template('like.html', names=names,pid = str(pid),photo=photo,num=num_like)

# begin display friend list code
def getFriendList(uid):
    cursor = conn.cursor()

    cursor.execute("SELECT UID2 FROM FRIENDSHIP WHERE UID1 = %s", uid)
    uids = cursor.fetchall()
    uid2s = []
    for uid2 in uids:
        ab = uid2[0]
        uid2s.append(ab)
    return uid2s

def getFirstNames(friendList):
    cursor = conn.cursor()
    FirstNames = []
    for uid in friendList:
        cursor.execute("SELECT FNAME FROM USER WHERE UID = %s", uid)
        firstname = cursor.fetchone()
        FirstNames.append(firstname[0])
    return FirstNames

def getEmailFirst():
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor.execute("SELECT EMAIL, FNAME FROM USER WHERE UID IN (SELECT UID2 FROM FRIENDSHIP WHERE UID1 = %s)", uid)
    datas = cursor.fetchall()
    print(datas)
    return datas

@app.route('/friendship')
@flask_login.login_required
def upload_friendlist():
        datas = getEmailFirst();
        conn.commit()
        return render_template('friendship.html', datas =datas)

#end view friend list


# begin add friends

def isEmailExist(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    print(email)

    uid = getUserIdFromEmail(flask_login.current_user.id)
    print(email)
    print(getFriendList(uid))
    cursor.execute("SELECT UID  FROM USER WHERE EMAIL = %s ",email)
    print(cursor.fetchall())
    cursor.execute("SELECT U.UID  FROM USER U WHERE U.EMAIL = %s AND U.UID NOT IN(SELECT UID2 FROM FRIENDSHIP F WHERE F.UID1 = %s)", (email, uid))
    condition = cursor.fetchall()
    print(condition)
    if email and email != flask_login.current_user.id and condition:
        # this means there are greater than zero entries with that email
        return True
    else:
        return False

def recommendFriend():
    cursor = conn.cursor()
    uid1 = getUserIdFromEmail(flask_login.current_user.id)
    print(uid1)
    fnames= []
    emails = []
    lnames =[]
    cursor.execute("SELECT F1.UID2 FROM FRIENDSHIP F1 WHERE F1.UID1 IN(SELECT F2.UID2 FROM FRIENDSHIP F2 WHERE F2.UID1 = %s)",uid1)
    data = cursor.fetchall()
    print(data)
    cursor.execute(
        "SELECT U.EMAIL, U.FNAME, U.LNAME FROM USER U WHERE U.UID <> %s and U.UID IN(SELECT F1.UID2 FROM FRIENDSHIP F1 WHERE F1.UID1 IN(SELECT F2.UID2 FROM FRIENDSHIP F2 WHERE F2.UID1 = %s))",
        (uid1,uid1))
    datas = cursor.fetchall()
    print(datas)
    for data in datas:
        emails.append(data[0])
        fnames.append(data[1])
        lnames.append(data[2])
        print(data)

    return datas



@app.route("/addFriends", methods=['GET'])
def addFriends():
    datas = recommendFriend()

    return render_template('addFriends.html',supress = 'True',datas = datas)

@app.route("/addFriends", methods=['POST'])
def add_Friends():
    try:
        email = request.form.get('email')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('addFriends'))
    cursor = conn.cursor()


    if request.form['submit'] == 'Submit':

        test = isEmailExist(email)
        if test:
            # print(cursor.execute("INSERT INTO USER (email, PASSWORD) VALUES ('email', 'password')"))

            # cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption) VALUES (%s, %s, %s)",
            #               (photo_data, uid, caption))

            cursor.execute("SELECT EMAIL, FNAME, LNAME  FROM USER WHERE EMAIL = %s", email)
            a = cursor.fetchall()
            name = a[0][0]
            FNAME = a[0][1]
            LNAME = a[0][2]
            conn.commit()

            return render_template('addFriends.html', name=name, FNAME=FNAME,LNAME = LNAME,supress = 'True')
        else:
            print("couldn't find all tokens")
            return render_template('addFriends.html')

@app.route('/addFriends/<email2>',methods=['GET'])
@flask_login.login_required
def upload_friendlist2(email2):
    cursor = conn.cursor()
    uid1 = getUserIdFromEmail(flask_login.current_user.id)
    cursor.execute("SELECT UID FROM USER WHERE EMAIL = %s", email2)
    uid2 = cursor.fetchall()
    cursor.execute("INSERT INTO FRIENDSHIP (UID1, UID2) VALUES (%s, %s )", (uid1, uid2))
    return upload_friendlist()


# end FriendList code

if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)