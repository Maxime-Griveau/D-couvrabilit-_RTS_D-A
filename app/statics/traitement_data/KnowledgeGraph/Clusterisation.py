import matplotlib
import pandas as pd
import requests
from tqdm import tqdm
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import numpy as np
from ...utils.tokenisation import tokenisation







# Nombre de lignes à afficher
rows = 500

base_url = "http://localhost:8983/solr/rtsarch/query"

# Test sur une seule année
datedebut = 2023
datefin = 2023

# Dictionnaire pour stocker les GUID et les entités associées
data_list = []

params = {
    'q': f'CategorieAsset:Programme',
    'wt': 'json',
    'rows': f'{rows}',
    'fl': "ContenuDocument, Guid",  # Champs à retourner
    'fq': f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
}
response = requests.get(base_url, params=params, verify=False)

if response.status_code == 200:
    data = response.json()
    for doc in data.get("response", {}).get("docs", []):
        contenu = tokenisation(doc.get("ContenuDocument", []))
        guid = doc.get("Guid", None)
        if guid and contenu:  # Assurez-vous que le GUID et le contenu ne sont pas None ou vides
            data_list.append((contenu, guid))
else:
    print(f"Erreur lors de la requête : {response.status_code}")

# Supprimer les listes vides et imbriquées entre elles 
data = []
guids = []

for contenu, guid in data_list:
    if contenu:  # Vérifiez que le contenu n'est pas vide
        
        for list in contenu:
            if list:
                data.append(list)
                guids.append(guid)

# Récupérer les mots 
cleaned_docs = [' '.join(doc) for doc in data]

# Vectorisation 
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(cleaned_docs)

print(X.toarray())  # Liste de vecteurs 

def plot_elbow_method(X):
    distortions = []
    K = range(1, 10)
    for k in K:
        kmeans = KMeans(n_clusters=k, random_state=0)
        kmeans.fit(X)
        distortions.append(kmeans.inertia_)
    
    plt.figure(figsize=(8, 4))
    plt.plot(K, distortions, 'bx-')
    plt.xlabel('k')
    plt.ylabel('Distortion')
    plt.title('The Elbow Method showing the optimal k')
    plt.show()

plot_elbow_method(X)

# Appliquer K-Means avec le nombre optimal de clusters
num_clusters = 6  # Ajuster le nombre de clusters si nécessaire

kmeans = KMeans(n_clusters=num_clusters, random_state=0)
kmeans.fit(X)

# Obtenir les labels des clusters
labels = kmeans.labels_

# Réduction de la dimensionnalité pour la visualisation
pca = PCA(n_components=2)
scatter_plot_points = pca.fit_transform(X.toarray())

colors = ['r', 'b', 'c', 'y', 'm', 'g']
x_axis = scatter_plot_points[:, 0]
y_axis = scatter_plot_points[:, 1]

plt.figure(figsize=(10, 6))
plt.scatter(x_axis, y_axis, c=[colors[label] for label in labels])
plt.title("K-means clustering des documents")
plt.xlabel("PCA 1")
plt.ylabel("PCA 2")
plt.show()

# Vérifiez que les longueurs de `cleaned_docs` et `guids` sont les mêmes avant de créer le DataFrame
assert len(cleaned_docs) == len(guids), "Les longueurs de cleaned_docs et guids ne correspondent pas."

# Créer un DataFrame avec les documents, leurs GUID et leurs clusters
df_clusters = pd.DataFrame({'Document': cleaned_docs, 'Guid': guids, 'Cluster': labels})

# Exporter les résultats dans un fichier Excel
df_clusters.to_excel('app/statics/datas/out/clusterisation/cluster_results.xlsx', index=False)

# Afficher les documents pour chaque cluster
for cluster in range(num_clusters):
    print(f"Cluster {cluster}:")
    cluster_docs = df_clusters[df_clusters['Cluster'] == cluster]
    if not cluster_docs.empty:  # Vérifier si le cluster contient des documents
        for _, row in cluster_docs.head(5).iterrows():  # Afficher les 5 premiers documents pour chaque cluster
            print(f" - GUID: {row['Guid']}, Document: {row['Document']}")
    else:
        print(f" - Aucun document dans ce cluster")