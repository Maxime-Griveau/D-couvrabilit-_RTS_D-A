import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Polygon, MultiPolygon
import requests
import pandas as pd
import json
from concurrent.futures import ThreadPoolExecutor
from ..utils.escape_solr_special_chars import escape_solr_special_chars

# Ce script est à lancer de façon périodique (une fois par semaine ?) pour "regénérer les fichiers"

date_debut = 1954  # Date du début des archives 
date_fin = 2024  # Date de fin 

# Liste des layers à récupérer dans le fichier gdb
layers = ["TLM_KANTONSGEBIET", "TLM_BEZIRKSGEBIET", "TLM_HOHEITSGEBIET"]

# Noms des colonnes à garder pour chaque layer
colonnes_a_garder = {
    "TLM_KANTONSGEBIET": ["geometry", "KANTONSNUMMER", "NAME"],
    "TLM_BEZIRKSGEBIET": ["geometry", "NAME", "BEZIRKSNUMMER", "KANTONSNUMMER"],
    "TLM_HOHEITSGEBIET": ["geometry", "NAME", "BFS_NUMMER", "BEZIRKSNUMMER", "KANTONSNUMMER"]
}

# Traduction en français des noms de layer 
correspondance_noms = {
    "TLM_KANTONSGEBIET": "cantons",
    "TLM_BEZIRKSGEBIET": "districts",
    "TLM_HOHEITSGEBIET": "villes"
}

# Téléchargement et extraction du fichier gdb depuis https://ogd.swisstopo.admin.ch/ch.swisstopo.swissboundaries3d

url_gdb = "https://data.geo.admin.ch/ch.swisstopo.swissboundaries3d/swissboundaries3d_2024-01/swissboundaries3d_2024-01_2056_5728.gdb.zip"
response_gdb = requests.get(url_gdb)

with open("./app/statics/datas/in/suisse.gdb.zip", "wb") as f:
    f.write(response_gdb.content)

zip_file_path = "./app/statics/datas/in/suisse.gdb.zip"

# Import des numéros OFS et des noms français des communes pour jointure (depuis wikidata en SPARQL)
url = 'https://query.wikidata.org/sparql'
query = '''
SELECT ?VilleLabel ?numerosOFS
WHERE {
  ?Ville wdt:P31 wd:Q70208.
  ?Ville wdt:P771 ?numerosOFS
  . MINUS { ?Ville wdt:P31 wd:Q685309 } 
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr". }
}
'''
r = requests.get(url, params={'format': 'json', 'query': query})

if r.status_code == 200:
    datas = r.json()
    data_fields = datas["results"]["bindings"]
    data_list = []
    for data in data_fields:
            BFS_NUMMER = data["numerosOFS"]["value"]
            ville = data["VilleLabel"]["value"]
            data_list.append({"ville": ville, "BFS_NUMMER": BFS_NUMMER})
    df_villefr = pd.DataFrame(data_list)
    df_villefr['BFS_NUMMER'] = df_villefr['BFS_NUMMER'].astype(int)
else:
    print("Erreur de récupération des données de Wikidata concernant les communes (traduction des noms de communes en français), ça arrive souvent : relancez la requête")

# Téléchargement des numéros et noms des cantons en français pour jointure (depuis l'OFS)

url_cantons = "https://www.atlas.bfs.admin.ch/core/projects/13.40/xshared/xlsx/134_132.xlsx"
cantons = requests.get(url_cantons)
if cantons.status_code == 200:
    with open("./app/statics/datas/in/cantons.xlsx", "wb") as f:
        f.write(cantons.content)
    df_cantonsfr = pd.read_excel("./app/statics/datas/in/cantons.xlsx")
    df_cantonsfr.rename(columns={"Les 26 cantons de la Suisse": "KANTONSNUMMER", "Unnamed: 1": "Nom"}, inplace=True)
    df_cantonsfr.drop(columns=134, axis=1, inplace=True)
    df_cantonsfr.drop(df_cantonsfr.index[0:4], inplace=True)
    df_cantonsfr.reset_index(drop=True, inplace=True)
    df_cantonsfr.drop(df_cantonsfr.index[26:], inplace=True)
    df_cantonsfr.replace(to_replace="Appenzell Rh.-Int.", value="Appenzell Rhodes-Intérieures", inplace=True)
    df_cantonsfr.replace(to_replace="Appenzell Rh.-Ext.", value="Appenzell Rhodes-Extérieures", inplace=True)
    
    # df_cantonsfr.replace(to_replace="Schwyz", value="Schwytz", inplace=True)
    df_cantonsfr['KANTONSNUMMER'] = df_cantonsfr['KANTONSNUMMER'].astype(int)  # Assurez-vous que le type est correct
else:
    print("Erreur de récupération des données de l'OFS concernant les cantons (traduction des noms de cantons en français)")

# Liste créée pour vérification ultérieure 
noms_cantons = df_cantonsfr['Nom'].tolist()

# Création d'un transformateur pour convertir les coordonnées MN-95 en format lat/long
transformer = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
def convertMN95versLatLong(multipolygon):
    """Converti les coordonnées au format suisse (EPSG:2056) vers le format lat/long (EPSG:4326) pour utilisation dans leaflet

    Args:
        multipolygon (list): liste de vecteurs géographiques comprenant les coordonnées (lat long et hauteurs [qui ne sont pas gardées])
        always_xy = True (indique qu'on ne garde que les coordonnées x et y)
    Returns: Les coordonnées au format lat/long 
    """
    nouvelles_geometries = []
    for polygon in multipolygon.geoms:
        x_coords, y_coords = polygon.exterior.coords.xy
        points_transformes = transformer.itransform(zip(x_coords, y_coords))
        points_transformes = [(x, y) for x, y in points_transformes]
        exterior = Polygon(points_transformes)
        nouvelles_geometries.append(Polygon(exterior))
    return MultiPolygon(nouvelles_geometries)

def CompterResultats(df, datedebut="1800", datefin="5000", fields=['ResumeSequence', 'Titre', 'ContenuDocument', 'MetadonneesAutomatiques', 'ThesaurusGEO']):
    """Compter résultats : prends comme argument un géodataframe et les paramètres de la requête SolR pour générer un json où sont indiqués les résultats des requêtes pour chaque nom de territoire

    Args:
        gdf (object): geodataframe contenant une colonne "NAME"
        datedebut (str, optional): Date du début de la requête. Par défaut à "1800".
        datefin (str, optional): Date de fin de la requête. Par défaut, les champs : ['ResumeSequence', 'Titre', 'ContenuDocument', 'MetadonneesAutomatiques', 'ThematiquesGEO'] sont pris en compte.

    Returns:
        Dataframe : Dataframe avec une colonne "Nombre Résultats" totalisant les résultats des requêtes 
    """
    data_list = []
    base_url = "http://localhost:8983/solr/rtsarch/query"

    def fetch_results(name):
        if pd.isnull(name):
            return 0
        GEO = escape_solr_special_chars(str(name))
        field_queries = [f'{field}:"{GEO}"' for field in fields]
        query_string = ' OR '.join(field_queries)
        params = {
            'q': f'({query_string})',
            'wt': 'json',
            'rows': '1',
            'fl': 'idSupport',
            'fq': f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]'
        }
        response = requests.get(base_url, params=params, verify=False)
        data = response.json()
        return data['response']['numFound']
    #un worker par coeur logique du processeur 
    with ThreadPoolExecutor(max_workers=8) as executor:
        data_list = list(executor.map(fetch_results, df["NAME"]))

    df["NombreResultats"] = data_list
    return df 

# Ajouter la propriété render_order en fonction des critères spécifiés
def ajouter_render_order(gdf):
    gdf["render_order"] = gdf["NAME"].apply(lambda x: 1 if x in ["Appenzell Rhodes-Intérieures", "Appenzell Rhodes-Extérieures", "Fribourg"] else 2)
    return gdf

# Pour chaque layer (couche)
for layer in layers:
    nom_fr = correspondance_noms[layer]  # Traduction en français des noms 
    gdf_temp = gpd.read_file(f"zip://{zip_file_path}", layer=layer)  # Lecture du fichier requêté en zip 
    gdf_reduit = gdf_temp[colonnes_a_garder[layer]]  # On ne garde que les colonnes utiles 
    gdf_reduit.loc[:, 'geometry'] = gdf_reduit['geometry'].apply(convertMN95versLatLong)  # Conversion des coordonnées 
    gdf_reduit = gpd.GeoDataFrame(gdf_reduit, geometry='geometry', crs="EPSG:4326")  # remise au format geopandas pour export 
    
    if 'BFS_NUMMER' in gdf_reduit.columns:  # Pour les communes ayant un numéro OFS 
        gdf_reduit['BFS_NUMMER'] = gdf_reduit['BFS_NUMMER'].astype(int)  # Il est converti en int pour jointure 
        
    if layer == "TLM_KANTONSGEBIET":  # Pour les cantons 
        gdf_reduit['KANTONSNUMMER'] = gdf_reduit['KANTONSNUMMER'].astype(int)  # Le numéro du canton est converti en int   
        gdf_final = gdf_reduit.merge(df_cantonsfr, on="KANTONSNUMMER", how="left")  # Jointure gauche avec les noms français des cantons 
        gdf_final.drop(["NAME"], axis=1, inplace=True)
        gdf_final.rename(columns={'Nom': 'NAME'}, inplace=True)
        # Ajouter la propriété render_order pour les cantons (pour éviter les problèmes de superposition)
        gdf_final = ajouter_render_order(gdf_final)
    
    elif layer == "TLM_HOHEITSGEBIET": #Pour les villes
        gdf_final = gdf_reduit.merge(df_villefr, on="BFS_NUMMER", how="left")
        gdf_final.drop(["NAME"], axis=1, inplace=True)
        gdf_final.rename(columns={'ville': 'NAME'}, inplace=True)
        gdf_final['NAME'] = gdf_final['NAME'].apply(lambda x: f"{x}-ville" if x in noms_cantons else x)
    
    else:
        gdf_final = gdf_reduit

    

    output_file_path = f"./app/statics/datas/out/carte/{nom_fr}.geojson"
    gdf_final.to_file(output_file_path, driver='GeoJSON')
    df_name = gdf_final[['NAME']]
    print(f"Les données de la couche {layer} ont été converties et exportées en GEOJSON sous le nom de {nom_fr}.geojson")
    
    
    output_file_path_name = f"./app/statics/datas/out/{nom_fr}_name.csv"
    df_name.to_csv(output_file_path_name)
    print(f"Les noms des territoires pour la couche {layer} ont bien été exportés en csv sous le nom de {output_file_path_name}")

    
    #Ancienne logique de génération de deux fichiers par année avec et sans métadonnées. 
    #Plus utilisée depuis le quatre juin 2024  
    # Metadonnees = [True, False]

    # for annee in range(date_debut, date_fin+1): #Ajouter +1 à la date car la date finale n'est pas comprise dans l'intervale range() (pour éviter les erreurs)
    #     for bool in Metadonnees:
    #         if bool == True:
    #             print(f"Annee : {annee}, Booléen : {bool}")
    #             output_file_path = f"./app/statics/datas/out/carte/{nom_fr}_{annee}_Metadonnees.json"   
    #             with open(output_file_path, "w", encoding='utf-8') as output_file:
    #                 resultats = CompterResultats(df_final, datedebut=str(annee), datefin=str(annee))
    #                 resultats_dict = resultats.to_dict('records')
    #                 json.dump(resultats_dict, output_file, indent=4, ensure_ascii=False)
    #                 print(f"Les données de la couche {layer} pour l'année {annee} avec les métadonnées automatiques et le speech to text ont été exportées en JSON sous le nom de {nom_fr}_{annee}_Metadonnees.json")
    #         else:
    #             print(f"Annee : {annee}, Booléen : {bool}")
    #             output_file_path = f"./app/statics/datas/out/carte/{nom_fr}_{annee}_NoMetadonnees.json"   
    #             with open(output_file_path, "w", encoding='utf-8') as output_file:
    #                 resultats = CompterResultats(df_final, datedebut=str(annee), datefin=str(annee), fields = ['ResumeSequence', 'Titre', 'ThematiquesGEO'])
    #                 resultats_dict = resultats.to_dict('records')
    #                 json.dump(resultats_dict, output_file, indent=4, ensure_ascii=False)
    #                 print(f"Les données de la couche {layer} pour l'année {annee} SANS les métadonnées automatiques et le speech to text ont été exportées en JSON sous le nom de {nom_fr}_{annee}_NoMetadonnees.json")
