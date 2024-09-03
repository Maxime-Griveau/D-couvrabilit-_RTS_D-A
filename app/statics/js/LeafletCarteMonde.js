console.log("Script chargé !");

/* <============= Section 1 : Initialisation de la carte avec Leaflet ===============> */

// Initialisation de la carte avec Leaflet
var carte = L.map('map', {
    wheelPxPerZoomLevel: 150,  // Réduction du zoom par mouvement de la molette
    zoomSnap: 0.5,             // Ajoute des niveaux de zoom intermédiaires 
    zoomDelta: 1               // Contrôle la valeur du zoom quand l'utilisateur clique sur + ou - sur la carte 
}).setView([46.8155135, 8.224471999999992], 2.7);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 8,
    minZoom: 2,
    attribution: '© OpenStreetMap'
}).addTo(carte);




var controleRecherche = {};
var minMax = {};
var caseCochee = false;
var nomPropriete = null;
var nomPays = null;
var valeursSlider = [1992, 2100];
var geojsonLayer = null;
var dataRecherche = "";
var exporter = false;
var etiquettes = [];
var seulThesaurus = false;

var divResultats = document.getElementById('resultats');
var chargement = document.getElementById("chargementPage");

// Initialisation
cacherChargement();
initialiserSlider();
initEcouteursEvenements();
initialiserLegendeCarte();
initialiserBoutonReset();
chargerGeoJSONLayer(geojsonUrl, "NAME", carte);

/**
 * Fonction pour charger le layer GeoJSON sur la carte.
 *
 * @param {string} geojson - URL du fichier GeoJSON contenant les données à afficher.
 * @param {string} nomPropriete - Nom de la propriété à utiliser pour la recherche.
 * @param {Object} carte - Objet représentant la carte Leaflet.
 */
function chargerGeoJSONLayer(geojson, nomPropriete, carte) {
    fetch(geojson)
        .then(response => response.json())
        .then(data => {
            // Créer le layer GeoJSON et l'ajouter à la carte
            geojsonLayer = L.geoJSON(data, {
                style: function (feature) {
                    return { weight: 1 };
                }
            }).addTo(carte);

            // Créer le contrôle de recherche pour le layer
            controleRecherche = barreRecherche(carte, geojsonLayer, nomPropriete);

            // Ajouter le contrôle de recherche à la carte
            carte.addControl(controleRecherche);

            // Optionnel : Gérer d'autres actions ou états de votre application
            document.getElementById('map').classList.remove('reduced');
            divResultats.classList.add('hidden');
            divResultats.classList.remove('visible');



            envoyerDonneesFlask();
        })
        .catch(error => {
            console.error('Erreur lors du chargement du fichier GeoJSON:', error);
        });
}


/**
 * Fonction pour gérer l'interactivité des layers.
 *
 * @param {Event} e - Événement Leaflet.
 */
function interactivite(e) {
    var couche = e.target;
    if (couche.feature && couche.feature.properties) {
        nomPays = couche.feature.properties.NAME;
  

    }
    envoyerDonneesFlask();
}


/* <============= Section 2 : Fonctions Utilitaires ===============> */

/**
 * Fonction pour cacher l'élément de chargement et activer les éléments interactifs.
 */
function cacherChargement() {
    document.getElementById('chargementPage').style.display = 'none';
    let elementsInteractifs = document.querySelectorAll('button, input, select, textarea, a');
    elementsInteractifs.forEach(element => {
        element.removeAttribute('disabled');
    });
}

/**
 * Fonction pour afficher l'élément de chargement et désactiver les éléments interactifs.
 */
function afficherChargement() {
    document.getElementById('chargementPage').style.display = 'flex';
    let elementsInteractifs = document.querySelectorAll('button, input, select, textarea, a');
    elementsInteractifs.forEach(element => {
        element.setAttribute('disabled', 'true');
    });
}

/* <============= Section 2 : Fonctions Utilitaires ===============> */

/**
 * Fonction pour créer une barre de recherche pour un layer donné.
 *
 * @param {Object} carte - Objet représentant la carte Leaflet.
 * @param {Object} layer - Layer sur lequel appliquer la recherche.
 * @param {string} nomPropriete - Propriété à utiliser pour la recherche.
 * @returns {Object} - Contrôle de recherche.
 */
function barreRecherche(carte, layer, nomPropriete) {
    var controleRecherche = new L.Control.Search({
        layer: layer,
        propertyName: nomPropriete,
        marker: false,
        moveToLocation: function (latlng, title, carte) {
            carte.setView(latlng, 12);
        }
    });

    controleRecherche.on('search:locationfound', function (e) {
        e.layer.openPopup();
    });

    controleRecherche.on('search:expanded', function() {
        try {
            controleRecherche._fillRecordsCache();
        } catch (error) {
            console.error('Erreur lors de la mise à jour du cache de recherche:', error);
            // Ajouter un log pour les entités problématiques
            if (!layer.feature || !layer.feature.properties) {
                console.warn('Layer with missing properties:', layer);
            }
        }
    });

    return controleRecherche;
}

/**
 * Fonction pour mettre à jour les données de recherche.
 *
 * @param {Array} data - Données à mettre à jour.
 * @param {Object} minMax - Valeurs min et max pour l'échelle de couleurs.
 * @param {Object} layer - Le layer à mettre à jour.
 */
function miseAJourDataRecherche(data, minMax, layer) {
   

    const donneesGeojson = {
        type: "FeatureCollection",
        features: data.map(item => ({
            type: "Feature",
            properties: {
                NAME: item.NAME,
                NombreResultats: item.NombreResultats
            },
            geometry: item.geometry // Assurez-vous d'inclure la géométrie si nécessaire
        }))
    };

    // Vérifier que layer est défini
    if (layer) {
    

        // Si layer possède des sous-couches, parcourons-les
        const layers = layer._layers;
        if (layers) {


            // Parcourir les sous-couches
            for (const key in layers) {
                if (layers.hasOwnProperty(key)) {
                    const subLayer = layers[key];
                    if (subLayer.feature && subLayer.feature.properties) {
                   

                        const feature = donneesGeojson.features.find(f => f.properties.NAME === subLayer.feature.properties.NAME);
                        if (feature) {
                            const value = feature.properties.NombreResultats;
                
                            subLayer.setStyle({
                                fillColor: CouleursResultats(value, minMax),
                                fillOpacity: 0.5,
                                color: "Red",
                                weight: subLayer.options.weight
                            });
                        } else {
                            console.log("Aucune feature correspondante trouvée dans donneesGeojson");
                        }
                    } else {
                        console.log("Sous-couche sans propriétés de feature valides:", subLayer.feature);
                    }
                }
            }
        } else {
            console.log("Layer ne contient pas de sous-couches");
        }
    } else {
        console.log("Layer n'est pas défini");
    }

    cacherChargement();
}


/**
 * Fonction pour déterminer la couleur des résultats en fonction de la valeur.
 *
 * @param {number} value - Valeur à évaluer.
 * @param {Object} minMax - Valeurs min et max pour l'échelle.
 * @returns {string} - Couleur correspondante.
 */
function CouleursResultats(value, minMax) {

    if (value === 0) {
        return '#FFFFFF'; // Blanc
    }

    const { min, max } = minMax;
    const range = max - min;
    const step = range / 7;
    return value > min + 6 * step ? '#800026' :
        value > min + 5 * step ? '#BD0026' :
            value > min + 4 * step ? '#E31A1C' :
                value > min + 3 * step ? '#FC4E2A' :
                    value > min + 2 * step ? '#FD8D3C' :
                        value > min + step ? '#FEB24C' :
                            '#FFEDA0';
}

/* <============= Section 3 : Initialisation des Écouteurs d'Événements ===============> */

/**
 * Fonction pour initialiser les écouteurs d'événements.
 */
function initEcouteursEvenements() {
    document.getElementById('export').addEventListener('click', function (event) {
        event.preventDefault();
        exporter = true;
        envoyerDonneesFlask();
    });

    document.getElementById('applyYearChange').addEventListener('click', function () {
        envoyerDonneesFlask();
    });

    document.getElementById('rechercheForm').addEventListener('submit', function (event) {
        event.preventDefault();
        dataRecherche = document.getElementById('entite1').value;
        envoyerDonneesFlask();
    });
    
}

/* <============= Section 4 : Initialisation du Slider ===============> */

/**
 * Fonction pour initialiser le slider.
 */
function initialiserSlider() {
    var slider = document.getElementById('slider');

    noUiSlider.create(slider, {
        connect: true,
        range: {
            'min': 1992,
            'max': 2024,
        },
        start: [1992, 2024],
        step: 1,
        tooltips: [true, true],
        format: {
            to: function (value) {
                return Math.round(value);
            },
            from: function (value) {
                return Number(value);
            },
        }
    });

    slider.noUiSlider.on('update', function (values, handle) {
        valeursSlider = values.map(value => parseInt(value));
    });
}


/* <============= Section 6 : Initialisation du Bouton de Réinitialisation ===============> */

/**
 * Fonction pour initialiser le bouton de réinitialisation.
 */
function initialiserBoutonReset() {
    document.getElementById('resetResults').addEventListener('click', function () {
        window.location.reload();
    });
}

/* <============= Section 7 : Initialisation de la Légende de la Carte ===============> */

/**
 * Fonction pour initialiser la légende de la carte.
 */
function initialiserLegendeCarte() {
    var legende = L.control({ position: "bottomleft" });

    legende.onAdd = function (carte) {
        var div = L.DomUtil.create("div", "legend");
        div.innerHTML += "<h4>Légende</h4>";
        div.innerHTML += "<i style='background: #800026'></i><span>Nombre de médias disponibles sur un territoire donné (foncé = nombre élevé, clair = nombre faible [blanc=pas de résultats])</span>.";
        return div;
    };

    legende.addTo(carte);
}

/* <============= Section 8 : Fonctions de Gestion des Layers et des Données ===============> */

/**
 * Fonction pour réinitialiser les résultats.
 */
function reinitialiserResultats() {
    divResultats.innerHTML = '';
    divResultats.classList.remove('visible');
    divResultats.classList.add('hidden');
    nomPays = null;
}
let pageActuelle = 1;
const resultatsParPage = 10;
let totalPages = 1;
function envoyerDonneesFlask(page = 1) {
    afficherChargement();
    pageActuelle = page;  // mettre à jour la page actuelle
    console.log("Nom pays dans Flask", nomPays);
    var data = {
        slider: slider.noUiSlider.get(),
        export: exporter,
        seulThesaurus: seulThesaurus
    };

    if (nomPays) {
        data.name = nomPays;
    }
    if (dataRecherche) {
        data.entite1 = dataRecherche;
    }

    fetch('/carte_monde', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(response => {
        let chaineResultats = "";
        let nombre_resultats = "";

        if (dataRecherche && nomPays) {
            let resultatsFiltres = response.results.filter(result => result.NAME === nomPays);

            if (resultatsFiltres.length > 0) {
                nombre_resultats = `Recherche : ${dataRecherche} | Sur le territoire : ${resultatsFiltres[0].NAME} | Nombre de résultats : ${resultatsFiltres[0].NombreResultats}<br>`;

                // Filtrer les résultats qui ont un GUID
                let resultatsAvecGUID = resultatsFiltres[0].GUID.filter(guid => guid); // Filtrer les GUID non vides

                // Logique pour la pagination basée sur les résultats avec GUID
                totalPages = Math.ceil(resultatsAvecGUID.length / resultatsParPage);
                const paginationHTML = creerPagination();
                const startIndex = (pageActuelle - 1) * resultatsParPage;
                const endIndex = Math.min(startIndex + resultatsParPage, resultatsAvecGUID.length);

                chaineResultats += '<table class="table">';
                chaineResultats += '<tr><th>Titre</th><th>Lien GICO</th><th>Visonneuse</th><th>Date</th><th>Guid</th></tr>';

                for (let i = startIndex; i < endIndex; i++) {
                    const indexGlobal = resultatsFiltres[0].GUID.indexOf(resultatsAvecGUID[i]); // Trouver l'index global correspondant dans resultatsFiltres[0]

                    chaineResultats += '<tr>';
                    chaineResultats += `<td>${resultatsFiltres[0].Titre[indexGlobal]}</td>`;

                    if (resultatsFiltres[0].idGICO[indexGlobal]) {
                        chaineResultats += `<td><a href="${resultatsFiltres[0].idGICO[indexGlobal]}" target="_blank">Fiche détaillée (GICO)</a></td>`;
                    } else {
                        chaineResultats += `<td>Pas de fiche disponible</td>`;
                    }

                    if (resultatsFiltres[0].UMID[indexGlobal]) {
                        chaineResultats += `<td><a href="${resultatsFiltres[0].UMID[indexGlobal]}" target="_blank">Visionner</a></td>`;
                    } else {
                        chaineResultats += `<td>Pas de media disponible </td>`;
                    }

                    chaineResultats += `<td>${resultatsFiltres[0].Date[indexGlobal]}</td>`;
                    chaineResultats += `<td>${resultatsFiltres[0].GUID[indexGlobal]}</td>`;
                    chaineResultats += '</tr>';
                }

                chaineResultats += '</table>';
                chaineResultats += paginationHTML;
                cacherChargement();
            } else {
                nombre_resultats = `Territoire: ${nomPays} - Nombre de résultats : 0 <br>`;
            }

            document.getElementById('map').classList.add('reduced');
            divResultats.classList.remove('hidden');
            divResultats.classList.add('visible');

        } else if (dataRecherche) {
            miseAJourDataRecherche(response.results, response.minMax, geojsonLayer);
        } else if (nomPays) {
            let resultatsFiltres = response.results.filter(result => result.NAME === nomPays);
            nombre_resultats = `Territoire : ${resultatsFiltres[0].NAME} | Nombre de résultats : ${resultatsFiltres[0].NombreResultats}<br>`;
            if (resultatsFiltres.length > 0) {
                nombre_resultats = `Territoire : ${resultatsFiltres[0].NAME} | Nombre de résultats : ${resultatsFiltres[0].NombreResultats}<br>`;

                // Filtrer les résultats qui ont un GUID
                let resultatsAvecGUID = resultatsFiltres[0].GUID.filter(guid => guid); // Filtrer les GUID non vides

                // Logique pour la pagination basée sur les résultats avec GUID
                totalPages = Math.ceil(resultatsAvecGUID.length / resultatsParPage);
                const paginationHTML = creerPagination();
                const startIndex = (pageActuelle - 1) * resultatsParPage;
                const endIndex = Math.min(startIndex + resultatsParPage, resultatsAvecGUID.length);

                chaineResultats += '<table class="table">';
                chaineResultats += '<tr><th>Titre</th><th>Lien GICO</th><th>Visonneuse</th><th>Date</th><th>Guid</th></tr>';

                for (let i = startIndex; i < endIndex; i++) {
                    const indexGlobal = resultatsFiltres[0].GUID.indexOf(resultatsAvecGUID[i]); // Trouver l'index global correspondant dans resultatsFiltres[0]

                    chaineResultats += '<tr>';
                    chaineResultats += `<td>${resultatsFiltres[0].Titre[indexGlobal]}</td>`;

                    if (resultatsFiltres[0].idGICO[indexGlobal]) {
                        chaineResultats += `<td><a href="${resultatsFiltres[0].idGICO[indexGlobal]}" target="_blank">Fiche détaillée (GICO)</a></td>`;
                    } else {
                        chaineResultats += `<td>Pas de fiche disponible</td>`;
                    }

                    if (resultatsFiltres[0].UMID[indexGlobal]) {
                        chaineResultats += `<td><a href="${resultatsFiltres[0].UMID[indexGlobal]}" target="_blank">Visionner</a></td>`;
                    } else {
                        chaineResultats += `<td>Pas de media disponible </td>`;
                    }

                    chaineResultats += `<td>${resultatsFiltres[0].Date[indexGlobal]}</td>`;
                    chaineResultats += `<td>${resultatsFiltres[0].GUID[indexGlobal]}</td>`;
                    chaineResultats += '</tr>';
                }

                chaineResultats += '</table>';
                chaineResultats += paginationHTML;
                cacherChargement();
            }

            document.getElementById('map').classList.add('reduced');
            divResultats.classList.remove('hidden');
            divResultats.classList.add('visible');
        } else {
            miseAJourDataRecherche(response.results, response.minMax, geojsonLayer);
        }

        if (nombre_resultats) {
            divResultats.innerHTML = `<h2>Résultats de la recherche</h2><h6>${nombre_resultats}</h6><div>${chaineResultats}</div>
            <button type="button" class="close close-btn" aria-label="Close" id="closeResults">
            <span aria-hidden="true">&times;</span>
            </button>`;

            document.getElementById('closeResults').addEventListener('click', function () {
                reinitialiserResultats();
                document.getElementById('map').classList.remove('reduced');
                envoyerDonneesFlask();
            });
        }

        if (response.download_url) {
            const url_telechargement = response.download_url;
            const a = document.createElement('a');
            a.href = url_telechargement;
            a.download = url_telechargement;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            exporter = false;
            alert("La sélection actuelle a bien été téléchargée.");
        }

        mettreAJourPopups(response.results);
    })
    .catch(error => {
        console.error('Erreur lors de l\'envoi des données:', error);
    });
}









function creerPagination() {
    let paginationHTML = '<nav aria-label="Page navigation"><ul class="pagination">';

    // Afficher le bouton "Première page" et "Page précédente" si ce n'est pas la première page
    if (pageActuelle > 1) {
        paginationHTML += `<li class="page-item"><button class="page-btn page-link" data-page="1">Première</button></li>`;
        paginationHTML += `<li class="page-item"><button class="page-btn page-link" data-page="${pageActuelle - 1}">&laquo;</button></li>`;
    }

    // Afficher les 5 premiers numéros de page avant la page actuelle
    for (let i = Math.max(1, pageActuelle - 4); i < pageActuelle; i++) {
        paginationHTML += `<li class="page-item"><button class="page-btn page-link" data-page="${i}">${i}</button></li>`;
    }

    // Afficher la page actuelle (désactivée)
    paginationHTML += `<li class="page-item active" aria-current="page"><button class="page-btn page-link current" disabled>${pageActuelle}</button></li>`;

    // Afficher les 5 premiers numéros de page après la page actuelle
    for (let i = pageActuelle + 1; i <= Math.min(pageActuelle + 4, totalPages); i++) {
        paginationHTML += `<li class="page-item"><button class="page-btn page-link" data-page="${i}">${i}</button></li>`;
    }

    // Afficher le bouton "Dernière page" et "Page suivante" si ce n'est pas la dernière page
    if (pageActuelle < totalPages) {
        paginationHTML += `<li class="page-item"><button class="page-btn page-link" data-page="${pageActuelle + 1}">&raquo;</button></li>`;
        paginationHTML += `<li class="page-item"><button class="page-btn page-link" data-page="${totalPages}">Dernière</button></li>`;
    }

    paginationHTML += '</ul></nav>';

    return paginationHTML;
}


document.addEventListener('click', function (e) {
    if (e.target.classList.contains('page-btn')) {
        const page = parseInt(e.target.getAttribute('data-page'));
        envoyerDonneesFlask(page);
    }
});


/*
 * Fonction pour mettre à jour les popups avec les résultats.
 *
 * @param {Array} resultats - Liste des résultats.
 */
function mettreAJourPopups(resultats) {
    // Vider les anciens labels
    etiquettes.forEach(etiquette => {
        carte.removeLayer(etiquette);
    });
    etiquettes = [];

    // Vérifier que le layer GeoJSON est défini
    if (geojsonLayer) {
        // Parcourir les résultats
        resultats.forEach(result => {
            // Vérifier chaque feature dans le layer GeoJSON
            geojsonLayer.eachLayer(function (layer) {
                if (layer.feature && layer.feature.properties && layer.feature.properties.NAME === result.NAME) {
                    var nombreResultats = result.NombreResultats || '';
                    var contenuPopup = `<div><h3>${result.NAME}</h3><p>Nombre de résultats : ${nombreResultats}</p></div>`;
                    layer.bindPopup(contenuPopup);
                    layer.on('click', function (e) {
                        interactivite(e);
                    });

                     let etiquette = { nombreResultats, name: result.NAME };

                    // Définir les coordonnées pour l'étiquette
                    var center;
                    if (result.NAME === "Russie") {
                        // Coordonnées manuelles pour la Russie
                        center = [85, 61.3188];
                    }
                    else if (result.NAME === "Norvège"){
                        center = [8, 61];
                    }
                    else if (result.NAME === "USA"){
                        center = [-100, 39]
                    }

                    else if (result.NAME === "Canada"){
                        center = [-104, 57] 
                    }
                    
                    else {
                        // Utiliser le centre de masse pour les autres entités
                        center = turf.centerOfMass(layer.feature).geometry.coordinates;
                    }

                    var labelAffichage = L.marker([center[1], center[0]], {
                        icon: L.divIcon({
                            className: 'label',
                            html: nombreResultats,
                            iconSize: [65, 30]
                        })
                    }).addTo(carte);
                    etiquettes.push(labelAffichage);
                    // Attacher un événement click à l'étiquette
                    labelAffichage.on('click', function (e) {
                        nomPays = etiquette.name; // Mise à jour de nomPays
                      
                        interactivite(e);
                    });

            
       
                }
            });
        });
    }
}


