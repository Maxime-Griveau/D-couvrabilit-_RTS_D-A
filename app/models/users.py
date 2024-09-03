from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import or_
from ..app import app, db, login

class Users(UserMixin, db.Model):
    """
    Une classe représentant les utilisateurs. Gère les informations des utilisateurs et fournit des méthodes pour leur gestion.

    Attributes
    ----------
    id : db.Column
        Identifiant de l'utilisateur. C'est la clé primaire, auto-incrémentée.
    pseudo : db.Column
        Pseudo de l'utilisateur, doit être unique.
    password : db.Column
        Mot de passe hashé de l'utilisateur.
    mail : db.Column
        Adresse mail de l'utilisateur, doit être unique.
    administrateur : db.Column
        Booléen indiquant si l'utilisateur est un administrateur.
    notifications- : db.Column
        Booléen indiquant si l'utilisateur souhaite recevoir des notifications 

    Methods
    -------
    get_id()
        Permet de récupérer l'identifiant de l'utilisateur.
    get_user_by_id(id)
        Récupère un utilisateur par son identifiant.
    Ajout(pseudo, password, mail)
        Ajoute un nouvel utilisateur à la base de données.
    Identification(password, mail)
        Identifie un utilisateur à partir de son mail et de son mot de passe.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    pseudo = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    mail = db.Column(db.String(100), nullable=False)
    administrateur = db.Column(db.Boolean, nullable=False, default=0)
    notifications = db.Column(db.Boolean, nullable=False, default=0)

    def get_id(self):
        """Permet de récupérer l'identifiant de l'utilisateur."""
        return self.id

    @login.user_loader
    def get_user_by_id(id):
        """
        Récupère un utilisateur par son identifiant.

        Parameters
        ----------
        id : int
            Identifiant de l'utilisateur.

        Returns
        -------
        app.models.users.Users
            Instance de Users correspondant à l'identifiant.
        """
        return Users.query.get(int(id))

    @staticmethod
    def Ajout(pseudo, password, mail):
        """
        Ajoute un nouvel utilisateur à la base de données.

        Parameters
        ----------
        pseudo : str
            Pseudo de l'utilisateur.
        password : str
            Mot de passe de l'utilisateur (non hashé).
        mail : str
            Adresse mail de l'utilisateur.

        Returns
        -------
        tuple
            (Utilisateur créé, liste des erreurs) si réussite, sinon (None, liste des erreurs).
        """
        erreurs = []
        # Vérification et traitement des données d'entrée...
        # ...

        try:
            utilisateur = Users(
                mail=mail,
                pseudo=pseudo,
                password=generate_password_hash(password)
                
            )
            db.session.add(utilisateur)
            db.session.commit()
            return utilisateur, None
        except Exception as erreur:
            return None, [str(erreur)]

    @staticmethod
    def Identification(password, mail):
        """
        Identifie un utilisateur à partir de son mail et de son mot de passe.

        Parameters
        ----------
        mail : str
            Adresse mail de l'utilisateur.
        password : str
            Mot de passe de l'utilisateur.

        Returns
        -------
        app.models.users.Users or None
            Si l'identification est un succès : retourne l'objet utilisateur.
            Sinon : retourne None.
        """
        utilisateur = Users.query.filter(Users.mail == mail).first()

        if utilisateur and check_password_hash(utilisateur.password, password):
            return utilisateur
        else:
            return None
