import geopandas as gpd
from shapely.geometry import mapping
import json

# Liste des noms de couches
liste_layer = ["cantons", "districts", "villes"]

# Dictionnaire pour stocker les GeoDataFrames
gdfs = {}

# Boucle pour lire chaque fichier GeoJSON et stocker dans le dictionnaire
for layer in liste_layer:
    gdfs[layer] = gpd.read_file(f"app/statics/datas/out/carte/{layer}.geojson")

# Accès aux GeoDataFrames
gdf_cantons = gdfs["cantons"]
gdf_districts = gdfs["districts"]
gdf_villes = gdfs["villes"]

# Liste des cantons sans districts
cantons_sans_districts = [
    "Genève", "Neuchâtel", "Uri", "Obwald", "Nidwald",
    "Glaris", "Zoug", "Bâle-Ville", "Appenzell-Rhodes-Intérieures"
]

# Fusion des DataFrames en une structure hiérarchisée
features = []

for canton_num in gdf_cantons['KANTONSNUMMER'].unique():
    canton = gdf_cantons[gdf_cantons['KANTONSNUMMER'] == canton_num]
    canton_name = canton['NAME'].iloc[0]
    canton_geometry = canton['geometry'].iloc[0]
    districts = []

    if canton_name in cantons_sans_districts:
        villes = []
        for _, ville_row in gdf_villes[gdf_villes['KANTONSNUMMER'] == canton_num].iterrows():
            ville_name = ville_row['NAME']
            ville_geometry = ville_row.geometry
            villes.append({
                'type': 'Feature',
                'properties': {'name': ville_name, 'level': 2},
                'geometry': mapping(ville_geometry)
            })

        features.append({
            'type': 'Feature',
            'properties': {'name': canton_name, 'villes': villes, 'level': 1},
            'geometry': mapping(canton_geometry)
        })
    else:
        for district_num in gdf_districts[gdf_districts['KANTONSNUMMER'] == canton_num]['BEZIRKSNUMMER'].unique():
            district = gdf_districts[gdf_districts['BEZIRKSNUMMER'] == district_num]
            district_name = district['NAME'].iloc[0]
            district_geometry = district['geometry'].iloc[0]
            villes = []

            for _, ville_row in gdf_villes[gdf_villes['BEZIRKSNUMMER'] == district_num].iterrows():
                ville_name = ville_row['NAME']
                ville_geometry = ville_row['geometry']
                villes.append({
                    'type': 'Feature',
                    'properties': {'name': ville_name, 'level': 3},
                    'geometry': mapping(ville_geometry)
                })

            districts.append({
                'type': 'Feature',
                'properties': {'name': district_name, 'villes': villes, 'level': 2},
                'geometry': mapping(district_geometry)
            })

        features.append({
            'type': 'Feature',
            'properties': {'name': canton_name, 'districts': districts, 'level': 1},
            'geometry': mapping(canton_geometry)
        })

geojson_data = {
    'type': 'FeatureCollection',
    'features': features
}

# Sauvegarder le GeoJSON hiérarchisé
with open('app/statics/datas/out/carte/global_geojson_hierarchise.geojson', 'w') as f:
    json.dump(geojson_data, f, ensure_ascii=False, indent=2)

print("GeoJSON global hiérarchisé créé avec succès.")
