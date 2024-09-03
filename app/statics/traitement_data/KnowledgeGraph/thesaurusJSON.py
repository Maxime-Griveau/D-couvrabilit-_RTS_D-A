import json 
import requests
import pandas as pd

### Création des fichier csv pour injection dans Neo4J

## Création du fichier thesaurus.csv, il va contenir toutes les entrées des thésaurus avec les occurences associées.

base_url = "http://localhost:8983/solr/rtsarch/query"

datedebut = 1900 
datefin = 2025

# Nom des champs thésaurus dans la base
fields_pivot = ["ThesaurusGEO", "ThesaurusMAT", "ThesaurusPM", "ThesaurusPP"]

all_data = []

id_counter = 1  # initialisation d'un compteur pour les identifiants 

for item in fields_pivot: #Pour chaque champ thésaurs 
    params = {
        'q': 'CategorieAsset:Programme',
        'wt': 'json',
        'rows': '20',
        'fl': 'idSupport',  # Champs à retourner 
        'fq': f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
        'facet': 'true',
        'facet.limit': '-1',
        'facet.pivot': item
    }

    response = requests.get(base_url, params=params, verify=False)
    data = response.json()

    data_fields = data["facet_counts"]["facet_pivot"][item] #Récupération du contenu

    for entry in data_fields:
        name = entry["value"] #De la valeur 
        count = entry["count"] #Des occurences 
        all_data.append({"Id_thesaurus": id_counter, "Type_Thesaurus": item, "Entité": name, "occurences_totales": count})
        #Création d'une liste de dictionnaires pour les stocker 
        id_counter +=1 #Incrémentation du compteur




# Export CSV 
output_file_path = "app/statics/datas/out/tout_thesaurus.json"
with open(output_file_path, "w", encoding='utf-8') as output_file:
    json.dump(all_data, output_file, indent=4, ensure_ascii=False)

print("Tous les thésaurus ont correctement été convertis en JSON :", output_file_path)



    