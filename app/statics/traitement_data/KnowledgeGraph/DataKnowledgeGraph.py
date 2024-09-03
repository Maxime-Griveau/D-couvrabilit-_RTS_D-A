import requests
from tqdm import tqdm
import json

base_url = "http://localhost:8983/solr/rtsarch/query"
json_file_path = "app/statics/datas/out/tout_thesaurus.json"
entité_field = "Entité"
id_thesaurus_field = "Id_thesaurus"

datedebut = 1962
datefin = 1962 #Test sur une seule année 

with open(json_file_path, mode="r", newline='', encoding='utf-8') as thesaurus:
    json_thesaurus = json.load(thesaurus)
    
# Décommenter pour tester sur un échantillon réduit de valeurs
json_thesaurus = json_thesaurus[:100]

# Dictionnaire pour stocker les GUID et les entités associées
data_list = []

for entity in tqdm(json_thesaurus): # Affiche une barre de progression
    params = {
        'q': f'CategorieAsset:Programme AND ContenuDocument:"{entity["Entité"]}"',
        'wt': 'json',
        'rows': '100000000',
        'fl': "Guid",  # Champs à retourner
        'fq': f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
    }
    response = requests.get(base_url, params=params, verify=False)
   
    if response.status_code == 200:
        data = response.json()
        for doc in data.get("response", {}).get("docs", []):
            guid = doc.get("Guid", "")
            identifiant = entity["Id_thesaurus"]
            nom = entity['Entité']
            data_list.append({"id": identifiant, "name": nom, "guid": guid})
    else:
        print(f"Erreur lors de la requête pour l'entité {entity['entité']}: {response.status_code}")

# Extraire les nœuds et les liens
nodes = {}
links = []

for item in data_list:
    th_id = item["id"]
    th_name = item["name"]
    guid = item["guid"]

    # Ajouter l'entité thésaurus comme nœud si elle n'existe pas
    if th_id not in nodes:
        nodes[th_id] = {"id": th_id, "name": th_name}

    # Ajouter le GUID comme nœud si il n'existe pas
    if guid not in nodes:
        nodes[guid] = {"id": guid, "name": guid}

    # Créer un lien entre l'entité thésaurus et le GUID
    links.append({"source": th_id, "target": guid})

# Convertir les nœuds en liste
nodes_list = list(nodes.values())

# Construire la structure JSON finale
jsonStructure = {
    "nodes": nodes_list,
    "links": links
}

# Sauvegarder le JSON dans un fichier
outfilePath = "app/statics/datas/out/DataGraphThesaurus.json"

with open(outfilePath, 'w', encoding='utf-8') as outfile:
    json.dump(jsonStructure, outfile, ensure_ascii=False, indent=4)

print(f"JSON généré et sauvegardé sous {outfilePath}")




print(f"Les données filtrées ont été exportée en json sous le nom de {outfilePath}")