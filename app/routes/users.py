from ..app import app, db, login
from flask import render_template, request, flash, abort, redirect, url_for, abort 
from ..models.formulaires import InsertionUsers, Connexion

from ..models.users import Users
from flask_login import current_user, logout_user, login_user
from functools import wraps
from flask import abort


@app.route("/connexion", methods=['GET', 'POST'])
def connexion():
    """
    Route pour gérer la connexion des utilisateurs.

    Parameters
    ----------
    page : int, optional
        Numéro de la page actuelle, par défaut à 1.

    Returns
    -------
    template
        Retourne le template de la page de connexion avec les données nécessaires.

    Redirect 
    --------
    page 
        Redirige les utilisateurs connectés vers la page données 
    """
    form = Connexion()
    try:
        if form.validate_on_submit():
            mot_de_passe = request.form.get("mot_de_passe", None)
            mail = request.form.get("mail", None)
            if not current_user.is_authenticated:
                if mail and mot_de_passe:
                    utilisateur = Users.Identification(password=mot_de_passe, mail=mail)
                    if utilisateur:
                        login_user(utilisateur)
                        if utilisateur.administrateur:
                            flash(f"{utilisateur.mail} est désormais connecté en tant qu'administrateur.", 'success')
                        else:
                            flash(f"{utilisateur.mail} est désormais connecté en tant que journaliste.", 'success')
                        return redirect(url_for('donnees')) #redirige l'utilisateur connecté vers la page données  
                            
                    else:
                        flash("Adresse mail ou mot de passe incorrect.", 'error')
                else:
                    flash("Impossible de vous connecter, merci de fournir vos informations de connexion.", 'error')
            else:
                flash("Vous êtes déjà connecté.", 'info')

    except Exception as e:
        print("Une erreur est survenue : " + str(e))
        flash("Une erreur s'est produite lors de la connexion, avez-vous respecté les contraintes de saisie ?" + str(e), 'info')
        db.session.rollback()

    return render_template("pages/connexion.html", sous_titre="Recherche", form=form)



def admin_required(f):
    """
    Décorateur pour restreindre l'accès aux utilisateurs administrateurs.

    Ce décorateur s'assure que seule une personne disposant des privilèges d'administrateur puisse accéder à certaines routes. 
    Si un utilisateur non administrateur tente d'accéder à une route protégée par ce décorateur, une erreur 403 est renvoyée.

    Parameters
    ----------
    f : function
        La fonction de vue (route) à laquelle ce décorateur est appliqué.

    Returns
    -------
    function
        La fonction décorée avec la logique de contrôle d'accès administrateur.
    """
    @wraps(f)  # Préserve les métadonnées de la fonction originale
    def decorated_function(*args, **kwargs):
        if not current_user.administrateur:  # Vérifie si l'utilisateur courant est administrateur
            abort(403)  # Interdit l'accès en renvoyant une erreur 403
        return f(*args, **kwargs)  # Continue avec la fonction originale si l'utilisateur est administrateur
    return decorated_function


@app.route("/utilisateurs/deconnexion", methods=["POST", "GET"])
def deconnexion():
    """
    Route pour gérer la déconnexion des utilisateurs.

    Cette route permet aux utilisateurs de se déconnecter de l'application. Si un utilisateur est authentifié, la fonction logout_user() de Flask-Login est appelée pour terminer la session utilisateur. Un message flash informe l'utilisateur qu'il est déconnecté. L'utilisateur est ensuite redirigé vers la page 'donnees'.

    Méthodes acceptées
    ------------------
    POST, GET

    Returns
    -------
    redirect
        Redirige vers la page d'accueil (définie par la route 'donnees') après la déconnexion.
    """
    if current_user.is_authenticated:
        logout_user()  # Déconnecte l'utilisateur
        flash("Vous êtes déconnecté", "info")  # Affiche un message de déconnexion
    return redirect(url_for("donnees"))  # Redirige vers la page d'accueil après la déconnexion

# Définit la vue de connexion pour Flask-Login
login.login_view = "connexion"
