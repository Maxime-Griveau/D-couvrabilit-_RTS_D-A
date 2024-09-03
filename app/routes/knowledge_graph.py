from ..app import app, db
from flask import render_template, request, flash, redirect, url_for, jsonify
import requests
import json
from ..statics.utils.escape_solr_special_chars import escape_solr_special_chars
from datetime import datetime
from hashlib import md5



@app.route("/knowledge_graph_explications")
def knowledge_graph_explications():
    return render_template("pages/knowledge_graph/knowledge_graph_explications.html")


@app.route("/recherche_knowledge_graph")
def recherche_knowledge_graph_affichage():
    return render_template("pages/knowledge_graph/recherche_knowledge_graph.html")

@app.route("/recherche_knowledge_graph", methods=['POST'])
def recherche_knowledge_graph():
    """Route qui récupère les valeurs des formulaires et renvoie les données traitées par get_filtered_data
    

    Returns:
        json: guid des entités, liens vers la fiche Gico correspondante et noms des entités recherchées 
    """
    entite1 = request.json.get("Entite1", None)
    entite2 = request.json.get("Entite2", None)
    entite3 = request.json.get("Entite3", None)
    entite4 = request.json.get("Entite4", None)

    slider = request.json.get("slider", None)
    excludeMetadata = request.json.get("excludeMetadata", False)
    seulThesaurus = request.json.get("seulThesaurus", False)
    
    print(slider)
    data = get_filtered_data(entite1, entite2, entite3, entite4, slider, excludeMetadata, seulThesaurus)

    return jsonify(data)
    

def get_filtered_data(entite1=None, entite2=None, entite3=None, entite4=None, dates=[1954, 2024], excludeMetadata=False, seulThesaurus=False):
    base_url = "http://localhost:8983/solr/rtsarch/query"
    datedebut = dates[0]
    datefin = dates[1]

    print("Vous avez choisi d'associer", entite1, "à", entite2, entite3, entite4)
    print("Vous avez sélectionné les dates suivantes :", dates)
    print("Exclusion des métadonnés automatiques et du speech to text ?", excludeMetadata)
    print("Exclusion du thésaurus ?", seulThesaurus)

   

    def fetch_guids_for_entity(entity_name, excludeMetadata, seulThesaurus):
        if not entity_name:
            return []

        if seulThesaurus:
            fields_list = ["ThesaurusGEO_flou", "ThesaurusMAT_flou", "ThesaurusPP_flou", "ThesaurusPM_flou"]
        elif excludeMetadata:
            fields_list = ['Resume_exact', 'Titre_exact', "ThesaurusGEO_flou", "ThesaurusMAT_flou", "ThesaurusPP_flou", "ThesaurusPM_flou"]
        else:
            fields_list = ['ContenuDocument_exact', 'MetadonneesAutomatiques_exact', 'Resume_exact', 'Titre_exact', "ThesaurusGEO_flou", "ThesaurusMAT_flou", "ThesaurusPP_flou", "ThesaurusPM_flou"]

        query_parts = [f"{field}:{escape_solr_special_chars(entity_name)}" for field in fields_list]
        query_finale = " OR ".join(query_parts)

        params = {
            'q': f'CategorieAsset:Sujet AND ({query_finale})',
            'wt': 'json',
            'rows': '1000000000',
            'fl': 'Guid',
            'fq': [
            f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
            'DureeMediaSec:[15 TO 1500]',
            'Achat:"Non"'
        ],
        }

        response = requests.get(base_url, params=params, verify=False)
        print(f"Requête Solr: {response.url}")
        print("Réponse de Solr:", response.status_code)

        data_list = []

        if response.status_code == 200:
            data = response.json()
            for doc in data.get("response", {}).get("docs", []):
                guid = doc.get("Guid", "")
                data_list.append({"name": entity_name, "guid": guid})
        else:
            print(f"Erreur lors de la requête pour l'entité {entity_name}: {response.status_code}")

        return data_list

    data_list_entite1 = fetch_guids_for_entity(entite1, excludeMetadata, seulThesaurus)
    data_list_entite2 = fetch_guids_for_entity(entite2, excludeMetadata, seulThesaurus)
    data_list_entite3 = fetch_guids_for_entity(entite3, excludeMetadata, seulThesaurus) if entite3 else []
    data_list_entite4 = fetch_guids_for_entity(entite4, excludeMetadata, seulThesaurus) if entite4 else []

    guids_entite1 = {item["guid"] for item in data_list_entite1}
    guids_entite2 = {item["guid"] for item in data_list_entite2}
    guids_entite3 = {item["guid"] for item in data_list_entite3} if data_list_entite3 else set()
    guids_entite4 = {item["guid"] for item in data_list_entite4} if data_list_entite4 else set()

    if guids_entite3 and guids_entite4:
        common_guids = guids_entite1 & guids_entite2 & guids_entite3 & guids_entite4
    elif guids_entite3:
        common_guids = guids_entite1 & guids_entite2 & guids_entite3
    elif guids_entite4:
        common_guids = guids_entite1 & guids_entite2 & guids_entite4
    else:
        common_guids = guids_entite1 & guids_entite2

    print(common_guids)

    def fetch_gico_links(common_guids):
        url_base_gico = "https://rtsarchives.media.int/tsr-intranet-media/public/asset.do?id="
        liens_Gico = []
        DatePublication = []
        nombre_noeuds = 0
        Collection = []
        for guid in common_guids:
            params = {
                'q': f'CategorieAsset:Sujet AND Guid:"{guid}"',
                'wt': 'json',
                'rows': '1000000000',
                'fl': 'idGICO, Collection, DatePublication',
                'fq': f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
            }
            response = requests.get(base_url, params=params, verify=False)
            if response.status_code == 200:
                data = response.json()
                for doc in data.get("response", {}).get("docs", []):
                    idGICO = doc.get("idGICO")
                    Collection.append(doc.get("Collection", "Collection inconnue"))
                    DatePublication.append(doc.get("DatePublication", "Date inconnue"))
                    lienGico = url_base_gico + str(idGICO)
                    liens_Gico.append(lienGico)
                    nombre_noeuds += 1
            else:
                print(f"Erreur lors de la requête pour le guid {guid}: {response.status_code}")
                
        
        return liens_Gico, nombre_noeuds, Collection, DatePublication

    liens_Gico, nombre_noeuds, Collection, DatePublication = fetch_gico_links(common_guids)
    
    
    nodes = {}
    links = []

    for item in data_list_entite1 + data_list_entite2 + data_list_entite3 + data_list_entite4:
        if item["guid"] in common_guids:
            name = item["name"]
            guid = item["guid"]
            
            if name not in nodes:
                nodes[name] = {"id": name, "name": name}
            if guid not in nodes:
                nodes[guid] = {"id": guid, "name": guid}

            links.append({"source": name, "target": guid})

    nodes_list = list(nodes.values())

    json_structure = {
        "nodes": nodes_list,
        "links": links
    }

    return [{"json_structure": json_structure, "url": liens_Gico, "nombre_noeuds": nombre_noeuds, "Collection":Collection, "DatePublication":DatePublication}]