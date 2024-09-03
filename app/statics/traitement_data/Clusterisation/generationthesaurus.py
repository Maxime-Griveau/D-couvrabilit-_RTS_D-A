import pandas as pd
import requests
from tqdm import tqdm
import nltk
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer, util
from transformers import T5Tokenizer, pipeline
import time
from datetime import datetime
from ...utils.tokenisation import clean_text

# Initialisation NLTK
nltk.download('punkt')

NB_ROWS = 5
TAILLE_MAX_RESUMES = 200
TAILLE_MIN_RESUMES = 100
TAILLE_MAX_INPUT_RESUMES = 500 #512 = limite pour faire en un seul batch ?
TOKENS_ANALYSER = 152 # 300 = limite ?  Tokens donnés au modèle pour générer les résumés 
DATE_DEBUT = '2012'
DATE_FIN = '2012'
MODEL_NAME = "t5-base-fr-sum-cnndm"


def truncate_to_tokens(text, num_tokens):
    tokens = word_tokenize(text)
    truncated_tokens = tokens[:num_tokens]
    return ' '.join(truncated_tokens)

def chunk_text(text, max_chunk_length):
    chunks = []
    for i in range(0, len(text), max_chunk_length):
        chunks.append(text[i:i + max_chunk_length])
    return chunks

def generate_summary(text_chunks, summarizer):
    summaries = []
    start_time = time.time()
    for chunk in tqdm(text_chunks, desc="Génération des résumés"): #On n'utilise pas le dernier chunk, de trop petite taille pour être utile.
        summary = summarizer(chunk)[0]['summary_text']
        summaries.append(summary)
    end_time = time.time()
    summary_time = end_time - start_time
    return ' '.join(summaries), summary_time

def calculate_similarity(text_embedding, thesaurus_embeddings, thesaurus_labels):
    similarities = util.cos_sim(text_embedding, thesaurus_embeddings)
    top_3_indices = similarities[0].argsort(descending=True)[:3]
    top_3_labels = []
    top_3_scores = []
    for idx in top_3_indices:
        top_3_labels.append(thesaurus_labels[idx])
        top_3_scores.append(similarities[0][idx].item())
    return top_3_labels, top_3_scores

# Charger les données depuis Solr
def load_data_from_solr(url, params):
    response = requests.get(url, params=params, verify=False)
    data = response.json()
    print(f'Nombre de réponses : {data["response"]["numFound"]}')
    data_docs = data["response"]["docs"]
    data_list = []
    for data_doc in tqdm(data_docs):
        contenu_document = data_doc.get('ContenuDocument', '')
        data_list.append({"SpeechToText": contenu_document})
    return pd.DataFrame(data_list)

def main():
    # Chargement des données Solr
    url = "http://localhost:8983/solr/rtsarch/query"
    params = {
        'q': 'CodeCollection:TEMPR',
        'indent': 'true',
        'fl': "DureeMediaSec, ContenuDocument, Titre, Resume,ThematiquesMAT,ThematiquesGEO,ThematiquesPP, ThematiquesPM, Guid, Collection  ",
        'fq': [
            f'DatePublication:[{DATE_DEBUT}-01-01T00:00:00Z TO {DATE_FIN}-12-31T23:59:59Z]',
            'DureeMediaSec:[30 TO *]',
            'Achat:"Non"',
            '-Collection:"News"',
            '-Collection:"AFPTV"'
        ],
        'rows': f'{NB_ROWS}',
        'wt': 'json'
    }
    
    df = load_data_from_solr(url, params)
    
    # Nettoyage des données
    df['SpeechToText'] = df['SpeechToText'].apply(lambda x: clean_text(x))
    df = df.dropna(subset=["SpeechToText"])
    
    print(df.head(15))
    
    # Tokenizer et Summarizer
    tokenizer = T5Tokenizer.from_pretrained("plguillou/t5-base-fr-sum-cnndm")
    summarizer = pipeline("summarization", model="plguillou/t5-base-fr-sum-cnndm",
                          max_length=TAILLE_MAX_RESUMES, min_length=TAILLE_MIN_RESUMES)
    
    # Modèle de transformation de phrases en vecteurs
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    
    # Encodage des étiquettes du thesaurus
    df_thesaurus = pd.read_json("app/statics/datas/out/tout_thesaurus.json")
    thesaurus_labels = df_thesaurus[df_thesaurus["Type_Thesaurus"] == 'ThesaurusMAT']['Entité'].tolist()
    thesaurus_embeddings = model.encode(thesaurus_labels)
    
    # Génération des résumés et calcul des similarités
    results = []
    summary_times = []
    start_time = time.time()

    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Nombre de résumés chargés"):
        text = row['SpeechToText']
        truncated_text = truncate_to_tokens(text, TOKENS_ANALYSER)
        print(truncated_text)
        text_chunks = chunk_text(truncated_text, TAILLE_MAX_INPUT_RESUMES)
        summary, summary_time = generate_summary(text_chunks, summarizer)
        
        # Calcul de similarité
        to_classify = summary
        text_embedding = model.encode(to_classify)
        top_3_labels, top_3_scores = calculate_similarity(text_embedding, thesaurus_embeddings, thesaurus_labels)
        
        # Filtrer les résultats avec un score inférieur à 0.5
        filtered_top_labels = []
        filtered_top_scores = []
        for i in range(3):
            if top_3_scores[i] < 0.5:
                filtered_top_labels.append("PAS D'ENTITÉ TROUVÉE")
                filtered_top_scores.append(None)
            else:
                filtered_top_labels.append(top_3_labels[i])
                filtered_top_scores.append(top_3_scores[i])
        
        # Construire une entrée de résultat unique
        result_entry = {
            # 'SpeechToText': text,
            'Summary': summary,
            'Top_Label_1': filtered_top_labels[0], 'Score_1': filtered_top_scores[0],
            'Top_Label_2': filtered_top_labels[1], 'Score_2': filtered_top_scores[1],
            'Top_Label_3': filtered_top_labels[2], 'Score_3': filtered_top_scores[2],
            'TEMPS D\'EXÉCUTION': summary_time
        }
        
        results.append(result_entry)
        summary_times.append(summary_time)

    # Création du DataFrame à partir de la liste de résultats
    df_results = pd.DataFrame(results)

    # Calcul du temps total d'exécution
    end_time = time.time()
    total_time = end_time - start_time
    df_results["TEMPS D'EXÉCUTION TOTALE"] = total_time


    # Enregistrement des résultats dans un fichier CSV
    current_date = datetime.now().strftime("%d-%m-%Y_%Hh%M-%Ssecs")
    output_file = f"app/statics/datas/out/clusterisation/classification_results_{MODEL_NAME}_{current_date}.csv"
    df_results.to_csv(output_file, index=False)

    print("Résultats enregistrés dans", output_file)
    
    
main()