from flask import render_template, jsonify, request
from ..app import app, db
import json
from ..models.formulaires import RechercheCarte
import pandas as pd 
import requests
from itertools import zip_longest
from ..statics.utils.escape_solr_special_chars import escape_solr_special_chars



@app.route("/visualisation/thesaurusgeo")
def thesaurusgeo():

    from ..statics.traitement_data import HierarchieThesaurusGEO #Import dans la route afin d'éviter le chargement des données à chaque démarrage de l'application 


    return render_template("pages/visualisations/ThesaurusGEOSunburst.html")

@app.route("/visualisation/thesaurusGEO/fetch",  methods=['POST'])
def fetch_thesaurusGEO():
    
    Recherche = request.json.get("Recherche", "")
    
    print("Recherche en cours :", Recherche)
    if Recherche:
        escape_solr_special_chars(Recherche)
        data = request_solr_pivot(Recherche)
    else:
        data=request_solr_pivot("*:*")
    
    return jsonify(data)
  

def request_solr_pivot(recherche="*:*"):
    print("Valeur recherchée", recherche)
    base_url = "http://localhost:8983/solr/rtsarch/query"
    params = {
        'q': f'{recherche}',
        'indent': 'true',
        'fl': 'idSupport, Guid, idGICO, DatePublication, Titre',
        'facet': 'true',
        'wt': 'json',
        'facet.limit': '-1',
        'rows': '0'
    }

    # Construire l'URL avec plusieurs pivots
    pivot_params = '&facet.pivot=ThesaurusGEO&facet.pivot=ThesaurusMAT'
    response = requests.get(base_url, params=params, verify=False)
    full_url = response.url + pivot_params

    response = requests.get(full_url, verify=False)
    print(f"Requête Solr : {response.url}")
    print("Réponse de Solr:", response.status_code)

 

    if response.status_code == 200:
        data = response.json()
    else:
        print(f"Erreur lors de la requête pour la recherche {recherche}: {response.status_code}")

    # Import des thésaurus "à plat" depuis SolR avec les occurrences
    data_list_pivot_GEO = []
    data_list_pivot_MAT = []
    
    data_fields_GEO = data["facet_counts"]["facet_pivot"]["ThesaurusGEO"]

    for valeur in data_fields_GEO:
        name = valeur["value"]
        value = valeur["count"]
        data_list_pivot_GEO.append({"name": name, "value": value})

    df_count_GEO = pd.DataFrame(data_list_pivot_GEO)

    data_fields_MAT = data["facet_counts"]["facet_pivot"]["ThesaurusMAT"]

    for valeur in data_fields_MAT:
        name = valeur["value"]
        value = valeur["count"]
        data_list_pivot_MAT.append({"name": name, "value": value})

    df_count_MAT = pd.DataFrame(data_list_pivot_MAT)

    # Import des thésaurus "en mode hiérarchique"
    df_GEO = pd.read_excel("./app/statics/datas/in/SUISSE_ThesaurusGEO.xlsx")
    df_MAT = pd.read_excel("./app/statics/datas/in/ThesaurusMAT.xlsx")

    # Pré-remplir les DataFrames avec tous les niveaux nécessaires
    def pre_remplir_df(df, niveaux):
        for i in range(1, niveaux + 1):
            if f'Niveau{i}' not in df.columns:
                df[f'Niveau{i}'] = ""
        return df

    df_GEO = pre_remplir_df(df_GEO, 5)
    df_MAT = pre_remplir_df(df_MAT, 11)

    # Création de la hiérarchie : chaque élément se voit attribuer un niveau
    def mettre_a_jour_hierarchie(df, niveau, nombre_niveaux):
        for index, ligne in df[f"Niveau{niveau}"].items():
            if pd.notna(ligne) and ligne.strip() != "":
                df.at[index, "hiérarchie"] = niveau
        if niveau < nombre_niveaux:
            mettre_a_jour_hierarchie(df, niveau + 1, nombre_niveaux)

    # Appel de la fonction, elle débute au niveau 1
    mettre_a_jour_hierarchie(df_GEO, 1, 5)
    mettre_a_jour_hierarchie(df_MAT, 1, 11)

    # Concaténation des valeurs dans une seule colonne, drop des anciennes et nettoyage des valeurs "NaN"
    def concatener_niveaux(df, nombre_niveaux):
        niveaux = [f'Niveau{i}' for i in range(1, nombre_niveaux + 1)]
        df['entrée'] = df[niveaux].apply(lambda x: ' '.join(x.dropna().astype(str)), axis=1)
        df.drop(inplace=True, axis=1, columns=niveaux)

    concatener_niveaux(df_GEO, 5)
    concatener_niveaux(df_MAT, 11)

    # Fusion des thésaurus pour que le thésaurus hiérarchique ait le compte d'occurrences issu de SolR
    def fusionner_thesaurus(df, df_count):
        df['entrée_normalized'] = df['entrée'].str.lower().str.strip()
        df_count['entrée_normalized'] = df_count['name'].str.lower().str.strip()
        df_count.drop(["name"], axis=1, inplace=True)

        df_count_grouped = df_count.groupby('entrée_normalized').agg({'value': 'sum'}).reset_index()

        df_joined = df.merge(df_count_grouped, on='entrée_normalized', how='left')

        df_joined['value'] = df_joined['value'].fillna(0).astype(int)

        df_joined.drop(["entrée_normalized"], axis=1, inplace=True)
        
        return df_joined

    df_cleaned_GEO = fusionner_thesaurus(df_GEO, df_count_GEO)
    df_cleaned_MAT = fusionner_thesaurus(df_MAT, df_count_MAT)

    # Assurez-vous que les valeurs de la colonne 'hiérarchie' sont bien des entiers
    df_cleaned_GEO['hiérarchie'] = pd.to_numeric(df_cleaned_GEO['hiérarchie'], errors='coerce').fillna(0).astype(int)
    df_cleaned_MAT['hiérarchie'] = pd.to_numeric(df_cleaned_MAT['hiérarchie'], errors='coerce').fillna(0).astype(int)

    # Création des JSONs hiérarchiques
    def json_hierarchique(df, root_name):
        parent_nodes = {}
        
        root = {
            'name': root_name,
            'hiérarchie': 1,  # Assurez-vous que c'est un entier
            'value': 0,
            'children': []
        }
        parent_nodes[0] = root

        for index, row in df.iterrows():
            current_node = {
                "name": row['entrée'],
                "hiérarchie": row['hiérarchie'],
                "value": row['value'],
                "children": []
            }

            parent_level = row['hiérarchie'] - 1
            if parent_level in parent_nodes:
                parent = parent_nodes[parent_level]
                parent['children'].append(current_node)
            else:
                print(f"Warning: parent level {parent_level} not found for row {index}")
                continue
                    
            parent_nodes[row['hiérarchie']] = current_node
            
        return root

    df_cleaned_GEO.fillna("NA|", inplace=True)
    df_cleaned_MAT.fillna("NA|", inplace=True)

    hierarchy_json_GEO = json_hierarchique(df_cleaned_GEO, 'ThésaurusGEO')
    hierarchy_json_MAT = json_hierarchique(df_cleaned_MAT, 'ThésaurusMAT')

    # Export des fichiers JSON
    output_file_path_GEO = "./app/statics/datas/out/thesaurusGEO.json"
    with open(output_file_path_GEO, "w", encoding='utf-8') as output_file:
        json.dump(hierarchy_json_GEO, output_file, indent=4, ensure_ascii=False)
    print("Le Thésaurus Géographique a correctement été converti en JSON hiérarchique :", output_file_path_GEO)

    output_file_path_MAT = "./app/statics/datas/out/thesaurusMAT.json"
    with open(output_file_path_MAT, "w", encoding='utf-8') as output_file:
        json.dump(hierarchy_json_MAT, output_file, indent=4, ensure_ascii=False)
    print("Le Thésaurus Matières a correctement été converti en JSON hiérarchique :", output_file_path_MAT)

    return hierarchy_json_GEO, hierarchy_json_MAT
@app.route("/visualisation/thesaurusmat")
def thesaurusmat():

    from ..statics.traitement_data import HierarchieThesaurusMAT#Import dans la route afin d'éviter le chargement des données à chaque démarrage de l'application 

    return render_template("pages/visualisations/ThesaurusMATSunburst.html")



@app.route("/visualisation/typecontenu")
def typecontenu():
    from ..statics.traitement_data import ImportDataTypeContenu#Import dans la route afin d'éviter le chargement des données à chaque démarrage de l'application 
    

    return render_template("pages/visualisations/CodeContenuTreemap.html")

@app.route("/visualisation/carte")
def carte():
    return render_template("pages/visualisations/carte.html")

@app.route("/visualisation/cartev2")
def cartev2():
    return render_template("pages/visualisations/cartev2.html")

@app.route("/visualisation/monde")
def carteMonde():
    return render_template("pages/visualisations/carteMonde.html")



@app.route('/visualisation/cartev2/villes_problematiques')
def villes_problematiques():
    
    # Import de la liste des villes et districts problématiques
    villes_problematiques = ['Au', 'Bulle','Vals', 'Port', 'Le Lieu', 'La Verrerie', 'Rue', 'Premier', 'Sâles', 'Court', 'Le Vaud', 'Champion', 'Alle', 'Les Bois', 'Crans', 'Roche', 'La Roche', 'Roches', 'Bassins', 'Les Enfers', 'Bière', 'Champagne', 'Granges', 'La Bourg', 'Chapelle', 'Bâche', 'Perles', 'Vallon', "L'Abbayes", 'Provence']
    
    districts_problematiques = ['See', 'March']
    
    # Combine les villes et les districts en utilisant zip_longest pour gérer les listes de longueurs différentes
    territoires = []
    for ville, district in zip_longest(villes_problematiques, districts_problematiques, fillvalue=''):
        territoires.append({"ville": ville, "district": district})

    return render_template("pages/visualisations/territoires_problematiques.html", territoires=territoires)
