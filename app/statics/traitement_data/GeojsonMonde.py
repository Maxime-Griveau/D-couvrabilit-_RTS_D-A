import geopandas as gpd
import pandas as pd 
import requests

# URL du fichier GeoJSON
url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"

# Effectuer la requête pour obtenir le contenu du fichier
response = requests.get(url)

path_in = "app/statics/datas/out/carte/countries.geo.json"

# Vérifier si la requête a réussi
if response.status_code == 200:
    # Stocker le contenu du fichier dans un fichier local
    with open(path_in, 'wb') as f:
        f.write(response.content)
    print("Le fichier a été téléchargé et stocké avec succès.")
else:
    print(f"Erreur lors du téléchargement du fichier. Statut de la requête : {response.status_code}")


gdf = gpd.read_file(path_in)
gdf


#Comme notre dataset est en anglais, on va utiliser Wikidata pour récupérer les noms français et les code ISO pour une traduction en français des noms de pays 

url = 'https://query.wikidata.org/sparql'
query = '''

SELECT DISTINCT ?country ?countryLabel ?countrycode 
WHERE
{
  ?country wdt:P31 wd:Q3624078 .
  # Not a former country
  ?country wdt:P298 ?countrycode .
  FILTER NOT EXISTS {?country wdt:P31 wd:Q3024240} .
  # And not an ancient civilization (needed to exclude ancient Egypt)
  FILTER NOT EXISTS {?country wdt:P31 wd:Q28171280} .

  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}
ORDER BY ?countryLabel


'''
r = requests.get(url, params={'format': 'json', 'query': query})

if r.status_code == 200:
    datas = r.json()
    data_fields = datas["results"]["bindings"]
    data_list = []
    for data in data_fields:
            pays = data["countryLabel"]["value"]
            id= data["countrycode"]["value"]
            data_list.append({"NAME": pays, "id": id})
else:
    print("Erreur de récupération des données de Wikidata concernant les communes (traduction des noms de communes en français), ça arrive souvent : relancez la requête")


df_paysfr = pd.DataFrame(data_list)

# Ajout des pays et territoires manquants dans wikidata 
nouvelles_lignes = [
    pd.DataFrame({"NAME": ["Danemark"], "id": ["DNK"]}),
    pd.DataFrame({"NAME": ["Groenland"], "id": ["GRL"]}),
    pd.DataFrame({"NAME": ["Antarctique"], "id": ["ATA"]}),
    pd.DataFrame({"NAME": ["Sahara Occidental"], "id": ["ESH"]}),
    pd.DataFrame({"NAME": ["Somaliland"], "id": ["-99"]}),
    pd.DataFrame({"NAME": ["Guyane"], "id": ["GUF"]}),
    pd.DataFrame({"NAME": ["Kosovo"], "id": ["CS-KM"]}),
    pd.DataFrame({"NAME": ["Porto Rico"], "id": ["PRI"]}),  
    pd.DataFrame({"NAME": ["Îles Falkland"], "id": ["FLK"]}),  
    pd.DataFrame({"NAME": ["Bermudes"], "id": ["BMU"]}),  
    pd.DataFrame({"NAME": ["Terres australes et antarctiques françaises"], "id": ["ATF"]}),
    pd.DataFrame({"NAME": ["Nouvelle-Calédonie"], "id": ["NCL"]})
]

# Concaténation avec pd.concat()
df_paysfr = pd.concat([df_paysfr] + nouvelles_lignes, ignore_index=True)

df_paysfr.to_clipboard()

#Remplacement des valeurs de certains pays par celles connues du Speech to text
df_paysfr.replace(to_replace="Viêt Nam", value="Vietnam", inplace=True)
df_paysfr.replace(to_replace="république populaire de Chine", value="Chine", inplace=True)
df_paysfr.replace(to_replace="République centrafricaine", value="Centrafrique", inplace=True)
df_paysfr.replace(to_replace="Royaume des Pays-Bas", value="Pays-Bas", inplace=True)
df_paysfr.replace(to_replace="État de Palestine", value="Palestine", inplace=True)
df_paysfr.replace(to_replace="États-Unis", value="USA", inplace=True)


print(df_paysfr.head())

df_paysfr.to_csv("app/statics/datas/out/countries_name.csv")


gdf = gdf.merge(df_paysfr, on="id", how="left")
gdf.drop(["name"], axis=1, inplace=True)


# Écrire le GeoJSON corrigé
output_geojson = 'app/statics/datas/out/carte/countries_corrigé.geojson'
gdf.to_file(output_geojson, driver='GeoJSON')

print(f'GeoJSON corrigé écrit avec succès à : {output_geojson}')
