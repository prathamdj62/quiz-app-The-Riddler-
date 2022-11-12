import math
import os
from functools import wraps
import mysql.connector
from flask import Flask, render_template, url_for, request, g, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

sql = mysql.connector.connect(
        host="b9vaclvircawegwho7zq-mysql.services.clever-cloud.com",
        user="ubekknzap7t50jhg",
        passwd="mBZARSVCORUzGyDeW0IE",
        database="b9vaclvircawegwho7zq",
        port=3306
    )


@app.teardown_appcontext
def close_dbconnection(error):
    if hasattr(g,'newriddler_db'):
        g.newriddler_db.close()



def get_current_user():
    user_result = None
    if 'user' in session:
        user = session['user']
        db = sql.cursor()
        db.execute("select * from user where name = %s", [user])
        user_result = db.fetchone()
        db.close()

    return user_result

def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'user' in session:
            return test(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    user = get_current_user()

    print(user)
    db = sql.cursor()
    db.execute("select questions.id, questions.question_text, requester.name as requester_name,"
                                 "master.name as master_name from questions join user as requester on "
                                 "requester.id = questions.asked_by_id join user as master on master.id = questions.teacher_id where "
                                 "questions.answer_text is not null")
    question_result = db.fetchall()
    per_page = 3
    last = math.ceil(len(question_result) / per_page)
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    question_result = question_result[(page - 1) * per_page: (page - 1) * per_page + per_page]
    if (page == 1):
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif (page == last):
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)
    return render_template("Home.html", user=user, questions=question_result, prev=prev, next=next)

@app.route('/login', methods = ["POST","GET"])
def login():
    user = get_current_user()
    error = None
    if request.method == "POST":
        name = request.form['name']
        password = request.form['password']

        db = sql.cursor()
        db.execute("select * from user where name = %s", [name])
        person_from_database = db.fetchone()


        if person_from_database:
            if check_password_hash(person_from_database[2], password):
                session['user'] = person_from_database[1]
                return redirect(url_for('index'))

            else:
                error = "Invalid username or password"
                return render_template('login.html', error = error)

        else:
            error = "Invalid username or password"
            return render_template('login.html', error = error)

    return render_template("login.html", user = user, error = error)

@app.route('/register', methods = ["POST","GET"])
def register():
    user = get_current_user()
    error = None
    if request.method == "POST":
        db = sql.cursor()
        name = request.form['name']
        name = name.replace(" ","")
        password = request.form['password']

        db.execute("select * from user where name = %s", [name])
        existing_user = db.fetchone()

        if existing_user:
            error = "Username already taken!"
            return render_template("register.html", error = error)

        for x in password:
            if x == " ":
                error = "Password cannot contain spaces"
                return render_template("register.html", error=error)
                break

        hashed_password = generate_password_hash(password, method='sha256')
        db.execute("insert into user (name,password, teacher, admin) values(%s,%s,%s,%s)",
                   [name, hashed_password,'0','0'])
        sql.commit()
        session['user'] = name
        return redirect(url_for('index'))

    return render_template("register.html", user = user)


@app.route('/askquestions', methods=["POST","GET"])
@login_required
def askquestions():
    user = get_current_user()
    db = sql.cursor()
    if request.method == "POST":
        question = request.form['question']
        teacher = request.form['teacher']
        db.execute("insert into questions (question_text, asked_by_id, teacher_id) values (%s,%s,%s)",
                   [question, user[0], teacher])
        sql.commit()
        return redirect(url_for("index"))
    db.execute("select * from user where teacher = 1")
    teachers = db.fetchall()
    return render_template("askquestions.html", user = user, teachers = teachers)


@app.route('/unansweredquestions')
@login_required
def unansweredquestions():
    user = get_current_user()
    db = sql.cursor()
    db.execute("select questions.id,questions.question_text, user.name from questions"
                                 " join user on user.id = questions.asked_by_id "
                                 "where questions.answer_text is null and questions.teacher_id = %s",[user[0]])
    allquestions = db.fetchall()
    print(allquestions)
    return render_template("unansweredquestions.html", user = user, allquestions = allquestions)



@app.route('/answer/<question_id>', methods=["POST","GET"])
@login_required
def answer(question_id):
    user = get_current_user()
    db = sql.cursor()
    if request.method == "POST":
        db.execute("update questions set answer_text = %s where id = %s",[request.form['answer'], question_id])
        sql.commit()
        return redirect(url_for('unansweredquestions'))
    query = ("select id, question_text from questions where id= %s")
    data = [(question_id)]
    db.execute(query,data)
    question = db.fetchone()
    return render_template("answer.html",user = user, question = question)


@app.route('/myquestions', methods=["POST","GET"])
@login_required
def myquestions():
    user = get_current_user()
    db = sql.cursor()
    db.execute("select questions.id,questions.question_text, questions.answer_text, master.name as name from questions " 
                      "join user on user.id = questions.asked_by_id join user as master on master.id = questions.teacher_id  where questions.answer_text is not null " 
                      "and questions.asked_by_id = %s",[user[0]])
    allquestions = db.fetchall()
    return render_template("myquestions.html", user=user, allquestions=allquestions)




@app.route('/allusers', methods = ["POST","GET"])
@login_required
def allusers():
    user = get_current_user()
    db = sql.cursor()
    db.execute("select * from user")
    per_page = 5
    allusers = db.fetchall()
    last = math.ceil(len(allusers)/per_page)
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page = 1
    page=int(page)
    allusers = allusers[(page-1) * per_page: (page-1) * per_page + per_page]
    if (page==1):
        prev="#"
        next="/allusers?page="+str(page+1)
    elif(page==last):
        prev = "/allusers?page="+str(page-1)
        next="#"
    else:
        prev = "/allusers?page=" + str(page - 1)
        next = "/allusers?page=" + str(page + 1)


    return render_template("allusers.html", user = user, allusers = allusers, prev=prev, next=next)


@app.route('/promote/<int:id>', methods = ["POST","GET"])
@login_required
def promote(id):
    user = get_current_user()
    if request.method == "GET":
        db = sql.cursor()
        data = [(id)]
        query=("update user set teacher= case teacher when 0 then 1 else 0 end where id = %s")
        db.execute(query,data)
        sql.commit()
        return redirect(url_for('allusers'))


    return render_template("allusers.html", user = user)



@app.route('/delete/<int:id>', methods = ["POST","GET"])
@login_required
def delete(id):
    user = get_current_user()
    if request.method == "GET":
        db = sql.cursor()
        db.execute("delete from user where id =%s",[(id)])
        sql.commit()
        return redirect(url_for('allusers'))


    return render_template("allusers.html", user = user)

@app.route('/make_admin/<int:id>', methods = ["POST","GET"])
@login_required
def make_admin(id):
    user = get_current_user()
    if request.method == "GET":
        db = sql.cursor()
        db.execute("update user set admin= case admin when 0 then 1 else 0 end where id =%s",[(id)])
        sql.commit()
        return redirect(url_for('allusers'))


    return render_template("allusers.html", user = user)

@app.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    print("abc")
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug = True)