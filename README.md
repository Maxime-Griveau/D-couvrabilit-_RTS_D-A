# Projet de visualisation des données du service Données & archives
(Fork du projet https://github.com/NatachaGrim/M2_Projet-JO/tree/main)
# Manuel de l'application

## Contributeurs
- [Maxime Griveau](https://github.com/Maxime-Griveau) ;




## Fonctionnalités
Notre application dispose des fonctionnalités suivantes :
- Visualisation sous forme de carte Suisse (avec les échellons administratifs) des contenus archivés avec possibilité de filtrage (par date, avec ou sans les métadonnées automatiques, par mot clé) et coloration en fonction des résultats les plus importants
- Visualisation sous forme de carte mondiale des News archivées par les documentalistes 
- Visualisation des Thésaurus Matière et Géographiques sous forme de digramme _sunburst_ (hiérarchisés)
- Visualisation des Codes contenus (identifiants classifiant les émissions) sous forme de _treemap_ (hiérarchisées)

  **/!\ Attention : les codes contenus ne concernent qu'un tiers des émissions télévisuelles, c'est bien la tendance générale qu'il faut regarder et non les valeurs chiffrées** 
- Découverte des liens entre deux à quatre termes de recherche sous forme de knowledge graph

### Quelques images : 

**Carte interractive**:

![image carte interactive](https://github.com/SRGSSR/DATAVIZ--DonneesArchives/blob/main/pictures/carteInterractive.png)

**Carte mondiale des News** :

![image carte mondiale des News](https://github.com/SRGSSR/DATAVIZ--DonneesArchives/blob/main/pictures/carteNews.png)

**Sunburst des thésaurus matières et géographie**

![image sunburst](https://github.com/SRGSSR/DATAVIZ--DonneesArchives/blob/main/pictures/sunburstGeo.png)

**Treemap interactive et hiérarchique des codes contenus**

![image treemap](https://github.com/SRGSSR/DATAVIZ--DonneesArchives/blob/main/pictures/treemap.png)


## Instructions : un premier lancement

### Prérequis : 
- Avoir accès à l'API solR de RTS archive (soit depuis le réseau interne de la SSR soit en créant un conteneur [cf. https://github.com/SRGSSR/look-devstack])
- Avoir un shell sous UNIX (Linux ou Apple)

### Étape 1 : installer Python
- Ouvrez votre terminal, collez-y la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
sudo apt install python3
```

### Étape 2 : cloner l'application
- Dans le terminal, collez la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
git clone https://github.com/SRGSSR/DATAVIZ--DonneesArchives
```

### Étape 3 : installer un environnement virtuel
- Dans le terminal, collez la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
cd Appli/BASE_app
```

- Puis collez-y la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :
(en supposant que virtualenv soit installé)
```shell
virtualenv env -p python3
```

### Étape 4 : saisir les variables
- Dans le terminal, collez la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
touch .env
```

- Ouvrez le fichier ```.env``` et copiez-collez-y ce bloc de code avec ```ctrl+v``` :

```shell
DEBUG=False
WTF_CSRF_ENABLE=True
SECRET_KEY=[à demander par mail à maxime.griveau@rts.ch]
```

- Enregistrez avec ```ctrl+s``` et fermez le fichier.

## Étape 6 : installer les dépendances
- Dans le terminal, collez la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
source env/bin/activate
```

- Collez ensuite la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
pip install -r requirements.txt
```

## Étape 7 : lancer l'application

- Dans le terminal, collez la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
python3 run.py
```

L'application devrait démarrer. Ouvrez ensuite votre navigateur web et saisissez le nom d'une route. Par exemple :

```shell
localhost:5000/accueil
```

Nos différentes routes sont consultables dans [ce dossier](BASE_app/app/routes).

## Étape 8 : quitter l'application
- Dans le terminal, maintenez la touche ```ctrl``` enfoncée et appuyez sur la touche ```c``` ;
- Collez-y ensuite la ligne suivante avec ```ctrl+maj+v``` et appuyez sur la touche ```Entrée``` :

```shell
deactivate
```

## Instructions : mémo

Pour lancer l'application :
```shell
cd cheminJusqu'auDossierBASE_app
```

```shell
source env/bin/activate
```

```shell
python run.py
```

Pour quitter l'application :
- Maintenir ```ctrl``` et appuyer sur ```c``` ;

```shell
deactivate
```
