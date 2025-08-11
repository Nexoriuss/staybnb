import os
import tempfile
import urllib.request
from datetime import datetime, date
from sqlalchemy.orm import selectinload
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, DecimalField, DateField, FileField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, Date, DateTime, and_, or_
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session

# =========================================================
# App config
# =========================================================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-please-change")

# DB path:
# - En local: fichier à côté du code
# - Sur Railway: /tmp (écriture autorisée)
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PORT"):
    DB_PATH = os.path.join(tempfile.gettempdir(), "staybnb.sqlite3")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "staybnb.sqlite3")

app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# =========================================================
# Database (SQLAlchemy)
# =========================================================
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    listings = relationship("Listing", back_populates="host", cascade="all, delete-orphan")
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")

    @property
    def is_authenticated(self): return True
    @property
    def is_active(self): return True
    @property
    def is_anonymous(self): return False
    def get_id(self): return str(self.id)

class Listing(Base):
    __tablename__ = "listings"
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    city = Column(String(120), nullable=False)
    country = Column(String(120), nullable=False)
    price_per_night = Column(Float, nullable=False)
    max_guests = Column(Integer, nullable=False)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Integer, nullable=False)
    amenities = Column(Text, default="")
    photos = relationship("Photo", back_populates="listing", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="listing", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="listing", cascade="all, delete-orphan")
    host = relationship("User", back_populates="listings")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    filename = Column(String(255), nullable=False)
    listing = relationship("Listing", back_populates="photos")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    listing_id = Column(Integer, ForeignKey("listings.id"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    guests = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(50), default="pending")  # pending, confirmed, cancelled, paid
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    listing = relationship("Listing", back_populates="bookings")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    listing = relationship("Listing", back_populates="reviews")
    user = relationship("User")

Base.metadata.create_all(engine)

# =========================================================
# Seed auto si base vide (annonces de démo)
# =========================================================
def seed_if_empty():
    db = SessionLocal()
    try:
        if db.query(Listing).count() > 0:
            return
        demo = User(name="Hôte Démo", email="demo@staybnb.local", password_hash=generate_password_hash("demo1234"))
        db.add(demo); db.commit()

        demo_listings = [
            {"title":"Loft lumineux près du Canal Saint-Martin","description":"Grand loft refait à neuf, hauteur sous plafond, cuisine ouverte, idéal pour un city-break.","city":"Paris","country":"France","price":145,"max_guests":3,"bedrooms":1,"bathrooms":1,"amenities":"Wi-Fi, Cuisine équipée, Lave-linge, Chauffage, TV","photos":["https://picsum.photos/id/1067/1200/800","https://picsum.photos/id/1018/1200/800"]},
            {"title":"Appartement cosy près du Vieux-Port","description":"Ambiance méditerranéenne, balcon ensoleillé, parfait pour explorer Marseille.","city":"Marseille","country":"France","price":95,"max_guests":2,"bedrooms":1,"bathrooms":1,"amenities":"Wi-Fi, Climatisation, Cuisine, Machine à café","photos":["https://picsum.photos/id/1025/1200/800","https://picsum.photos/id/103/1200/800"]},
            {"title":"Duplex design sur les quais","description":"Style contemporain, vue sur la Saône, idéal pour les amoureux d’architecture.","city":"Lyon","country":"France","price":120,"max_guests":4,"bedrooms":2,"bathrooms":1,"amenities":"Wi-Fi, Lave-vaisselle, Chauffage, TV, Lit bébé","photos":["https://picsum.photos/id/1043/1200/800","https://picsum.photos/id/1050/1200/800"]},
            {"title":"Studio vue mer Promenade des Anglais","description":"Face à la mer, terrasse privée et accès plage à 2 minutes.","city":"Nice","country":"France","price":130,"max_guests":2,"bedrooms":1,"bathrooms":1,"amenities":"Wi-Fi, Climatisation, Terrasse, Ascenseur","photos":["https://picsum.photos/id/1011/1200/800","https://picsum.photos/id/1016/1200/800"]},
            {"title":"Maison en pierre proche des vignobles","description":"Charme de l’ancien, grande cuisine, jardin au calme à 20 min de Bordeaux.","city":"Bordeaux","country":"France","price":160,"max_guests":5,"bedrooms":3,"bathrooms":2,"amenities":"Wi-Fi, Cheminée, Jardin, Parking, Barbecue","photos":["https://picsum.photos/id/1040/1200/800","https://picsum.photos/id/1008/1200/800"]},
        ]

        updir = app.config["UPLOAD_FOLDER"]
        os.makedirs(updir, exist_ok=True)

        for item in demo_listings:
            l = Listing(
                host_id=demo.id, title=item["title"], description=item["description"],
                city=item["city"], country=item["country"],
                price_per_night=float(item["price"]), max_guests=item["max_guests"],
                bedrooms=item["bedrooms"], bathrooms=item["bathrooms"], amenities=item["amenities"]
            )
            db.add(l); db.commit()
            for i, url in enumerate(item["photos"]):
                fname = f"seed_{l.id}_{i}.jpg"
                try:
                    urllib.request.urlretrieve(url, os.path.join(updir, fname))
                    db.add(Photo(listing_id=l.id, filename=fname)); db.commit()
                except Exception as e:
                    print("Seed photo error:", e)
        print("✅ Base de démo initialisée.")
    finally:
        db.close()

seed_if_empty()

# =========================================================
# Auth (Flask-Login)
# =========================================================
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    db = SessionLocal()
    try:
        return db.get(User, int(user_id))
    finally:
        db.close()

# =========================================================
# Forms
# =========================================================
class RegisterForm(FlaskForm):
    name = StringField("Nom", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Créer mon compte")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    submit = SubmitField("Se connecter")

class ListingForm(FlaskForm):
    title = StringField("Titre", validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=10)])
    city = StringField("Ville", validators=[DataRequired()])
    country = StringField("Pays", validators=[DataRequired()])
    price_per_night = DecimalField("Prix / nuit (€)", validators=[DataRequired(), NumberRange(min=0)], places=2)
    max_guests = IntegerField("Voyageurs max", validators=[DataRequired(), NumberRange(min=1)])
    bedrooms = IntegerField("Chambres", validators=[DataRequired(), NumberRange(min=0)])
    bathrooms = IntegerField("Salles de bain", validators=[DataRequired(), NumberRange(min=0)])
    amenities = TextAreaField("Équipements (séparés par des virgules)", validators=[Optional()])
    photo1 = FileField("Photo 1 (jpg/png)", validators=[Optional()])
    photo2 = FileField("Photo 2 (jpg/png)", validators=[Optional()])
    submit = SubmitField("Publier")

class BookingForm(FlaskForm):
    start_date = DateField("Arrivée", validators=[DataRequired()], format="%Y-%m-%d")
    end_date = DateField("Départ", validators=[DataRequired()], format="%Y-%m-%d")
    guests = IntegerField("Voyageurs", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Réserver")

class MessageForm(FlaskForm):
    body = TextAreaField("Message", validators=[DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField("Envoyer")

class ReviewForm(FlaskForm):
    rating = IntegerField("Note (1-5)", validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField("Avis", validators=[DataRequired(), Length(min=5)])
    submit = SubmitField("Publier l'avis")

# =========================================================
# Helpers
# =========================================================
def overlap(a_start, a_end, b_start, b_end):
    return a_start <= b_end and b_start <= a_end

def listing_available(db, listing_id, start, end):
    bookings = db.query(Booking).filter(Booking.listing_id==listing_id, Booking.status.in_(["pending","confirmed","paid"])).all()
    for b in bookings:
        if overlap(b.start_date, b.end_date, start, end):
            return False
    return True

def save_photo(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    filename = secure_filename(file_storage.filename)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in [".jpg",".jpeg",".png",".webp"]:
        return None
    unique = f"{name}_{int(datetime.utcnow().timestamp())}{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique)
    file_storage.save(path)
    return unique

# =========================================================
# Routes
# =========================================================
@app.route("/")
@app.route("/")
def index():
    q_city = request.args.get("city")
    q_country = request.args.get("country")
    q_guests = request.args.get("guests")

    # On charge aussi les photos pour éviter DetachedInstanceError
    listings = db.query(Listing).options(selectinload(Listing.photos))

    if q_city:
        listings = listings.filter(Listing.city.ilike(f"%{q_city}%"))
    if q_country:
        listings = listings.filter(Listing.country.ilike(f"%{q_country}%"))
    if q_guests and q_guests.isdigit():
        listings = listings.filter(Listing.max_guests >= int(q_guests))

    listings = listings.order_by(Listing.id.desc()).all()

    return render_template("index.html", listings=listings)


@app.route("/register", methods=["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db = SessionLocal()
        try:
            if db.query(User).filter(User.email==form.email.data.lower()).first():
                flash("Un compte existe déjà avec cet email.", "warning")
            else:
                user = User(
                    name=form.name.data,
                    email=form.email.data.lower(),
                    password_hash=generate_password_hash(form.password.data)
                )
                db.add(user); db.commit()
                login_user(user)
                flash("Bienvenue ! Ton compte est créé.", "success")
                return redirect(url_for("index"))
        finally:
            db.close()
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email==form.email.data.lower()).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash("Connecté.", "success")
                return redirect(url_for("index"))
            else:
                flash("Identifiants invalides.", "danger")
        finally:
            db.close()
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnecté.", "info")
    return redirect(url_for("index"))

@app.route("/listings/new", methods=["GET","POST"])
@login_required
def new_listing():
    form = ListingForm()
    if form.validate_on_submit():
        db = SessionLocal()
        try:
            listing = Listing(
                host_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                city=form.city.data,
                country=form.country.data,
                price_per_night=float(form.price_per_night.data),
                max_guests=form.max_guests.data,
                bedrooms=form.bedrooms.data,
                bathrooms=form.bathrooms.data,
                amenities=form.amenities.data or ""
            )
            db.add(listing); db.commit()
            for ph in [form.photo1.data, form.photo2.data]:
                fn = save_photo(ph)
                if fn:
                    db.add(Photo(listing_id=listing.id, filename=fn))
            db.commit()
            flash("Annonce publiée.", "success")
            return redirect(url_for("listing_detail", listing_id=listing.id))
        finally:
            db.close()
    return render_template("new_listing.html", form=form)

@app.route("/listings/<int:listing_id>", methods=["GET","POST"])
def listing_detail(listing_id):
    db = SessionLocal()
    try:
        listing = db.get(Listing, listing_id)
        if not listing:
            flash("Annonce introuvable.", "warning")
            return redirect(url_for("index"))
        bform = BookingForm()
        rform = ReviewForm()

        if bform.submit.data and bform.validate_on_submit():
            start = bform.start_date.data
            end = bform.end_date.data
            guests = bform.guests.data
            if end < start:
                flash("La date de départ doit être après l'arrivée.", "warning")
            elif guests > listing.max_guests:
                flash("Nombre de voyageurs supérieur à la capacité.", "warning")
            elif not current_user.is_authenticated:
                flash("Connecte-toi pour réserver.", "warning")
                return redirect(url_for("login"))
            elif not listing_available(db, listing.id, start, end):
                flash("Ces dates ne sont pas disponibles.", "warning")
            else:
                nights = (end - start).days or 1
                total = nights * listing.price_per_night
                booking = Booking(user_id=current_user.id, listing_id=listing.id,
                                  start_date=start, end_date=end, guests=guests,
                                  total_price=total, status="confirmed")
                db.add(booking); db.commit()
                flash("Réservation créée (paiement simulé).", "success")
                return redirect(url_for("dashboard"))

        if rform.submit.data and rform.validate_on_submit():
            if not current_user.is_authenticated:
                flash("Connecte-toi pour publier un avis.", "warning")
                return redirect(url_for("login"))
            past_booking = db.query(Booking).filter(
                Booking.user_id==current_user.id,
                Booking.listing_id==listing.id,
                Booking.end_date <= date.today(),
                Booking.status.in_(["confirmed","paid"])
            ).first()
            if not past_booking:
                flash("Tu peux laisser un avis après un séjour terminé.", "warning")
            else:
                review = Review(listing_id=listing.id, user_id=current_user.id,
                                rating=rform.rating.data, comment=rform.comment.data)
                db.add(review); db.commit()
                flash("Avis publié.", "success")
                return redirect(url_for("listing_detail", listing_id=listing.id))

        reviews = db.query(Review).filter(Review.listing_id==listing.id).order_by(Review.created_at.desc()).all()
        return render_template("listing_detail.html", listing=listing, bform=bform, rform=rform, reviews=reviews)
    finally:
        db.close()

@app.route("/dashboard")
@login_required
def dashboard():
    db = SessionLocal()
    try:
        my_listings = db.query(Listing).filter(Listing.host_id==current_user.id).all()
        my_bookings = db.query(Booking).filter(Booking.user_id==current_user.id).order_by(Booking.created_at.desc()).all()
        incoming = db.query(Booking).join(Listing).filter(Listing.host_id==current_user.id).order_by(Booking.created_at.desc()).all()
        return render_template("dashboard.html", my_listings=my_listings, my_bookings=my_bookings, incoming=incoming)
    finally:
        db.close()

@app.route("/messages/<int:receiver_id>", methods=["GET","POST"])
@login_required
def messages(receiver_id):
    db = SessionLocal()
    try:
        other = db.get(User, receiver_id)
        if not other:
            flash("Utilisateur introuvable.", "warning")
            return redirect(url_for("index"))
        form = MessageForm()
        if form.validate_on_submit():
            m = Message(sender_id=current_user.id, receiver_id=other.id, body=form.body.data)
            db.add(m); db.commit()
            return redirect(url_for("messages", receiver_id=other.id))
        convo = db.query(Message).filter(
            or_(
                and_(Message.sender_id==current_user.id, Message.receiver_id==other.id),
                and_(Message.sender_id==other.id, Message.receiver_id==current_user.id),
            )
        ).order_by(Message.created_at.asc()).all()
        return render_template("messages.html", other=other, messages=convo, form=form)
    finally:
        db.close()

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# =========================================================
# Run
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
