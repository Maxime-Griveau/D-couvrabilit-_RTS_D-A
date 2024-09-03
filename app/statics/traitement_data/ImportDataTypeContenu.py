import requests
import pandas as pd 
import json


# URL de l'API

url = "http://localhost:8983/solr/rtsarch/query"

# Paramètres de la requête Solr
params = {
    'indent': 'true',
    'fl': 'Collection',
    'facet': 'true',
    'q': 'DureeSec>1',
    'facet.limit': '-1',
    'wt': 'json',
    'rows': '0',
    'facet.pivot': 'TypeContenu,idTypeContenu',
    'fq': 'DatePublication:[1900-01-01T00:00:00Z TO 2024-12-31T23:59:59Z]'
}

response = requests.get(url, params, verify=False)

data = response.json()


# Initialisation d'une liste pour stocker les données
data_list = []

nombre_réponses = data["response"]["numFound"]

# print(f'Le nombre de réponse est de {nombre_réponses}')

# Extraction des données du JSON
data_fields = data["facet_counts"]["facet_pivot"]["TypeContenu,idTypeContenu"]
for valeur in data_fields:
    type_contenu = valeur["value"]
    for pivot_data in valeur["pivot"]:
        identifiant_id = pivot_data["value"]
        count = pivot_data["count"]
        # Ajout des données dans la liste sous forme de dictionnaire
        data_list.append({"TypeContenu": type_contenu, "idTypeContenu": identifiant_id, "count": count})

# Création d'un DataFrame à partir de la liste
df = pd.DataFrame(data_list)



#Suppression des lignes contenant des UUID au lieu des valeurs décimales (absentes de Gico "valeurs fantomes")
mask = df['idTypeContenu'].str.match(r'[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}')

# Utilisez le masque pour sélectionner les lignes qui ne correspondent pas au critère
df = df[~mask]

#Remettre l'index à la bonne valeur après la suppression 

##  Recréation de la hiérarchie, les nombres seront mis au niveau 1, puis les chiffre à deux digits au niveau 2, etc. 

# On créé une fonction pour le faire 

def determiner_niveau(idTypeContenu):
    # Déterminer la longueur de l'idTypeContenu (si = 1 alors premier niveau, si égal 2 alors 2e niveau...)
    longueur = len(idTypeContenu)
    
    # Retourner le niveau en fonction de la longueur de l'idTypeContenu
    if longueur == 1:
        return 1
    elif longueur == 2:
        return 2
    elif longueur == 3:
        return 3
    elif longueur == 4:
        return 4
    else:
        return 1  # Si la longueur est différente de 1, 2, 3 ou 4 on retourne 1, car le seul cas où les émissions n'ont pas de valeur décimale de 1 à 4 digits c'est pour les valeurs multiples

# Ajout de la colonne "hiérarchie" en utilisant la méthode apply
df['hiérarchie'] = df['idTypeContenu'].apply(determiner_niveau)

#df.drop(df[df["count"] < 200].index, inplace=True) Supprimer les valeurs trop faibles 
     
if (df['hiérarchie'] == 1).any():
    # Diviser chaque élément de la colonne 'TypeContenu' en mots et appliquer la capitalisation de titre uniquement au premier mot, puis mettre en minuscule les mots suivants
    df['TypeContenu'] = df['TypeContenu'].str.split().str[0].str.title() + " " + df['TypeContenu'].str.split().str[1:].apply(lambda x: ' '.join(word.lower() for word in x))
    
    # print(df["TypeContenu"])

df.set_index(keys="TypeContenu", inplace=True)

df.reset_index(inplace=True)


## Transformation du df en fichier JSON hiéarchique (pour utilisation dans d3.js) 

def json_hierarchique(data):
    # Transformer le DataFrame en une liste de dictionnaires pour un traitement plus facile
    data_dict = data.to_dict('records')
    
    # Trier les données par hiérarchie pour assurer que les parents soient traités en premier
    data_sorted = sorted(data_dict, key=lambda x: x['hiérarchie'])
    
    # Un dictionnaire pour garder la trace des éléments ajoutés, clé = idTypeContenu, valeur = référence au dictionnaire de l'élément
    hierarchy = {}
    
    # L'objet JSON hiérarchique final
    root = {
        'name': 'Racine',  # Nom du nœud racine
        'idTypeContenu': '0',     # ID fictif pour la racine
        'value': "0",               # Compteur initial pour la racine, pourrait être recalculé si nécessaire
        'children': []            # Liste initiale vide pour les enfants de la racine
    }
    
    # Ajoutez la racine au dictionnaire pour référence future
    hierarchy['0'] = root
    
    # Construction de la hiérarchie
    for item in data_sorted:
        item_data = {
            'name': item['TypeContenu'],
            'idTypeContenu': item['idTypeContenu'],
            'value': item['count'],
            'children': []
        }
        
        if item['hiérarchie'] == 1:
            root['children'].append(item_data)  # Ajoutez directement au nœud racine
            hierarchy[item['idTypeContenu']] = item_data
        else:
            parent_id = None
            for i in range(len(item['idTypeContenu']) - 1, 0, -1):
                potential_parent_id = item['idTypeContenu'][:i]
                if potential_parent_id in hierarchy:
                    parent_id = potential_parent_id
                    break
            
            if parent_id:
                hierarchy[parent_id]['children'].append(item_data)
                hierarchy[item['idTypeContenu']] = item_data
    
    return root  # Retourne la racine qui contient maintenant toute la hiérarchie

# Utilisez cette fonction pour convertir le DataFrame en JSON hiérarchique
hierarchy_json = json_hierarchique(df)

output_file_path = "./app/statics/datas/out/TypeContenus.json"
with open(output_file_path, "w", encoding='utf-8') as output_file:
    json.dump(hierarchy_json, output_file, indent=4, ensure_ascii=False)

print("Le Type Contenu a correctement été transformé en JSON hiéarchique :", output_file_path)


# print(f'Le nombre de réponses est de {nombre_réponses}')

