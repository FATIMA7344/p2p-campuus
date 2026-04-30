from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
import cloudinary
import cloudinary.uploader
from flask_mail import Mail, Message as MailMessage

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'peer2peer_encg_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://p2p_user:p2p_password@localhost/p2p_campus'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_EMAIL')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_EMAIL')

mail = Mail(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

@app.before_request
def before_request():
    update_last_seen()

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'zip', 'mp4', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── MODELS ─────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    annee_etude = db.Column(db.String(20), nullable=False)
    filiere = db.Column(db.String(50), nullable=False)
    bio = db.Column(db.Text, default='')
    portfolio = db.Column(db.Text, default='')
    credits = db.Column(db.Integer, default=50)
    total_gagne = db.Column(db.Integer, default=0)
    total_depense = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    competences = db.relationship('Competence', backref='user', lazy=True, cascade='all, delete-orphan')
    missions_postees = db.relationship('Mission', backref='auteur', lazy=True, cascade='all, delete-orphan')
    evaluations_recues = db.relationship('Evaluation', foreign_keys='Evaluation.evalue_id', backref='evalue', lazy=True)
    evaluations_donnees = db.relationship('Evaluation', foreign_keys='Evaluation.evaluateur_id', backref='evaluateur', lazy=True)

class Competence(db.Model):
    __tablename__ = 'competences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Mission(db.Model):
    __tablename__ = 'missions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type_mission = db.Column(db.String(20), nullable=False)  # 'offre' ou 'demande'
    competence = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    statut = db.Column(db.String(20), default='ouvert')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    expediteur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    destinataire_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contenu = db.Column(db.Text)
    fichier = db.Column(db.String(300))
    lu = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expediteur = db.relationship('User', foreign_keys=[expediteur_id])
    destinataire = db.relationship('User', foreign_keys=[destinataire_id])

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    expediteur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    destinataire_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    montant = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expediteur = db.relationship('User', foreign_keys=[expediteur_id])
    destinataire = db.relationship('User', foreign_keys=[destinataire_id])

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    lu = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True)
    evalue_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    evaluateur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    note = db.Column(db.Integer, nullable=False)
    commentaire = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Meet(db.Model):
    __tablename__ = 'meets'
    id = db.Column(db.Integer, primary_key=True)
    organisateur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    date_meet = db.Column(db.DateTime, nullable=False)
    room_id = db.Column(db.String(100), unique=True, nullable=False)
    statut = db.Column(db.String(20), default='planifie')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    organisateur = db.relationship('User', foreign_keys=[organisateur_id])

class MeetParticipant(db.Model):
    __tablename__ = 'meet_participants'
    id = db.Column(db.Integer, primary_key=True)
    meet_id = db.Column(db.Integer, db.ForeignKey('meets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    statut = db.Column(db.String(20), default='invite')
    meet = db.relationship('Meet', backref='participants')
    user = db.relationship('User', foreign_keys=[user_id])


# ─── HELPERS ────────────────────────────────────────────────────────────────

def current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None
def update_last_seen():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            user.last_seen = datetime.utcnow()
            db.session.commit()

def envoyer_email(destinataire, sujet, corps):
    try:
        msg = MailMessage(
            subject=sujet,
            recipients=[destinataire],
            html=corps
        )
        mail.send(msg)
    except Exception as e:
        print(f"Erreur email: {e}")

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ROUTES ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('accueil'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Connexion réussie !', 'success')
            return redirect(url_for('accueil'))
        flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        annee = request.form.get('annee_etude', '')
        filiere = request.form.get('filiere', '')

        if not email.endswith('@uca.ac.ma'):
            flash("L'email doit être de la forme @uca.ac.ma", 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('register.html')

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(nom=nom, prenom=prenom, email=email, password=hashed,
                    annee_etude=annee, filiere=filiere, credits=50)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash('Compte créé avec succès ! 50 crédits offerts.', 'success')
        return redirect(url_for('accueil'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── MAIN PAGES ─────────────────────────────────────────────────────────────

@app.route('/accueil')
@login_required
def accueil():
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    total_etudiants = User.query.count()
    total_missions = Mission.query.count()
    total_echanges = Transaction.query.count()
    return render_template('accueil.html', user=user, notifs=notifs,
                           total_etudiants=total_etudiants,
                           total_missions=total_missions,
                           total_echanges=total_echanges)
@app.route('/profil')
@app.route('/profil/<int:user_id>')
@login_required
def profil(user_id=None):
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    if user_id and user_id != user.id:
        profil_user = User.query.get_or_404(user_id)
        is_own = False
    else:
        profil_user = user
        is_own = True
    evaluations = Evaluation.query.filter_by(evalue_id=profil_user.id).order_by(Evaluation.created_at.desc()).all()
    avg_note = 0
    if evaluations:
        avg_note = round(sum(e.note for e in evaluations) / len(evaluations), 1)
    return render_template('profil.html', user=user, profil_user=profil_user, is_own=is_own,
                           evaluations=evaluations, avg_note=avg_note, notifs=notifs)

@app.route('/profil/modifier', methods=['POST'])
@login_required
def modifier_profil():
    user = current_user()
    user.nom = request.form.get('nom', user.nom).strip()
    user.prenom = request.form.get('prenom', user.prenom).strip()
    user.annee_etude = request.form.get('annee_etude', user.annee_etude)
    user.filiere = request.form.get('filiere', user.filiere)
    user.bio = request.form.get('bio', '').strip()
    user.portfolio = request.form.get('portfolio', '').strip()
    db.session.commit()
    flash('Profil mis à jour avec succès.', 'success')
    return redirect(url_for('profil'))

@app.route('/competence/ajouter', methods=['POST'])
@login_required
def ajouter_competence():
    user = current_user()
    nom = request.form.get('competence', '').strip()
    if nom:
        c = Competence(user_id=user.id, nom=nom)
        db.session.add(c)
        db.session.commit()
        flash('Compétence ajoutée.', 'success')
    return redirect(url_for('profil'))

@app.route('/competence/supprimer/<int:cid>')
@login_required
def supprimer_competence(cid):
    user = current_user()
    c = Competence.query.get_or_404(cid)
    if c.user_id == user.id:
        db.session.delete(c)
        db.session.commit()
    return redirect(url_for('profil'))

@app.route('/evaluer/<int:user_id>', methods=['POST'])
@login_required
def evaluer(user_id):
    user = current_user()
    note = int(request.form.get('note', 5))
    commentaire = request.form.get('commentaire', '').strip()
    ev = Evaluation(evalue_id=user_id, evaluateur_id=user.id, note=note, commentaire=commentaire)
    db.session.add(ev)
    db.session.commit()
    flash('Évaluation envoyée.', 'success')
    return redirect(url_for('profil', user_id=user_id))

# ─── MISSION BOARD ──────────────────────────────────────────────────────────

@app.route('/missions')
@login_required
def missions():
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    query = Mission.query.filter_by(statut='ouvert')
    if search:
        query = query.filter(
            (Mission.titre.ilike(f'%{search}%')) |
            (Mission.competence.ilike(f'%{search}%')) |
            (Mission.description.ilike(f'%{search}%'))
        )
    if type_filter in ('offre', 'demande'):
        query = query.filter_by(type_mission=type_filter)
    missions_list = query.order_by(Mission.created_at.desc()).all()
    return render_template('missions.html', user=user, missions=missions_list,
                           search=search, type_filter=type_filter, notifs=notifs)
@app.route('/mission/publier', methods=['POST'])
@login_required
def publier_mission():
    user = current_user()
    titre = request.form.get('titre', '').strip()
    description = request.form.get('description', '').strip()
    type_mission = request.form.get('type_mission', 'offre')
    competence = request.form.get('competence', '').strip()
    credits = int(request.form.get('credits', 10))
    m = Mission(user_id=user.id, titre=titre, description=description,
                type_mission=type_mission, competence=competence, credits=credits)
    db.session.add(m)
    db.session.commit()
    tous_users = User.query.filter(User.id != user.id).all()
    for u in tous_users:
        corps_email = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto"><div style="background:#e8821e;padding:20px;text-align:center;border-radius:10px 10px 0 0"><h1 style="color:white;margin:0">Peer2Peer Campus</h1><p style="color:white;margin:5px 0">ENCG Marrakech</p></div><div style="background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px"><h2 style="color:#1a7a4a">Nouvelle mission publiee !</h2><p>Bonjour <strong>{u.prenom}</strong>,</p><p><strong>{user.prenom} {user.nom}</strong> vient de publier :</p><div style="background:white;border-left:4px solid #e8821e;padding:15px;margin:20px 0;border-radius:5px"><h3 style="color:#e8821e;margin:0 0 10px 0">{titre}</h3><p style="color:#666;margin:5px 0">Competence : <strong>{competence}</strong></p><p style="color:#666;margin:5px 0">Credits : <strong>{credits}</strong></p><p style="color:#444;margin:10px 0">{description[:200]}</p></div><a href="https://p2p-campuus-production.up.railway.app/missions" style="display:inline-block;background:#1a7a4a;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;font-weight:bold">Voir la mission</a></div></div>"""
        envoyer_email(
            u.email,
            f"Nouvelle mission : {titre}",
            corps_email
        )
    flash('Mission publiée avec succès !', 'success')
    return redirect(url_for('missions'))
@app.route('/mission/supprimer/<int:mid>')
@login_required
def supprimer_mission(mid):
    user = current_user()
    m = Mission.query.get_or_404(mid)
    if m.user_id == user.id:
        db.session.delete(m)
        db.session.commit()
        flash('Mission supprimée.', 'info')
    return redirect(url_for('missions'))

# ─── MESSAGES ───────────────────────────────────────────────────────────────

@app.route('/messages')
@login_required
def messages():
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    # Obtenir la liste des conversations uniques
    sent = db.session.query(Message.destinataire_id).filter_by(expediteur_id=user.id)
    received = db.session.query(Message.expediteur_id).filter_by(destinataire_id=user.id)
    contact_ids = set([r[0] for r in sent.all()] + [r[0] for r in received.all()])
    contacts = User.query.filter(User.id.in_(contact_ids)).all()
    return render_template('messages.html', user=user, contacts=contacts, notifs=notifs)

@app.route('/messages/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def conversation(contact_id):
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    contact = User.query.get_or_404(contact_id)
    if request.method == 'POST':
        contenu = request.form.get('contenu', '').strip()
        fichier_path = None
        if 'fichier' in request.files:
            f = request.files['fichier']
        if f and f.filename:
            extension = f.filename.rsplit('.', 1)[-1].lower()
            if extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                resource_type = 'image'
            elif extension in ['mp4', 'avi', 'mov', 'mkv']:
                resource_type = 'video'
            else:
                resource_type = 'raw'
            upload_result = cloudinary.uploader.upload(
                f,
                resource_type=resource_type,
                access_mode='public'
            )
            fichier_path = upload_result['secure_url']
        if contenu or fichier_path:
            msg = Message(expediteur_id=user.id, destinataire_id=contact_id,
                          contenu=contenu, fichier=fichier_path)
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('conversation', contact_id=contact_id))
    Message.query.filter_by(expediteur_id=contact_id, destinataire_id=user.id, lu=False).update({'lu': True})
    db.session.commit()
    msgs = Message.query.filter(
        ((Message.expediteur_id == user.id) & (Message.destinataire_id == contact_id)) |
        ((Message.expediteur_id == contact_id) & (Message.destinataire_id == user.id))
    ).order_by(Message.created_at.asc()).all()
    return render_template('conversation.html', user=user, contact=contact, msgs=msgs, notifs=notifs)

@app.route('/messages/nouveau/<int:user_id>')
@login_required
def nouveau_message(user_id):
    return redirect(url_for('conversation', contact_id=user_id))

# ─── WALLET ─────────────────────────────────────────────────────────────────

@app.route('/wallet')
@login_required
def wallet():
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    transactions = Transaction.query.filter(
        (Transaction.expediteur_id == user.id) | (Transaction.destinataire_id == user.id)
    ).order_by(Transaction.created_at.desc()).limit(20).all()
    return render_template('wallet.html', user=user, transactions=transactions, notifs=notifs)

@app.route('/wallet/envoyer', methods=['POST'])
@login_required
def envoyer_credits():
    user = current_user()
    destinataire_id = int(request.form.get('destinataire_id', 0))
    montant = int(request.form.get('montant', 0))
    if montant <= 0:
        flash('Montant invalide.', 'danger')
        return redirect(url_for('wallet'))
    if user.credits < montant:
        flash('Solde insuffisant pour effectuer ce transfert.', 'danger')
        return redirect(url_for('wallet'))
    destinataire = User.query.get(destinataire_id)
    if not destinataire or destinataire.id == user.id:
        flash('Destinataire introuvable.', 'danger')
        return redirect(url_for('wallet'))
    user.credits -= montant
    user.total_depense += montant
    destinataire.credits += montant
    destinataire.total_gagne += montant
    t = Transaction(expediteur_id=user.id, destinataire_id=destinataire_id, montant=montant)
    db.session.add(t)
    notif = Notification(
        user_id=destinataire_id,
        message=f"{user.prenom} {user.nom} vous a envoyé {montant} crédits."
    )
    db.session.add(notif)
    db.session.commit()
    flash(f'{montant} crédits envoyés à {destinataire.prenom} {destinataire.nom}.', 'success')
    return redirect(url_for('wallet'))

@app.route('/api/recherche-utilisateur')
@login_required
def recherche_utilisateur():
    user = current_user()
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    users = User.query.filter(
        (User.nom.ilike(f'%{q}%') | User.prenom.ilike(f'%{q}%') | User.email.ilike(f'%{q}%')),
        User.id != user.id
    ).limit(5).all()
    return jsonify([{'id': u.id, 'nom': f"{u.prenom} {u.nom}", 'email': u.email} for u in users])
@app.route('/notifications')
@login_required
def notifications():
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    notifs_list = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    Notification.query.filter_by(user_id=user.id, lu=False).update({'lu': True})
    db.session.commit()
    return render_template('notifications.html', user=user, notifs=notifs, notifs_list=notifs_list)
@app.route('/notifications/lire')
@login_required
def lire_notifications():
    user = current_user()
    Notification.query.filter_by(user_id=user.id, lu=False).update({'lu': True})
    db.session.commit()
    return redirect(request.referrer or url_for('accueil'))
# ─── INIT DB ────────────────────────────────────────────────────────────────

@app.route('/api/statut/<int:user_id>')
@login_required
def statut_utilisateur(user_id):
    u = User.query.get_or_404(user_id)
    if u.last_seen:
        diff = datetime.utcnow() - u.last_seen
        secondes = diff.total_seconds()
        if secondes < 300:
            statut = 'en ligne'
        elif secondes < 3600:
            minutes = int(secondes / 60)
            statut = f'vu il y a {minutes} min'
        elif secondes < 86400:
            heures = int(secondes / 3600)
            statut = f'vu il y a {heures}h'
        else:
            jours = int(secondes / 86400)
            statut = f'vu il y a {jours}j'
    else:
        statut = 'hors ligne'
    return jsonify({'statut': statut, 'en_ligne': secondes < 300 if u.last_seen else False})

import uuid

@app.route('/meets')
@login_required
def meets():
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    now = datetime.utcnow()
    # Meets organisés par l'utilisateur
    mes_meets = Meet.query.filter_by(organisateur_id=user.id).all()
    # Meets où l'utilisateur est participant
    participations = MeetParticipant.query.filter_by(user_id=user.id).all()
    meet_ids = [p.meet_id for p in participations]
    meets_invites = Meet.query.filter(Meet.id.in_(meet_ids)).all()
    # Combiner et dédupliquer
    tous_meets = list({m.id: m for m in mes_meets + meets_invites}.values())
    tous_meets.sort(key=lambda x: x.date_meet)
    meets_en_cours = [m for m in tous_meets if m.statut == 'en_cours']
    meets_a_venir = [m for m in tous_meets if m.statut == 'planifie' and m.date_meet > now]
    meets_termines = [m for m in tous_meets if m.statut == 'termine' or m.date_meet < now]
    return render_template('meets.html', user=user, notifs=notifs,
                           meets_en_cours=meets_en_cours,
                           meets_a_venir=meets_a_venir,
                           meets_termines=meets_termines,
                           now=now)

@app.route('/meets/creer', methods=['POST'])
@login_required
def creer_meet():
    user = current_user()
    titre = request.form.get('titre', '').strip()
    description = request.form.get('description', '').strip()
    date_str = request.form.get('date_meet', '')
    participants_ids = request.form.getlist('participants')
    try:
        date_meet = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
    except:
        flash('Date invalide.', 'danger')
        return redirect(url_for('meets'))
    room_id = str(uuid.uuid4())[:8] + '-encg-p2p'
    meet = Meet(organisateur_id=user.id, titre=titre,
                description=description, date_meet=date_meet,
                room_id=room_id)
    db.session.add(meet)
    db.session.flush()
    # Ajouter l'organisateur comme participant
    p = MeetParticipant(meet_id=meet.id, user_id=user.id, statut='accepte')
    db.session.add(p)
    # Ajouter les autres participants
    for pid in participants_ids:
        p = MeetParticipant(meet_id=meet.id, user_id=int(pid), statut='invite')
        db.session.add(p)
        # Envoyer notification
        notif = Notification(
            user_id=int(pid),
            message=f"{user.prenom} {user.nom} vous invite à un Meet : '{titre}' le {date_meet.strftime('%d/%m/%Y à %H:%M')}"
        )
        db.session.add(notif)
    db.session.commit()
    flash('Meet créé avec succès !', 'success')
    return redirect(url_for('meets'))

@app.route('/meets/rejoindre/<int:meet_id>')
@login_required
def rejoindre_meet(meet_id):
    user = current_user()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).count()
    meet = Meet.query.get_or_404(meet_id)
    # Vérifier que l'utilisateur est participant
    participation = MeetParticipant.query.filter_by(
        meet_id=meet_id, user_id=user.id).first()
    if not participation and meet.organisateur_id != user.id:
        flash('Vous n\'êtes pas invité à ce Meet.', 'danger')
        return redirect(url_for('meets'))
    # Mettre à jour le statut
    if meet.statut == 'planifie':
        meet.statut = 'en_cours'
        db.session.commit()
    return render_template('meet_room.html', user=user,
                           meet=meet, notifs=notifs)

@app.route('/meets/terminer/<int:meet_id>')
@login_required
def terminer_meet(meet_id):
    user = current_user()
    meet = Meet.query.get_or_404(meet_id)
    if meet.organisateur_id == user.id:
        meet.statut = 'termine'
        db.session.commit()
        flash('Meet terminé.', 'info')
    return redirect(url_for('meets'))

@app.route('/meets/supprimer/<int:meet_id>')
@login_required
def supprimer_meet(meet_id):
    user = current_user()
    meet = Meet.query.get_or_404(meet_id)
    if meet.organisateur_id == user.id:
        MeetParticipant.query.filter_by(meet_id=meet_id).delete()
        db.session.delete(meet)
        db.session.commit()
        flash('Meet supprimé.', 'info')
    return redirect(url_for('meets'))

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Base de données initialisée.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
