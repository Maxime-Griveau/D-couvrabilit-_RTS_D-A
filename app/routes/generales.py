from ..app import app, db
from flask import render_template, request, flash, redirect, url_for
from sqlalchemy import or_
from flask_login import login_required
from .users import admin_required #import du décorateur admin requiered 





@app.route("/accueil")
@app.route("/")

def accueil():
    # from ..statics.traitement_data import HierarchieGeojson
    # from ..statics.traitement_data import GeojsonSuisseEtNombreOccurences
    # from ..statics.traitement_data.KnowledgeGraph import DataKnowledgeGraph
    # from ..statics.traitement_data.KnowledgeGraph import Clusterisation
    from ..statics.traitement_data import GeojsonMonde
    return render_template("partials/conteneur.html")

"""
    Route pour effectuer une recherche rapide sur le nom des pays et récupérer les résultats paginés.

    Méthodes acceptées
    ------------------
    GET

    Parameters
    ----------
    chaine : str, optional
        La chaîne de recherche pour filtrer les résultats des pays.

    Returns
    -------
    template
        Retourne le template des résultats de recherche avec les données paginées correspondant à la chaîne de recherche fournie.
"""


# @app.route("/recherche_rapide")
# @app.route("/recherche_rapide/<int:page>")
# def recherche_rapide(page=1):
#     chaine = request.args.get("chaine", None)
#     resultats = None
    
#     if chaine:
#         # Utilisation de la fonction filter() pour filtrer les résultats en fonction de la chaîne de recherche
#         donnees = db.session.query(
#             Formulaire.year, 
#             Pays.nom
#         ).join(Pays, Pays.noc == Formulaire.noc) \
#          .filter(
#              #notre recherche_rapide ne portera que sur le nom du pays car il nous a semblé que c'est la seule chose qu'on pourrait vouloir chercher dans notre base
#              Pays.nom.ilike(f"%{chaine}%")
#          ).group_by(
#             Formulaire.year, Pays.nom
#          ).paginate(page=page, per_page=10)  # Pagination: 10 résultats par page
#     else:
#         # Si aucune chaîne de recherche n'est fournie, retournez None
#         donnees = None
        
#     return render_template(
#         "pages/resultats_recherche.html", 
#         sous_titre="Recherche | " + chaine if chaine else "Recherche rapide",
#         donnees=donnees,
#         requete=chaine
#     )
