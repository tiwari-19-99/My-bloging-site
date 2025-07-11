from flask import Flask, render_template, url_for, redirect, flash,request,session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField,TextAreaField,BooleanField
from wtforms.validators import DataRequired,length,Email
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_migrate import Migrate
from flask_mailman import Mail, EmailMessage


app= Flask(__name__)
app.config["SECRET_KEY"]="Secretkey"
app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///users.db"
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME='mayanktiwari5556@gmail.com',
    MAIL_PASSWORD='nuqt sjov antu vkva'
)

mail=Mail(app)
db=SQLAlchemy(app)
ma=Migrate(app,db)

class TimestampMixin:
    created_at= db.Column(db.DateTime, default=datetime.now)
    updated_at= db.Column(
        db.DateTime,
        default=datetime.now,
        onupdate=datetime.now
    )

class Users(db.Model):
    __tablename__ = 'users'
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(50),nullable=False, unique=True)
    password=db.Column(db.String(200),nullable=False)

    posts=db.relationship('Posts', backref='author', lazy=True)

class Posts(TimestampMixin,db.Model):
    __tablename__='posts'
    id= db.Column(db.Integer,primary_key=True)
    title= db.Column(db.String(200), nullable=False)
    body= db.Column(db.Text, nullable=False)
    published=db.Column(db.Boolean,default=False)
    likes=db.Column(db.Integer,default=0)
    author_id= db.Column(db.Integer, db.ForeignKey('users.id'))     

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    bio = db.Column(db.Text)

    user = db.relationship('Users', backref=db.backref('profile', uselist=False))

class EditProfileForm(FlaskForm):
    name = StringField("Name", validators=[length(max=100)])
    phone = StringField("Phone Number", validators=[length(max=20)])
    bio = TextAreaField("Bio", validators=[length(max=500)])
    submit = SubmitField("Save Changes")

class CredentialsForm(FlaskForm):
    email=StringField("Email", validators=[DataRequired("Email required"),Email("Enter valid email"),length(max=50)])
    password= PasswordField("Password", validators=[DataRequired("Password required"),length(min=8,message="Your password must be atleast 8 characters")])
    submit_register = SubmitField("Register")
    submit_login = SubmitField("Login")


class BlogForm(FlaskForm):
    title=StringField("Title", validators=[DataRequired("Title is required"),length(max=100)])
    body=TextAreaField("Content",validators=[DataRequired("Requires a body")])
    published=BooleanField("Publish")
    submit= SubmitField("Post")


@app.route("/", methods=['GET','POST'])
def home():
    if 'user_id' in session:
        session.pop("user_id", None)
    form=CredentialsForm()
    if form.validate_on_submit():
        user=Users.query.filter_by(email=form.email.data).first()
        if form.submit_register.data:
            if user:
                flash("Email already registered. Please login using your credentials","error")
            else:
                hashed_password=generate_password_hash(form.password.data)
                new_user=Users(email=form.email.data,password=hashed_password)
                email=EmailMessage(subject='Welcome Aboard to Cosmic Blogs!',body='Thank you for deciding to be a part of this family! Hoping to read great things from you!',to=[form.email.data])
                email.send()
                db.session.add(new_user)
                db.session.commit()
                session['user_id']=new_user.id
                flash("Registration Successful!","success")
                return redirect(url_for("posts"))
        elif form.submit_login.data:
            if not user or not check_password_hash(user.password, form.password.data):
                flash("Invalid login credentials.", "error")
            else:
                session["user_id"]= user.id
                flash("Login successful!", "success")
                return redirect(url_for("posts"))  
    return render_template("form.html", form=form)


@app.route("/post",methods=['GET','POST'])
def create_post():
    if 'user_id' not in session:
        flash("Login required to create a post.", "error")
        return redirect(url_for("home"))        
    form= BlogForm()
    if form.validate_on_submit():
        post=Posts(title=form.title.data, body=form.body.data,published=form.published.data, author_id=session["user_id"])
        try:
            db.session.add(post)
            db.session.commit()
            email=EmailMessage(subject='Successfully Posted!',body='Way to go! Your post has made to the cosmos, and is ready to be viewed by the galacticos.',to=[Users.query.get(session["user_id"]).email])        
            email.send()
        except:
            db.session.rollback()
            flash("Error posting", "error")    
        flash("Post created successfully!", "success")
        return redirect(url_for("posts"))
    return render_template("post.html", form=form)

@app.route("/dashboard")
def posts():
    all_posts = Posts.query.order_by(Posts.created_at.desc()).where(Posts.published==True)
    return render_template("dashboard.html", posts=all_posts)

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))


@app.route("/drafts")
def draft():
    if 'user_id' not in session:
        flash("Login required to view drafts.", "error")
        return redirect(url_for("home"))         
    all_posts= Posts.query.order_by(Posts.created_at.desc()).where(Posts.published==False, Posts.author_id==session['user_id']).all()
    return render_template("drafts.html",posts=all_posts)

@app.route("/edit/<int:post_id>", methods=['GET', 'POST'])
def edit(post_id):
    if 'user_id' not in session:
        flash("Login required to edit a post.", "error")
        return redirect(url_for("home"))
    post = Posts.query.get_or_404(post_id)
    if post.author_id!= session['user_id']:
        flash("You are not authorized to edit this post.", "error")
        return redirect(url_for("posts"))
    form = BlogForm(obj=post) 
    if form.validate_on_submit():
        post.title= form.title.data
        post.body= form.body.data
        post.published= form.published.data
        db.session.commit()
        flash("Post updated successfully!", "success")
        return redirect(url_for("posts") if post.published else url_for("draft"))

    return render_template("post.html", form=form)

@app.route("/your_posts")
def your_posts():
    if 'user_id' not in session:
        flash("Login required to view drafts.", "error")
        return redirect(url_for("home")) 
    all_posts= Posts.query.order_by(Posts.created_at.desc()).where(Posts.published==True, Posts.author_id==session['user_id']).all()
    return render_template("your_posts.html",posts=all_posts)

@app.route("/delete/<int:post_id>/<int:page>",methods=["POST"])
def delete(post_id,page):
    post= Posts.query.get_or_404(post_id)
    if not post:
        flash("Post not found!", "error")
        return redirect(url_for('posts'))

    if post.author_id!=session.get('user_id'):
        flash("You are not authorized to delete this post.", "error")
        return redirect(url_for('posts'))

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully.", "success")
    if page==1:
        return redirect(url_for("your_posts"))
    else:
        return redirect(url_for("draft"))

@app.route("/profile")
def profile():
    if 'user_id' not in session:
        flash("Login required to view profile.", "error")
        return redirect(url_for("home"))
    user = Users.query.get(session['user_id'])
    return render_template("profile.html", current_user=user, edit=False)


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if 'user_id' not in session:
        flash("Login required to edit profile.", "error")
        return redirect(url_for("home"))
    user = Users.query.get(session['user_id'])
    if not user.profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    form = EditProfileForm(obj=user.profile)
    if form.validate_on_submit():
        user.profile.name = form.name.data
        user.profile.phone = form.phone.data
        user.profile.bio = form.bio.data
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", current_user=user, edit=True, form=form)

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if 'user_id' not in session:
        flash("Login required to like blogs", "error")
        return redirect(url_for("home"))
    post = Posts.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    flash("You liked the post!", "success")
    return redirect(request.referrer or url_for("dashboard"))

    

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
