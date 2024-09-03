import pandas as pd
import requests
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from ...utils.tokenisation import tokenisation_et_lemmatisation
from tqdm import tqdm
import requests

### 1. Import des données

# Dates de début et de fin pour le filtre de date
datedebut = '2010'
datefin = '2023'

url = "http://localhost:8983/solr/rtsarch/query"

# Paramètres de la requête Solr
params = {
    'q': '*:*',
    'indent': 'true',
    'fl': "DureeMediaSec, ContenuDocument, Titre, Resume,ThematiquesMAT,ThematiquesGEO,ThematiquesPP, ThematiquesPM, Guid, Collection  ",  # Utilisation de guillemets doubles pour le champ
    'fq': [
        f'DatePublication:[{datedebut}-01-01T00:00:00Z TO {datefin}-12-31T23:59:59Z]',
        'DureeMediaSec:[30 TO *]',
        'Achat:"Non"',
        '-Collection:"News"',
        '-Collection:"AFPTV"'
          
    ],
    'rows': '1000',
    'wt': 'json'
}


response = requests.get(url, params=params, verify=False)
data = response.json()
print(f'Nombre de réponses : {data["response"]["numFound"]}')
data_docs = data["response"]["docs"]
data_list = []

for data_doc in tqdm(data_docs):

    titre = data_doc.get('Titre', '')
    collection = data_doc.get('Collection', '')
    contenu_document = data_doc.get('ContenuDocument', '')
    resume = data_doc.get('Resume', '')
    duree_secs = data_doc.get('DureeMediaSec', 0)
    MAT = data_doc.get('ThematiquesMAT', [])
    GEO = data_doc.get('ThematiquesGEO', [])
    PP = data_doc.get('ThematiquesPP', [])
    PM = data_doc.get('ThematiquesPM', [])
    GUID = data_doc.get('Guid', '')
    
    # Convertir les listes en valeurs séparées par des virgules pour les thésaurus
    MAT_str = ', '.join(MAT) if MAT else ''
    GEO_str = ', '.join(GEO) if GEO else ''
    PP_str = ', '.join(PP) if PP else ''
    PM_str = ', '.join(PM) if PM else ''
    
    data_list.append({
        "Titre": titre,
        "Collection": collection,
        "SpeechToText": contenu_document,
        "DureeSecs": duree_secs,
        "Resume": resume,
        "MAT": MAT_str,
        "GEO": GEO_str,
        "PP": PP_str,
        "PM": PM_str,
        "GUID":GUID
    })

df = pd.DataFrame(data_list)

### 2. Nettoyage des données 
def clean_text(text, type):
    
    if isinstance(text, list):
        text = ' '.join(text)
    if text is None:
        return pd.NA
    text = str(text)
    
    if type == "STT":
        # Supprimer les horodatages
        text = re.sub(r"[0-9]{2}:[0-9]{2}:[0-9]{2}", "", text)
        # Supprimer les espaces superflus
        text = re.sub(r'\s+', ' ', text)
        # Supprimer les informations au début des transcriptions
        text = re.sub(r'UMID\s*:\s*[A-Z0-9]+\s*Date\sde\stranscription\s*:\s*\d{2}-[A-Z]{3}-\d{2}\s*Nom\sdu\smodèle\s*:\s*\w*-\w+', "", text)
        text = re.sub(r'Locuteur .{3,6} \(.*\) \[[0-9]{1,3}%\]', "", text)
        text = re.sub(r'SOUS-TITRAGE [A-Z]* [A-Z]* [0-9]{4} [A-Z]* [0-9]* .*titrage.ch', "", text)
        
        #Supprimer les horodatages des transcriptions
        text = re.sub(r':[0-9]{1,2}', "", text)
         
        # Supprimer les caractères d'échappement
        text = re.sub(r'[\r\n]', ' ', text)
        # Supprimer le contenu entre crochets {}
        text = re.sub(r'\{.*?\}', '', text)
    
    if type == "Resume":
        # Supprimer les dates (faussent le clustering)
        text = re.sub(r"[0-9]{4,8}", "", text)
        text = re.sub(r"[0-9]{1,2}.[0-9]{1,2}.[0-9]{1,2}", "", text)
    if type == "Titre":
        #Supprimer les dates 
        text = re.sub(r"[0-9]{1,2}.[0-9]{1,2}.[0-9]{1,2}", "", text)
        text = re.sub(r"[0-9]{4,8}", "", text)
        
    # Supprimer les espaces en début et fin de chaîne
    text = text.strip()
    return pd.NA if text == "" else text

# Appliquer la fonction de nettoyage sur les colonnes appropriées
df['SpeechToText'] = df['SpeechToText'].apply(lambda x: clean_text(x, "STT"))
df['Resume'] = df['Resume'].apply(lambda x: clean_text(x, "Resume"))
df['Titre'] = df['Titre'].apply(lambda x: clean_text(x, "Titre"))


# Suppression des lignes où le STT, le Titre ou la collection sont absents
# Suppression des lignes avec des valeurs NaN
df.dropna(subset=['SpeechToText', 'Titre', 'Collection'], inplace=True)

# Suppression des lignes avec des titres et des collections vides ou uniquement des espaces
df = df[df['Titre'].str.strip() != '']
df = df[df['Collection'].str.strip() != '']

# Extraction de la première valeur de chaque liste de durées
df['DureeSecs'] = df['DureeSecs'].apply(lambda x: x[0] if isinstance(x, list) and x else x)

# Vérification des valeurs manquantes dans les autres colonnes et imputation
df = df.fillna({
    'Resume': 'No Resume',
    'MAT': 'No MAT',
    'GEO': 'No GEO',
    'PP': 'No PP',
    'PM': 'No PM'
})

## 3. Tokenisation et lemmatisation (fonction utilitaire importée)

#Variable pour stocker les stopwords (sous forme de regex)

#On supprime les ..., les caractères majuscules suivis d'apostrophe (C', L'...), les tirets et les chiffres seuls. 
regex_stopwords_STT = [r'\.\.\.', r"[A-Z]\'", r'\-', r'[0-9]{1}']


# Application de la fonction de tokenisation et de lemmatisation des textes
df['SpeechToText'] = df['SpeechToText'].apply(lambda x: tokenisation_et_lemmatisation(x, regex_stopwords=regex_stopwords_STT))
df['Resume'] = df['Resume'].apply(lambda x: tokenisation_et_lemmatisation(x))
df['Titre'] = df['Titre'].apply(lambda x: tokenisation_et_lemmatisation(x))
df['Collection'] = df['Collection'].apply(lambda x: tokenisation_et_lemmatisation(x))


#Remise à zéro de l'index
df.reset_index(drop=True, inplace=True)

## 4. Import des thésaurus en tant que liste de mots 
df_thesaurus = pd.read_json("app/statics/datas/out/tout_thesaurus.json")

thesaurus_list = ["GEO","MAT", "PP", "PM"]

# Créer des DataFrames pour chaque type de thésaurus
for Type in thesaurus_list:
    # Filtrer les lignes correspondant au type de thésaurus courant
    df_filtered = df_thesaurus[df_thesaurus["Type_Thesaurus"] == f'Thesaurus{Type}']
    # Extraire les mots de la colonne 'Entité'
    thesaurus_words = df_filtered['Entité'].tolist()
    # Créer une variable dynamique
    globals()[f'Thesaurus{Type}'] = thesaurus_words
    
    
print(ThesaurusGEO)
print(ThesaurusMAT)
print(ThesaurusPP)
print(ThesaurusPM)