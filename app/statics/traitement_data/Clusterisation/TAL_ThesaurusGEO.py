import pandas as pd
import requests
from tqdm import tqdm
import nltk
from nltk.tokenize import word_tokenize
import re
import spacy
from spacy import displacy
from ...utils.tokenisation import tokenisation_et_lemmatisation, clean_text

nltk.download('punkt')


# Chargement du modèle SpaCy en français
nlp = spacy.load('fr_core_news_sm')

# Paramètres de la requête Solr
datedebut = 2022
datefin = 2022
rows = 30
url = "http://localhost:8983/solr/rtsarch/query"

params = {
    'q': '*:*',
    'indent': 'true',
    'fl': "DureeMediaSec, ContenuDocument, Titre, Resume,ThematiquesMAT,ThematiquesGEO,ThematiquesPP, ThematiquesPM, Guid, Collection",
    'fq': [
        f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
        'DureeMediaSec:[30 TO *]',
        'Achat:"Non"',
        '-Collection:"News"',
        '-Collection:"AFPTV"'
    ],
    'rows': f'{rows}',
    'wt': 'json'
}

response = requests.get(url, params=params, verify=False)
data = response.json()
print(f'Nombre de réponses : {data["response"]["numFound"]}')
data_docs = data["response"]["docs"]
data_list = []

for data_doc in tqdm(data_docs):
    contenu_document = data_doc.get('ContenuDocument', '')
    guid = data_doc.get('Guid', '')
    data_list.append({
        "SpeechToText": contenu_document,
        "Guid": guid
    })

df_stt = pd.DataFrame(data_list)


df_villes = pd.read_csv("app/statics/datas/out/villes_name.csv")

# Listes des villes problématiques
villes_problematiques = ['Au', 'Bulle', 'Vals', 'Port', 'Le Lieu', 'La Verrerie', 'Rue', 'Premier', 'Sâles', 'Court', 'Le Vaud', 'Champion', 'Alle', 'Les Bois', 'Crans', 'Roche', 'La Roche', 'Roches', 'Bassins', 'Les Enfers', 'Bière', 'Champagne', 'Granges', 'La Bourg', 'Chapelle', 'Bâche', 'Perles', 'Vallon', "L'Abbayes", 'Provence']


# Exclude problematic territories from the set of city names
villes_set = set(df_villes['NAME'].str.lower().tolist()) - set([x.lower() for x in villes_problematiques])

# Convert set to a single string separated by spaces
villes_text = ' '.join(villes_set)

# Initialize spaCy's French language model
nlp = spacy.blank('fr')

# Process the text with spaCy
doc = nlp(villes_text)

# Iterate over entities found by spaCy
for ent in doc.ents:
    print(ent.text, ent.label_)