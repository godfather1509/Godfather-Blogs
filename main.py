from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_mail import Mail, Message
import datetime as datetime
import time, os
import json, math

with open(r"templates\config.json", "r") as c:
    data = json.load(c)
    # we will put url's, blog name, writer, passwords in .json file,
    # in future if we want to change any parameter we just edit config file
parameter = data["params"]
passwords = data["credentials"]

app = Flask(__name__)
app.config["SQLALCHEMY_BINDS"] = {
    "contacts": parameter["contact_db"],
    "posts": parameter["post_db"],
}
app.config["SECRET_KEY"] = passwords["password"]
app.config["UPLOAD_FOLDER"] = parameter["upload_location"]

db = SQLAlchemy(app)

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = passwords["username"]
app.config["MAIL_PASSWORD"] = passwords["password"]
app.config["MAIL_DEFAULT_SENDER"] = passwords["email"]

mail = Mail(app)


class Contact(db.Model):
    __bind_key__ = "contacts"
    Sr = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(20), nullable=False)
    msg = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    number = db.Column(db.String(12), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.datetime.now())


class Post(db.Model):
    __bind_key__ = "posts"
    Sr = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    sub_title = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(1500), nullable=False)
    background_image = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), default=time.strftime("%d %b %Y"))


@app.route("/")
def hello():
    # post = Post.query.all()[
    #     0 : parameter["no_of_posts"]
    # ]  # getting first 5 posts from database   
    posts = Post.query.filter_by().all()
    # post has all the rows in our database in list form each element is object of Post class
    last = math.ceil(len(posts) / int(parameter["no_of_posts"]))
    page = request.args.get("page")
    # This retrieves the page query parameter from the URL (e.g., /?page=2), which indicates the current page number.
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    # If page is not a number or is missing, it defaults to page 1. and typecast it to int
    posts = posts[(page - 1)* int(parameter["no_of_posts"]) : (page - 1)* int(parameter["no_of_posts"])+ int(parameter["no_of_posts"])]
    # This slicing operation selects only the posts relevant to the current page, based on the no_of_posts value.
    
    # Pagination Logic
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template(
        "index.html", parameter=parameter, post=posts, prev=prev, next=next
    )


@app.route("/about")
def about():
    return render_template("about.html", parameter=parameter)
    # parameter will get passed to contact.html as well all the extended templates as well


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        """Add contact data to database"""
        name = request.form["Name"]
        email = request.form["email"]
        number = request.form["number"]
        msg = request.form["msg"]
        contact = Contact(Name=name, msg=msg, email=email, number=number)
        db.session.add(contact)
        db.session.commit()
        msg = Message(
            subject="Hello " + name,
            recipients=[email],
            body="Thanks for contacting us. We will surely try to get in touch with you soon.",
        )
        mail.send(msg)

    return render_template("contact.html", parameter=parameter)


@app.route("/post/<string:Sr>", methods=["GET"])
def post_title(Sr):
    post = Post.query.filter_by(Sr=Sr).first()
    return render_template("post.html", parameter=parameter, post=post)


@app.route("/delete/<int:Sr>", methods=["GET", "POST"])
def delete_post(Sr):
    if "username" in session and session["username"] == passwords["username"]:
        post = Post.query.filter_by(Sr=Sr).first()
        db.session.delete(post)
        db.session.commit()
        return redirect("/admin")


@app.route("/delete_all", methods=["GET", "POST"])
def delete_all():
    if "username" in session and session["username"] == passwords["username"]:
        posts = Post.query.all()
        for post in posts:
            db.session.delete(post)
            db.session.commit()
        return redirect("/admin")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    post = Post.query.all()
    if "username" in session and session["username"] == passwords["username"]:
        return render_template("dashboard.html", parameter=parameter, post=post)
    # by doing this user won't have to enter password again in same session

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == passwords["username"] and password == passwords["login_password"]:
            session["username"] = email
            return render_template("dashboard.html", parameter=parameter, post=post)
    return render_template("admin.html", parameter=parameter)


@app.route("/edit/<string:Sr>", methods=["GET", "POST"])
def edit_post(Sr):
    if "username" in session and session["username"] == passwords["username"]:
        filename = False
        if request.method == "POST":
            # 'if' will only trigger when 'form' from 'edit.html' sends POST request
            title = request.form["title"]
            sub_title = request.form["tagline"]
            content = request.form["content"]
            f = request.files["file1"]
            if f:
                f.save(os.path.join(app.config["UPLOAD_FOLDER"], f.filename))
                filename = f.filename

            # here we get content from 'edit.html'
            if Sr == "0" or Sr == "":
                # this is block adds the new post
                new_post = Post(
                    title=title,
                    sub_title=sub_title,
                    content=content,
                    background_image=rf"img/{filename}",
                )

                db.session.add(new_post)
                # this creates new entry in database
                db.session.commit()
                return redirect("/admin")

            else:
                # this block edits the new post
                post = Post.query.filter_by(Sr=Sr).first()
                post.title = title
                post.sub_title = sub_title
                post.content = content
                if f:
                    post.background_image = rf"img/{filename}"
                db.session.commit()
                return redirect("/admin")

        post = Post.query.filter_by(Sr=Sr).first()

        return render_template("edit.html", post=post, parameter=parameter, Sr=Sr)


@app.route("/logout")
def logout():
    session.pop("username")
    return redirect("/admin")


@app.route("/search", methods=["POST", "GET"])
def search_func():
    if request.method == "POST":
        search = request.form.get("searchbar")
        search = f"%{search}%"
        post = Post.query.filter(
            or_(
                Post.title.like(search),
                Post.sub_title.like(search),
                Post.content.like(search),
            )
        ).all()
        """
        >> .filter_by performs exact match meaning it will only return item when it matches exactly 
        >> .like allows searching for results containing the search term rather than matching it exactly.
        >> or_ allows you to search for posts where either the title or sub_title or content contains the search term.
        >> % is used as a wildcard in SQL to match any sequence of characters, making it possible to search for substrings.
        A wildcard is a special character used in search queries to represent one or more unknown characters. Wildcards allow you to 
        broaden a search by specifying patterns rather than exact text.
        """
        return render_template("index.html", post=post, parameter=parameter)


if __name__ == "__main__":
    with app.app_context():
        db.create_all(bind_key="posts")
        db.create_all(bind_key="contacts")
        # this instruction creates database in instance folder
    app.run(debug=True)
