from ..app import app
from flask import render_template, request, flash, redirect, url_for



@app.route("/launch_code")
def clusterisation_exec():
    # from ..statics.traitement_data.Clusterisation import similarite_metriquev1
    from ..statics.traitement_data.Clusterisation import generationthesaurus
    # from ..statics.traitement_data.Clusterisation import TAL_ThesaurusGEO
    return render_template("pages/clusterisation/similarite_metrique.html")

