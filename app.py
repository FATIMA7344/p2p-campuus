from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
import cloudinary
import cloudinary.uploader

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

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

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

# ─── HELPERS ────────────────────────────────────────────────────────────────

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

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
    return render_template('accueil.html', user=user, notifs=notifs)

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

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Base de données initialisée.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
