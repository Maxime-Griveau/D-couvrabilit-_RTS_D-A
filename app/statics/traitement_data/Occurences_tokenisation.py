import csv
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import json



def tokenisation(liste, mots_reference, language='french'):
    """
    Tokenise une liste de textes et filtre les mots qui sont présents dans une liste de mots de référence.

    Parameters
    ----------
    liste : list
        Liste de textes à tokeniser.

    mots_reference : list
        Liste de mots de référence à filtrer.

    language : str, optional
        Langue utilisée pour la tokenisation et la liste des mots vides (stop words).
        Par défaut, la langue est le français ('french').

    Returns
    -------
    list
        Liste de listes de tokens filtrés pour chaque texte de la liste d'entrée.
    """
    resultats = []
    stop_words = set(stopwords.words(language))
    mots_reference_set = set(mot.lower() for mot in mots_reference)

    for texte in liste:
        tokens = word_tokenize(texte, language=language)
        tokens_filtres = [word.lower() for word in tokens if word.isalpha() and word.lower() not in stop_words and word.lower() in mots_reference_set]
        resultats.append(tokens_filtres)
    return resultats


def aplatir(liste_de_listes):
    """
    Aplatit une liste de listes en une seule liste.

    Parameters
    ----------
    liste_de_listes : list
        Liste de listes à aplatir.

    Returns
    -------
    list
        Liste résultante après l'aplatissement.
    """
    return [element for sous_liste in liste_de_listes for element in sous_liste]

def occurrences(liste_tokenisee, nombre_occurences):
    """
    Compte le nombre d'occurrences de chaque mot dans une liste tokenisée et retourne les mots avec un nombre d'occurrences supérieur à un seuil donné.

    Parameters
    ----------
    liste_tokenisee : list
        Liste de tokens à analyser.

    nombre_occurences : int
        Nombre minimum d'occurrences requis pour qu'un mot soit inclus dans les résultats.

    Returns
    -------
    list
        Liste des tuples (mot, nombre d'occurrences) pour les mots ayant un nombre d'occurrences supérieur à `nombre_occurences`.
    """
    compteur = {}
    for mot in liste_tokenisee:
        compteur[mot] = compteur.get(mot, 0) + 1
    return sorted((mot, count) for mot, count in compteur.items() if count > nombre_occurences)



