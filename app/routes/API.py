from flask import Flask, request, jsonify, flash, redirect, url_for, render_template, send_from_directory, after_this_request
from ..app import app
from ..statics.utils.escape_solr_special_chars import escape_solr_special_chars
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
import unidecode
import requests

# Import de la liste des villes et districts problématiques
villes_problematiques = ['Au','Bulle', 'Vals', 'Port', 'Le Lieu', 'La Verrerie', 'Rue', 'Premier', 'Sâles', 'Court', 'Le Vaud', 'Champion', 'Alle', 'Les Bois', 'Crans', 'Roche', 'La Roche', 'Roches', 'Bassins', 'Les Enfers', 'Bière', 'Champagne', 'Granges', 'La Bourg', 'Chapelle', 'Bâche', 'Perles', 'Vallon', "L'Abbayes", 'Provence']
districts_problematiques = ['See', 'March']
    

def execute_query(query_params):
    """Fonction qui exécute une recherche dans l'API solr en fonction des paramètres 
    Args:
        query_params (list): paramètre de la recherche
    Returns:
        retourne le résultat de la recherche sous forme de json utilisable par js 
    """
    base_url = "http://localhost:8983/solr/rtsarch/query"
    
    try:
        response = requests.get(base_url, params=query_params, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

def calculate_percentile(values, percentile):
    """Calcule les percentiles pour chaque valeur donnée en entrée"""
    index = (percentile / 100) * (len(values) - 1)
    if int(index) == index:
        return values[int(index)]
    else:
        lower = values[int(index)]
        upper = values[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))

def get_min_max_percentiles(values):
    """Calcule les percentiles des valeurs minimales et maximales"""
    values.sort()
    min_value = calculate_percentile(values, 5)
    max_value = calculate_percentile(values, 95)
    return min_value, max_value

def normalize_thesaurus_term(term):
    """Convertit un terme en majuscules et sans accents pour les recherches dans les thésaurus (car les valeurs dans le thésaurus sont en majuscules et sans accents)"""
    return unidecode.unidecode(term).upper()

def execute_solr_query(seulThesaurus=False, geo_value=None, include_id_support=False, exclusion_metadonnees=False, recherche_clause=None, datedebut=None, datefin=None):
    base_url = "http://localhost:8983/solr/rtsarch/query"
    fields_GEO = ['Resume_exact', 'Titre_exact', 'ThesaurusGEO_flou']
    if not exclusion_metadonnees:
        fields_GEO.extend(['ContenuDocument_exact', 'MetadonneesAutomatiques_exact'])
    
    geo_clause = ""
    if geo_value:
        geo_value_escaped = escape_solr_special_chars(geo_value)
        if seulThesaurus or geo_value in villes_problematiques or geo_value in districts_problematiques:
            fields_GEO = ['ThesaurusGEO']
            geo_value_escaped = normalize_thesaurus_term(geo_value)
        geo_clause = " OR ".join([f'{field}:"{geo_value_escaped}"' for field in fields_GEO])
    
    query_finale = f"({geo_clause})"
    if recherche_clause:
        query_finale = f"({recherche_clause}) AND ({geo_clause})" if geo_clause else f"({recherche_clause})"

    params = {
        'q': f'{query_finale}',
        'wt': 'json',
        'rows': '100' if include_id_support else '0', #Nombre de résultats à augmenter en production
        'fl': 'idSupport, Guid, idGICO, DatePublication, Titre' if include_id_support else 'id',
        'fq': [
            f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
            'DureeMediaSec:[15 TO *]',
            'Achat:"Non"'
        ],
        'boost': 'ThesaurusGEO_flou^4 Titre^3 Resume^2'  # On booste certains champs car ils sont plus signifiants
    }

    data = execute_query(params)
    if isinstance(data, tuple) and data[1] == 500:
        return data

    result_entry = {
        "NombreResultats": data['response']['numFound'],
        "NAME": geo_value,
        "UMID": [],
        "idGICO" : [],
        "Titre":[],
        "Date" : [],
        "GUID" : []
    }
    df_entry = pd.DataFrame()
    if include_id_support and data['response']['numFound'] > 0:
        entries = []

        for valeur in data["response"]["docs"]:
            entry = {}
            UMIDS = []
            
            
            if "idSupport" in valeur:
                base_url_player = "https://rtsarchives.media.int/tsr-intranet-media/player5/index.html?umid="
                UMIDS = valeur['idSupport']
                UMIDS_list = []  # Initialisez une liste vide pour stocker les UMID commençant par "Z"

                for UMID in UMIDS:
                    if UMID.startswith("Z"):
                        lienPlayer = base_url_player + str(UMID) + "&pos=1"
                        UMIDS_list.append(lienPlayer)  # Ajoutez le lien directement à la liste
  
                    # Pas besoin d'ajouter les UMIDs qui ne commencent pas par "Z" à UMIDS_list, donc retirez ce bloc else

                entry["UMID"] = UMIDS_list
                

            if "idGICO" in valeur:
                base_url_gico = "https://rtsarchives.media.int/tsr-intranet-media/public/asset.do?id="
                lienGico = base_url_gico + str(valeur["idGICO"])
                entry["idGICO"] = lienGico

            if "Titre" in valeur:
                entry["Titre"] = valeur["Titre"]

            if "DatePublication" in valeur:
                DatePublication = valeur["DatePublication"][0:10]
                entry["Date"] = DatePublication
            
            if "Guid" in valeur:
                entry["GUID"] = valeur["Guid"]
            
        
            
            entries.append(entry)

        # Trier les entrées par DatePublication (du plus récent au plus ancien)
        entries.sort(key=lambda x: x.get("Date", ""), reverse=True)
        
        df_entry = pd.DataFrame(entries, columns=["UMID", "idGICO", "Titre", "GUID", "Date"])
        for entry in entries:
            result_entry["UMID"].extend(entry["UMID"])
            result_entry["idGICO"].append(entry.get("idGICO", ""))
            result_entry["Titre"].append(entry.get("Titre", ""))
            result_entry["GUID"].append(entry.get("GUID", ""))
            DatePublication = entry.get("Date", "")
            if DatePublication:
                Annee = DatePublication[0:4]
                Mois = DatePublication[5:7]
                Jour = DatePublication[8:10]
                DateJJMMHH = Jour + "/" + Mois + "/" + Annee
                result_entry["Date"].append(DateJJMMHH)
            else:
                result_entry["Date"].append("")
 
   
    return result_entry, df_entry

@app.route('/carte_cliqueeV2', methods=['POST'])
def process_clickv2():
    """Gestion des requêtes fetch envoyées depuis l'application."""
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported Media Type"}), 415

    # Variables utilisées : 
    data = request.get_json()
    recherche = data.get('entite1', None)
    layer = data.get('layer', None)
    GEO = data.get('name', None)
    exclusion_metadonnees = data.get('excludeMetadata', False)
    dates = data.get('slider', [1954, 2024])
    datedebut = dates[0]
    datefin = dates[1]
    export = data.get('export', False)
    seulThesaurus = data.get('seulThesaurus', False)
    df_recherche = pd.read_csv(f"app/statics/datas/out/{layer}_name.csv", sep=',', header=0)
    jsonNombreResultats_List = []
    
    print("Années choisies :", datedebut, " - ", datefin)
    print("Layer actuel", layer)
    print("Exclusion du speech to text", exclusion_metadonnees) 
        
    print("Vous avez choisi d'exporter", export)
    # Construction de la clause de recherche pour SOLR
    recherche_clause = ""
    
    if recherche:
        print("RECHERCHE EFFECTUÉE :", recherche)
        recherche_escaped = escape_solr_special_chars(recherche)
        fields_Recherche = ['Resume_exact', 'Titre_exact', 'ThesaurusGEO_flou', 'ThesaurusMAT_flou', 'ThesaurusPM_flou', 'ThesaurusPP_flou']
        if not exclusion_metadonnees:
            fields_Recherche.extend(['ContenuDocument_exact', 'MetadonneesAutomatiques_exact'])
            recherche_escaped = normalize_thesaurus_term(recherche)
        if seulThesaurus:
            fields_Recherche = ['ThesaurusGEO_flou', 'ThesaurusMAT_exact', 'ThesaurusPM_exact', 'ThesaurusPP_exact']
            
        recherche_clause = " OR ".join([f"{field}:\"{recherche_escaped}\"" for field in fields_Recherche])
        print("Clause de recherche simple", recherche_clause)
    # Utilisation de ThreadPoolExecutor pour paralléliser les appels à execute_solr_query (un worker par coeur logique du processeur est recommandé)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        
        if GEO:
            # Si GEO est sélectionné, calculer les résultats uniquement pour ce territoire
            print("TERRITOIRE SÉLECTIONNÉ :", GEO)
            futures.append(executor.submit(execute_solr_query, seulThesaurus, GEO, True, exclusion_metadonnees, recherche_clause, datedebut, datefin))
        else:
            # Si GEO n'est pas sélectionné, calculer les résultats pour chaque NAME du layer
            for index, row in df_recherche.iterrows():
                geo_value = str(row["NAME"])
                futures.append(executor.submit(execute_solr_query, seulThesaurus, geo_value, False if not recherche else True, exclusion_metadonnees, recherche_clause, datedebut, datefin))

        for future in as_completed(futures):
            result_entry, df_entry = future.result()
            jsonNombreResultats_List.append(result_entry)

    # Calculer les valeurs min et max en utilisant la fonction get_min_max_percentiles
    nombre_resultats_values = [entry["NombreResultats"] for entry in jsonNombreResultats_List]
    min_value, max_value = get_min_max_percentiles(nombre_resultats_values)

    export_file_path = None

    if export and not GEO:
        print("Export des données globales de la carte")
        timestr = time.strftime("%d-%m-%Y_%Hh%M-%Ssecs")
        data_export = []
        for result in jsonNombreResultats_List:
            data_export.append({"Territoire": result["NAME"], "NombreResultats": result["NombreResultats"]})
        df_export = pd.DataFrame(data_export)

        if recherche:
            df_export["Recherche_associée"] = recherche
        df_export.sort_values(by=["NombreResultats"], axis=0, inplace=True, ascending=False)
        df_export.reset_index(inplace=True, drop=True)
        df_export.drop_duplicates(inplace=True)

        export_file_path = f"app/statics/datas/out/carte/export_donnees_{timestr}.xlsx"
        if recherche:
            export_file_path = f"app/statics/datas/out/carte/export_donnees_Recherche_{recherche}_{timestr}.xlsx"
        df_export.to_excel(export_file_path)
        
    #Si un territoire est sélectionné : l'export change, l'utilisateur aura le tableau des résultat global
    if export and GEO:
        print("Export du territoire géographique sélectionné") 
        timestr = time.strftime("%d-%m-%Y_%Hh%M-%Ssecs")
        df_entry_renomme = df_entry.rename(columns={"idGICO":"Lien vers l'asset (GICO)", "UMID":"Lien de visionnage"})
        print(df_entry_renomme)
        
        # Conversion des listes en chaînes de caractères séparées par des virgules
        df_entry_renomme['Lien de visionnage'] = df_entry_renomme['Lien de visionnage'].apply(lambda x: ', '.join(x))
        
        df_entry_renomme["Territoire sélectionné"] = GEO
        df_entry_renomme = df_entry_renomme[["Territoire sélectionné", "Titre", "GUID", "Date", "Lien vers l'asset (GICO)", "Lien de visionnage"]]
     
        
        if recherche:
            df_entry_renomme["Recherche_associée"] = recherche
            export_file_path = f"app/statics/datas/out/carte/export_donnees_{timestr}_pays_{GEO}_recherche_{recherche}.xlsx"
        
        
        export_file_path = f"app/statics/datas/out/carte/export_donnees_{timestr}_Territoire_{GEO}.xlsx"
        
        df_entry_renomme.to_excel(export_file_path)
      
    response_data = {
        "results": jsonNombreResultats_List,
        "minMax": {
            "min": min_value,
            "max": max_value
        }
    }

    if export_file_path:
        response_data["download_url"] = url_for('download_file', filename=os.path.basename(export_file_path))

    return jsonify(response_data)

@app.route('/download/<filename>')
def download_file(filename):
    """Route pour télécharger le fichier exporté et le supprimer après téléchargement."""
    directory = os.path.join(app.root_path, 'statics', 'datas', 'out', 'carte')

    @after_this_request
    def remove_file(response):
        """Retire le fichier une fois téléchargé
        Args:
            response (string): réponse du serveur 
        Returns:
            Retourne la réponse et supprime le fichier
        """
        try:
            os.remove(os.path.join(directory, filename))
        except Exception as error:
            app.logger.error("Error removing or closing downloaded file handle", error)
        return response

    return send_from_directory(directory=directory, path=filename, as_attachment=True)
