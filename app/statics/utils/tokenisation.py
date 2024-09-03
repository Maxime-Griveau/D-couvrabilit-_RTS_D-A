import nltk
from nltk.corpus import stopwords
import string
import spacy
import re
import pandas as pd 

# Assurez-vous d'avoir téléchargé les ressources nécessaires
nltk.download('punkt')
nltk.download('stopwords')

# Charger le modèle français de spaCy pour la lemmatisation
nlp = spacy.load('fr_core_news_sm')


def tokenisation_et_lemmatisation(text, regex_stopwords=None):
    """Tokenise et lemmatise un texte donné selon une liste de stopwords 

    Args:
        text (texte): texte à tokeniser et lematiser 
        regex_stopwords (regex): Stopwords sous forme de regex. Defaults to None.

    Returns:
        _type_: _description_
    """
    # Tokenisation des phrases
    sentences = nltk.sent_tokenize(text, language='french')
    
    # Tokenisation des mots et suppression de la ponctuation et des stopwords
    stop_words = set(stopwords.words('french'))
    tokens = []
    
    for sentence in sentences:
        words = nltk.word_tokenize(sentence, language='french')
        words = [word for word in words if word.lower() not in stop_words and word not in string.punctuation and word != '``' and word != "''"]
        tokens.extend(words)
    
    # Supprimer les mots correspondant aux regex
    if regex_stopwords:
        tokens = [word for word in tokens if not any(re.search(pattern, word) for pattern in regex_stopwords)]
    
    # Lemmatisation
    doc = nlp(' '.join(tokens))
    lemmas = [token.lemma_ for token in doc if token.lemma_ not in stop_words and token.lemma_ not in string.punctuation]
    
    return lemmas

def clean_text(text):
    if isinstance(text, list):
        text = ' '.join(text)
    if text =="":
        return None
    
    text = str(text)

    text = re.sub(r"[0-9]{2}:[0-9]{2}:[0-9]{2}", "", text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'UMID\s*:\s*[A-Z0-9]+\s*Date\sde\stranscription\s*:\s*\d{2}-[A-Z]{3}-\d{2}\s*Nom\sdu\smodèle\s*:\s*\w*-\w+', "", text)
    text = re.sub(r'Locuteur\s*[a-zA-Z0-9]{3,6}\s*\(\s*[0-9]{0,2}:[0-9]{0,2}:[0-9]{0,2}\s*[<>]\s*[0-9]{0,2}:[0-9]{0,2}:[0-9]{0,2}\s*\)\s*\[\s*[0-9]{0,3}\s*%\s*\]\s*:', "", text)
    text = re.sub(r'SOUS-TITRAGE [A-Z]* [A-Z]* [0-9]{4} [A-Z]* [0-9]* .*titrage.ch', "", text)
    text = re.sub(r':[0-9]{0,2}', ' ', text)
    text = re.sub(r'[\r\n]', ' ', text)
    text = re.sub(r'-(?=[A-Z])', '', text)
    text = re.sub(r'\{.*?\}', '', text)
    text = re.sub(r"\.\.\.", "", text)
    text = re.sub(r'\s+([.,;?!:])', r'\1', text)
    text = re.sub(r'\s{2,8}', ' ', text)

    return text.strip()