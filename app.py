from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from email_validator import validate_email, EmailNotValidError
from functools import wraps

##############################FORM-CLASS#############################################
#KULLANICI KAYIT FORMU
class RegisterForm(Form):
    name = StringField("Adınız ve Soyadınız", validators=[validators.length(min=4, max=25)])
    username = StringField("Kullanıcı Adınız", validators=[validators.length(min=5, max=15)])
    email = StringField("E-posta Adresi", validators=[])
    # Yukarıda validators için boş bir liste bıraktık, çünkü e-posta doğrulama kısmını kendimiz yapacağız
    password = PasswordField("Parolanızı Girin", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin!"),
        validators.EqualTo(fieldname="confirm", message="Parolanız Uyuşmuyor!")
    ])
    confirm = PasswordField("Parolanızı Tekrar Girin")
#KULLANICI GİRİŞ FORMU#################################################################
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")



##################################################
app = Flask(__name__)
app.secret_key = "fuyublog"

# Veritabanını yapılandırın ve SQLAlchemy nesnesini oluşturun
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///veritabani.db"
db = SQLAlchemy(app)

# Kullanıcı Modeli
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(80))

# Post Modeli
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    author = db.Column(db.String(80))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")
#Kayıt Olma
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        try:
            validate_email(email)  # E-posta doğrulaması
        except EmailNotValidError as e:
            flash("Geçerli bir e-posta adresi girin.", "danger")
            return render_template("register.html", form=form)

        new_user = User(name=name, username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Tebrikler! Başarıyla kayıt oldunuz..", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)
    

#####################Girişyap##############################
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        user = User.query.filter_by(username=username).first()

        if user:
            real_password = user.password
            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarıyla Giriş Yaptınız!", "success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Hatalı Parola!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle Bir Kullanıcı Bulunamadı!", "danger")
            return redirect(url_for("login"))

    return render_template("login.html", form=form)
#################################################################
#KULLANICI GİRİŞ YAPMA DEKORU
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))
    return decorated_function

#####ÇıkışYap#####
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla Çıkış Yaptınız","success")
    return redirect(url_for("index"))

######Dashboard#######
@app.route("/dashboard")
@login_required
def dashboard():
    myposts = Post.query.filter_by(author=session["username"]).all()
    return render_template("dashboard.html", myposts=myposts)


####################################
#GÖNDERİ EKLE
@app.route("/sharepost", methods = ["GET","POST"])
def sharepost():
    form = PostForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        new_post = Post(title=title, content=content, author=session["username"])
        db.session.add(new_post)
        db.session.commit()

        flash("✔️ Tebrikler! Gönderi Paylaşıldı", "success")
        return redirect(url_for("dashboard"))

    return render_template("sharepost.html", form=form)

########GÖNDERİFORM##############
class PostForm(Form):
    title = StringField("Başlık")
    content = TextAreaField("İçerik")
    author = StringField("Yazar")
    
##################################
#Gönderi Sayfası
@app.route("/posts")
def seeposts():
    allposts = Post.query.all()
    return render_template("allpost.html", allposts=allposts)



##Gönderi Silme
@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.author == session["username"]:
        db.session.delete(post)
        db.session.commit()
        flash("✔️ Gönderi silindi.", "success")
    else:
        flash("Bu gönderiyi silemezsiniz.", "danger")

    return redirect("/dashboard")

##Gönderi Düzenle
@app.route("/edit_post/<int:post_id>")
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.author == session["username"]:
        return render_template("edit_post.html", post=post)
    else:
        flash("Bu gönderiyi düzenleyemezsiniz.", "danger")
        return redirect("/dashboard")

##Gönderi Güncelleme
@app.route("/update_post/<int:post_id>", methods=["POST"])
def update_post(post_id):
    if request.method == "POST":
        new_title = request.form.get("title")
        new_content = request.form.get("content")

        post = Post.query.get_or_404(post_id)

        if post.author == session["username"]:
            post.title = new_title
            post.content = new_content
            db.session.commit()
            flash("✔️ Gönderi güncellendi.", "success")
        else:
            flash("Bu gönderiyi güncelleyemezsiniz.", "danger")

        return redirect("/dashboard")
    else:
        # Düzenleme formunu göster
        return render_template("edit_post.html")

#ARAMA URL#
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        keyword = request.form.get("keyword")

        found_posts = Post.query.filter(Post.title.like(f"%{keyword}%")).all()

        if not found_posts:
            flash("Aranan kelimeye uygun içerik bulunamadı!", "warning")
            return redirect(url_for("seeposts"))

        return render_template("search_results.html", found_posts=found_posts, keyword=keyword)

    return redirect(url_for("seeposts"))

        



if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Veritabanını oluşturun
    app.run(debug=True)
