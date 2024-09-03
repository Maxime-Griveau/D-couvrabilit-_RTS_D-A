import pandas as pd
import json
import requests


## 1. Import du thésaurus "à plat" depuis SolR aves les occurences 

url = "http://localhost:8983/solr/rtsarch/query?indent=true&fl=Collection&facet=true&wt=json&facet.limit=-1&rows=10&q=CategorieAsset:Programme&facet.pivot=ThesaurusGEO"

response = requests.get(url)

data = response.json()



nombre_réponses = data["response"]["numFound"]

# print(f'Le nombre de réponse est de {nombre_réponses}')
data_list = []

data_fields = data["facet_counts"]["facet_pivot"]["ThesaurusGEO"]

for valeur in data_fields:
    name = valeur["value"]
    value = valeur["count"]
    data_list.append({"name":name, "value":value})

df_count = pd.DataFrame(data_list)


##2. Import du thésaurus "en mode hiérarchique"

df = pd.read_excel("./app/statics/datas/in/SUISSE_ThesaurusGEO.xlsx")


## 3. Création de la hiéarchie : chaque élément se voit attribuer un niveau
def mettre_a_jour_hierarchie(df, niveau):
    """ Fonction qui défini le niveau hiérarchique de chaque item dans la colonne, prendre en entrée un dataframe et un niveau"""
    for index, ligne in df[f"Niveau{niveau}"].items():
        if pd.notna(ligne) and ligne.strip() != "":
            df.at[index, "hiérarchie"] = niveau
    if niveau < 5: 
        mettre_a_jour_hierarchie(df, niveau + 1)

#Appel de la fonction, elle débute au niveau 1 
mettre_a_jour_hierarchie(df, 1)


# 4. Concaténation des valeurs dans une seule colonne, drop des anciennes et nettoyage des valeurs "NaN" 

 
df['entrée'] = df[['Niveau1', 'Niveau2', 'Niveau3', 'Niveau4', 'Niveau5']].apply(lambda x: ' '.join(x.dropna().astype(str)), axis=1)

df.drop(inplace=True, axis=1, columns=['Niveau1', 'Niveau2', 'Niveau3', 'Niveau4', 'Niveau5'])

## 5. Fusion des deux thésaurus pour que le thésaurus hiérarchique aie le compte d'occurences issu de SolR 

#D'abord on normalise les noms 
df['entrée_normalized'] = df['entrée'].str.lower().str.strip()

# Normalisation de la colonne 'name' de df_count
df_count['entrée_normalized'] = df_count['name'].str.lower().str.strip()
df_count.drop(["name"], axis=1, inplace=True)

# df_count (données SolR) comprend des entrées doublées, on les fusionne ainsi que leur valeur  avec un groupby
df_count_grouped = df_count.groupby('entrée_normalized').agg({'value': 'sum'}).reset_index()

# On fait ensuite une jointure des deux df avec la colonnes normalisées 
df_joined = df.merge(df_count_grouped, on='entrée_normalized', how='inner')

# Vérifier s'il y a encore des doublons dans df_joined 
# print(df_joined[df_joined.duplicated(subset='entrée_normalized', keep=False)])


# On supprime les valeurs NaN (not a number)
df_cleaned = df_joined.dropna()


# On converti les colonnes "hiérarchie" et "value" en entiers

df_cleaned["hiérarchie"] = df_cleaned["hiérarchie"].astype(int)
df_cleaned["value"] = df_cleaned["value"].astype(int)



# On peut supprimer la colonne sur laquelle on faisait les jointures  
df_cleaned.drop(["entrée_normalized"],axis=1, inplace=True)

# print(df_cleaned.head())

## 7. Création d'un JSON hiérarchique


def json_hierarchique(df):
  
    parent_nodes = {}  # Dictionnaire pour suivre les parents à chaque niveau de hiérarchie
    
    root = {  # Racine du JSON
        'name': 'ThésaurusGEO',
        'hiérarchie': '1',
        'value': '0',
        'children': []
    }
    parent_nodes[0] = root  # Le nœud racine est le parent du premier niveau

    # Parcours les lignes et créé la hiérarchie 
    for index, row in df.iterrows():
        current_node = {  # Créer le noeud actuel
            "name": row['entrée'],
            "hiérarchie": row['hiérarchie'],
            "value": row['value'],
            "type":"Point", #Type de coordonées géographiques (Norme geoJSON : https://fr.wikipedia.org/wiki/GeoJSON) 
            # Laissé vide pour populate avec données externes 
            "children": []
            
            
        }

        if row['hiérarchie'] > 0:  # Les nœuds au niveau 1 (supérieur à 0 qui est le niveau root) sont directement sous la racine
            # Trouver le parent direct dans les niveaux précédents
            parent = parent_nodes[row['hiérarchie'] - 1]
            parent['children'].append(current_node)  # Ajouter le noeud courant aux enfants du parent

        parent_nodes[row['hiérarchie']] = current_node  # Mettre à jour le dernier noeud à ce niveau

    return root

#Les valeurs NaN sont remplacées par la chaine NA| pour éviter les erreurs et pouvoir les sélectionner facillement avec un regex si le besoin se présente

df_cleaned.fillna("NA|", inplace=True)
hierarchy_json = json_hierarchique(df_cleaned)



## Export du fichier 

output_file_path = "./app/statics/datas/out/thesaurusGEO.json"
with open(output_file_path, "w", encoding='utf-8') as output_file:
    json.dump(hierarchy_json, output_file, indent=4, ensure_ascii=False)

print("Le Thésaurus Géographique a correctement été converti en JSON hiérarchique :", output_file_path)
