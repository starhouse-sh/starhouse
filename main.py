import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from models import db, User, Property, PropertyImage
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'غير-المفتاح-ده-في-الإنتاج-123456789'

# مسار قاعدة البيانات
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'starhouse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/properties'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024

# Google OAuth Config
app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
google_bp = make_google_blueprint(
    scope=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
)
app.register_blueprint(google_bp, url_prefix="/login")

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'لازم تسجل دخول الأول'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# معالجة تسجيل جوجل
@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash("فشل تسجيل الدخول بجوجل", "error")
        return redirect(url_for("login"))

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("مقدرناش نجيب بياناتك من جوجل", "error")
        return redirect(url_for("login"))

    google_info = resp.json()
    google_id = google_info["id"]
    email = google_info["email"]
    name = google_info.get("name", email.split('@')[0])

    user = User.query.filter_by(oauth_provider='google', oauth_id=google_id).first()

    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.oauth_provider = 'google'
            user.oauth_id = google_id
            user.is_verified = True
        else:
            base_username = name.replace(' ', '_')
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User(
                username=username,
                email=email,
                oauth_provider='google',
                oauth_id=google_id,
                is_verified=True,
                phone=None
            )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash(f'أهلاً {user.username}', 'success')
    return redirect(url_for("index"))

@app.route('/')
def index():
    search = request.args.get('search', '')
    property_type = request.args.get('property_type', '')
    listing_type = request.args.get('listing_type', '')
    max_price = request.args.get('max_price', '')

    query = Property.query.filter_by(is_active=True)

    if search:
        query = query.filter(Property.location.contains(search) | Property.title.contains(search))
    if property_type:
        query = query.filter_by(property_type=property_type)
    if listing_type:
        query = query.filter_by(listing_type=listing_type)
    if max_price:
        query = query.filter(Property.price <= int(max_price))

    properties = query.order_by(Property.created_at.desc()).all()

    for prop in properties:
        main_img = PropertyImage.query.filter_by(property_id=prop.id, is_main=True).first()
        prop.first_image = main_img.filename if main_img else None

    return render_template('index.html', properties=properties)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('الإيميل ده مستخدم قبل كده', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم ده موجود', 'error')
            return redirect(url_for('register'))

        user = User(username=username, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('تم إنشاء الحساب بنجاح، سجل دخولك دلوقتي', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'أهلاً {user.username}', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('الإيميل أو الباسورد غلط', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج', 'success')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        try:
            new_property = Property(
                title=request.form['title'],
                description=request.form['description'],
                price=int(request.form['price']),
                property_type=request.form['property_type'],
                listing_type=request.form['listing_type'],
                location=request.form['location'],
                area=int(request.form['area']),
                bedrooms=int(request.form.get('bedrooms', 0)),
                bathrooms=int(request.form.get('bathrooms', 0)),
                user_id=current_user.id
            )
            db.session.add(new_property)
            db.session.commit()

            files = request.files.getlist('images')
            if not files or files[0].filename == '':
                flash('لازم ترفع صورة واحدة على الأقل', 'error')
                db.session.delete(new_property)
                db.session.commit()
                return redirect(url_for('add_property'))

            for i, file in enumerate(files[:10]):
                if file and file.filename:
                    filename = secure_filename(f"{new_property.id}{i}{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    img = Image.open(file)
                    img.thumbnail((1200, 1200))
                    img.save(filepath, optimize=True, quality=85)

                    img_db = PropertyImage(
                        filename=filename,
                        property_id=new_property.id,
                        is_main=(i==0)
                    )
                    db.session.add(img_db)

            db.session.commit()
            flash('تم إضافة العقار بنجاح', 'success')
            return redirect(url_for('property_detail', id=new_property.id))

        except Exception as e:
            flash(f'حصل خطأ: {str(e)}', 'error')
            return redirect(url_for('add_property'))

    return render_template('add_property.html')

@app.route('/property/<int:id>')
def property_detail(id):
    property = Property.query.get_or_404(id)
    images = PropertyImage.query.filter_by(property_id=id).all()
    return render_template('property_detail.html', property=property, images=images)

@app.route('/property/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_property(id):
    property = Property.query.get_or_404(id)
    if property.user_id!= current_user.id:
        flash('مش مسموحلك تعدل العقار ده', 'error')
        return redirect(url_for('property_detail', id=id))

    if request.method == 'POST':
        property.title = request.form['title']
        property.description = request.form['description']
        property.price = int(request.form['price'])
        property.property_type = request.form['property_type']
        property.listing_type = request.form['listing_type']
        property.location = request.form['location']
        property.area = int(request.form['area'])
        property.bedrooms = int(request.form.get('bedrooms', 0))
        property.bathrooms = int(request.form.get('bathrooms', 0))

        # رفع صور جديدة لو فيه
        files = request.files.getlist('images')
        if files and files[0].filename!= '':
            for i, file in enumerate(files[:10]):
                if file and file.filename:
                    filename = secure_filename(f"{property.id}{i}{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    img = Image.open(file)
                    img.thumbnail((1200, 1200))
                    img.save(filepath, optimize=True, quality=85)

                    img_db = PropertyImage(
                        filename=filename,
                        property_id=property.id,
                        is_main=False
                    )
                    db.session.add(img_db)

        db.session.commit()
        flash('تم تحديث العقار بنجاح', 'success')
        return redirect(url_for('property_detail', id=id))

    return render_template('edit_property.html', property=property)

@app.route('/property/<int:id>/delete', methods=['POST'])
@login_required
def delete_property(id):
    property = Property.query.get_or_404(id)
    if property.user_id!= current_user.id:
        flash('مش مسموحلك تحذف العقار ده', 'error')
        return redirect(url_for('property_detail', id=id))

    # احذف الصور من السيرفر
    for img in property.images:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img.filename))
        except:
            pass

    db.session.delete(property)
    db.session.commit()
    flash('تم حذف العقار بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/favorites')
@login_required
def favorites():
    return render_template('favorites.html')

@app.route('/evaluate')
def evaluate():
    return render_template('evaluate.html')

with app.app_context():
    db.create_all()
    print("✓ قاعدة البيانات جاهزة")

if __name__ == '__main__':
    app.run(debug=True)