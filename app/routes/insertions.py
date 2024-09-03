from ..app import app, db
from flask import render_template, request, flash, abort, redirect, url_for
from ..models.formulaires import InsertionUsers
from flask_login import current_user, logout_user, login_user, login_required
from ..models.users import Users
from .users import admin_required


@app.route("/insertion/utilisateur", methods=['GET', 'POST'])
@app.route("/insertion_utilisateur/<int:page>", methods=['GET', 'POST'])
def insertion_utilisateur(page=1):
    form = InsertionUsers()
    nouvel_utilisateur = ""
    try:
        donnees = [] # Initialiser données comme une liste vide

        if form.validate_on_submit():
            mail = request.form.get("mail", None)
            pseudo = request.form.get("pseudo", None)
            mot_de_passe = request.form.get("mot_de_passe", None)
            if mail and pseudo and mot_de_passe:
                    nouvel_utilisateur, erreurs = Users().Ajout(pseudo=pseudo, password=mot_de_passe, mail=mail) # Si l'on ne met pas ", erreurs" ici python considère que notre variable est égale à un tuple car notre méthode renvoie un tuple avec l'erreur et le contenu de la notre requête
                    print(nouvel_utilisateur)
                    if nouvel_utilisateur:
                        flash(f"L'utilisateur {nouvel_utilisateur.pseudo} a bien été ajouté dans la base.", 'success')
                    else:
                        flash(f"L'utilisateur n'a pas été ajouté dans la base. Erreurs : ", 'error')
        else:
            flash("Merci d'indiquer vos informations de création de compte.", 'info')
     
    except Exception as e:
            print("Une erreur est survenue : " + str(e))
            flash("Une erreur s'est produite lors de l'ajout de l'utilisateur, avez-vous respecté les contraintes de saisie ?" + str(e), 'info')
            db.session.rollback()
            abort(500)

    return render_template("pages/ajout_utilisateur.html", sous_titre="Recherche", donnees=donnees, form=form, nouvel_utilisateur=nouvel_utilisateur)