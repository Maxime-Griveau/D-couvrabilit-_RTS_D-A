console.log("Script chargé !");

/* <============= Section 1 : Initialisation de la carte avec Leaflet ===============> */

// Initialisation de la carte avec Leaflet
var carte = L.map('map', {
    wheelPxPerZoomLevel: 150,  //Réduction du zoom par mouvement de la molette 
    zoomSnap: 0.5,             // Ajoute des niveaux de zoom intermédiaires 
    zoomDelta: 1             // Contrôle la valeur du zoom quand l'utilisateur clique sur + ou - sur la carte 
}).setView([46.8155135, 8.224471999999992], 8);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 12,
    minZoom:7,
    attribution: '© OpenStreetMap'
}).addTo(carte);



// Variables globales
var geojson_villes = geojsonVillesUrl;
var geojson_districts = geojsonDistrictsUrl;
var geojson_cantons = geojsonCantonsUrl;
var base_geojson_url = baseGeojsonUrl;
var controleRecherche = {};
var controleRechercheActif = null;
var minMax = {};
var caseCochee = false;
var nomPropriete = null;
var valeursSlider = [1954, 2024];
var layerActuel = '';
var dataRecherche = "";
var nombreResultats = "";
var exporter = false;
var etiquettes = [];
var seulThesaurus = false;

var divResultats = document.getElementById('resultats');
var chargement = document.getElementById("chargementPage");

// Initialisation
cacherChargement();
initEcouteursEvenements();
initialiserSlider();
initialiserLegendeCarte();
initialiserBoutonsRadio();
initialiserBoutonReset();

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
/**
 * Fonction pour créer un layer GeoJSON avec une épaisseur spécifiée et l'ajouter à la carte.
 *
 * @param {Object} data - Données GeoJSON.
 * @param {number} epaisseur - Épaisseur des traits.
 * @param {Object} carte - Objet représentant la carte Leaflet.
 * @returns {Object} - Layer GeoJSON ajouté à la carte.
 */
function creerLayer(data, epaisseur, carte) {
    // Ajouter un log pour vérifier les entités sans propriétés
    data.features.forEach(feature => {
        if (!feature.properties) {
            console.warn('Feature without properties:', feature);
        }
    });

    // Filtrer et trier les entités GeoJSON par render_order
    data.features = data.features.filter(feature => feature.properties && feature.properties.NAME)
                                  .sort((a, b) => (b.properties.render_order || 0) - (a.properties.render_order || 0));

    return L.geoJSON(data, {
        style: function (feature) {
            return { weight: epaisseur };
        },
        onEachFeature: function (feature, layer) {
            if (feature.properties && feature.properties.render_order) {
                layer.on('add', function () {
                    layer.bringToFront();
                });
            }
        }
    }).addTo(carte);
}
/**
 * Fonction pour créer une barre de recherche pour un layer donné.
 *
 * @param {Object} carte - Objet représentant la carte Leaflet.
 * @param {Object} layer - Layer sur lequel appliquer la recherche.
 * @param {string} nomPropriete - Propriété à utiliser pour la recherche.
 * @returns {Object} - Contrôle de recherche.
 */
function barreRecherche(carte, layer, nomPropriete) {
    // Filtrer les entités sans propriétés
    let validLayers = [];
    layer.eachLayer(function(l) {
        if (l.feature && l.feature.properties && l.feature.properties[nomPropriete]) {
            validLayers.push(l);
        }
    });

    // Créer un nouveau LayerGroup avec uniquement les entités valides
    let validLayerGroup = L.layerGroup(validLayers);

    var controleRecherche = new L.Control.Search({
        layer: validLayerGroup,
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
            validLayerGroup.eachLayer(function (layer) {
                if (!layer.feature || !layer.feature.properties) {
                    console.warn('Layer with missing properties:', layer);
                }
            });
        }
    });
    return controleRecherche;
}

/**
 * Fonction pour activer ou désactiver le contrôle de recherche pour le layer actif.
 *
 * @param {string} coucheActive - Nom du layer actif.
 */
function basculerControleRecherche(coucheActive) {
    if (controleRechercheActif && carte.hasLayer(controleRechercheActif)) {
        carte.removeControl(controleRechercheActif);
    }
    controleRechercheActif = controleRecherche[coucheActive];
    if (controleRechercheActif) carte.addControl(controleRechercheActif);
}

/**
 * Fonction pour afficher ou masquer les informations des districts.
 *
 * @param {Element} element - Élément HTML.
 * @param {boolean} afficher - Indicateur pour afficher ou masquer l'élément.
 */
function informationsDistricts(element, afficher) {
    if (afficher) {
        element.classList.remove('info-hidden');
        element.classList.add('info-visible');
    } else {
        element.classList.remove('info-visible');
        element.classList.add('info-hidden');
    }
}

/**
 * Fonction pour gérer l'interactivité des layers.
 *
 * @param {Event} e - Événement Leaflet.
 */
function interactivite(e) {
    var couche = e.target;
    if (couche.feature && couche.feature.properties) {
        nomPropriete = couche.feature.properties.NAME;
    }
    envoyerDonneesFlask();
}

/**
 * Fonction pour mettre à jour les données de recherche.
 *
 * @param {Array} data - Données à mettre à jour.
 * @param {Object} minMax - Valeurs min et max pour l'échelle de couleurs.
 */
function miseAJourDataRecherche(data, minMax) {
    const donneesGeojson = {
        type: "FeatureCollection",
        features: data.map(item => ({
            type: "Feature",
            properties: {
                NAME: item.NAME,
                NombreResultats: item.NombreResultats
            }
        }))
    };

    window[layerActuel].eachLayer(function (layer) {
        if (layer.feature && layer.feature.properties) {
            const feature = donneesGeojson.features.find(f => f.properties.NAME === layer.feature.properties.NAME);
            if (feature) {
                const value = feature.properties.NombreResultats;
                layer.setStyle({
                    fillColor: CouleursResultats(value, minMax),
                    fillOpacity: 0.5,
                    color: "Red",
                    weight: layer.options.weight
                });
            }
        }
        cacherChargement();
    });
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

    document.getElementById('flexCheckChecked').addEventListener('change', function () {
        caseCochee = this.checked;
        envoyerDonneesFlask();
    });
    document.getElementById('seulThesaurus').addEventListener('change', function () {
        seulThesaurus = this.checked;
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
            'min': 1954,
            'max': 2024,
        },
        start: [1954, 2024],
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

/* <============= Section 5 : Initialisation des Boutons Radio ===============> */

/**
 * Fonction pour initialiser les boutons radio pour la sélection des couches.
 */
function initialiserBoutonsRadio() {
    ['villes', 'districts', 'cantons'].forEach(type => {
        document.getElementById(`${type}Radio`).addEventListener('change', function () {
            const geojsonLayers = {
                villes: geojson_villes,
                districts: geojson_districts,
                cantons: geojson_cantons
            };

            if (this.checked) {
                ['villes', 'districts', 'cantons'].forEach(layerType => {
                    if (layerType !== type) {
                        changementLayer(false, geojsonLayers[layerType], layerType, '', 'NAME', carte, layerType === 'districts' ? 'info-districts' : (layerType === 'cantons' ? 'info-cantons' : 'info-villes'));
                        reinitialiserResultats();
                    }
                });

                layerActuel = type;
                changementLayer(true, geojsonLayers[type], type, type === 'cantons' ? 2 : (type === 'districts' ? 1 : 0.5), 'NAME', carte, type === 'districts' ? 'info-districts' : (type === 'cantons' ? 'info-cantons' : 'info-villes'));
            }
        });
    });

    if (document.getElementById('cantonsRadio').checked) {
        layerActuel = 'cantons';
        changementLayer(true, geojson_cantons, 'cantons', 2, 'NAME', carte, 'info-cantons');
    }
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
    nomPropriete = null;
}

/**
 * Fonction qui change le layer de la carte en fonction de l'état de la case à cocher.
 * Si la case est cochée, le layer est ajouté à la carte, sinon il est retiré.
 *
 * @param {boolean} coche - État de la case à cocher.
 * @param {string} geojson - URL du fichier GeoJSON contenant les données à afficher.
 * @param {string} nomLayer - Nom du layer à créer ou à récupérer.
 * @param {number} epaisseur - Épaisseur des traits.
 * @param {string} nomPropriete - Nom de la propriété à utiliser pour la recherche.
 * @param {Object} carte - Objet représentant la carte Leaflet.
 * @param {string} infoElementId - ID de l'élément d'information à afficher ou masquer.
 */
function changementLayer(coche, geojson, nomLayer, epaisseur, nomPropriete, carte, infoElementId) {
    const elementInfo = infoElementId ? document.getElementById(infoElementId) : null;
    if (coche) {
        if (!window[nomLayer]) {
            fetch(geojson)
                .then(response => response.json())
                .then(data => {
                    window[nomLayer] = creerLayer(data, epaisseur, carte);
                    if (!controleRecherche[nomLayer]) {
                        controleRecherche[nomLayer] = barreRecherche(carte, window[nomLayer], nomPropriete);
                        envoyerDonneesFlask();
                    }
                    basculerControleRecherche(nomLayer);
                    if (elementInfo) {
                        informationsDistricts(elementInfo, true);
                    }
                });
        } else {
            carte.addLayer(window[nomLayer]);
            basculerControleRecherche(nomLayer);
            if (elementInfo) {
                informationsDistricts(elementInfo, true);
            }
        }
    } else {
        if (window[nomLayer]) {
            carte.removeLayer(window[nomLayer]);
            document.getElementById('map').classList.remove('reduced');
            divResultats.classList.add('hidden');
            divResultats.classList.remove('visible');

        }
        if (controleRecherche[nomLayer]) {
            carte.removeControl(controleRecherche[nomLayer]);
        }
        if (elementInfo) {
            informationsDistricts(elementInfo, false);
        }
    }
}
let pageActuelle = 1;
const resultatsParPage = 10;
let totalPages = 1;

/**
 * Fonction pour envoyer des données au serveur Flask et gérer la réponse.
 */
function envoyerDonneesFlask(page = 1) {
    pageActuelle = page;
    afficherChargement();

    var data = {
        excludeMetadata: caseCochee,
        seulThesaurus: seulThesaurus,
        slider: slider.noUiSlider.get(),
        layer: layerActuel,
        export: exporter,
        
        page: pageActuelle
    };

    if (nomPropriete) {
        data.name = nomPropriete;
    }
    if (dataRecherche) {
        data.entite1 = dataRecherche;
    }

    fetch('/carte_cliqueeV2', {
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
        let url_telechargement = "";

        if (dataRecherche && nomPropriete) {
            let resultatsFiltres = response.results.filter(result => result.NAME === nomPropriete);

            if (resultatsFiltres.length > 0) {
                nombre_resultats = `Territoire : ${resultatsFiltres[0].NAME} | Recherche : ${dataRecherche} | Nombre de résultats : ${resultatsFiltres[0].NombreResultats}<br>`;

                // Filtrer les résultats qui ont un GUID
                let resultatsAvecGUID = resultatsFiltres[0].GUID.filter(guid => guid); // Filtrer les GUID non vides

                // Logique pour la pagination basée sur les résultats avec GUID
                totalPages = Math.ceil(resultatsAvecGUID.length / resultatsParPage);
                const paginationHTML = creerPagination();
                const startIndex = (pageActuelle - 1) * resultatsParPage;
                const endIndex = Math.min(startIndex + resultatsParPage, resultatsAvecGUID.length);

                chaineResultats += '<table class="table table-hover" id="tableau_petit">';
                chaineResultats += '<tr><th>Titre</th><th>Lien GICO</th><th>Visionneuse</th><th>Date</th><th>Guid</th></tr>';

                for (let i = startIndex; i < endIndex; i++) {
                    const indexGlobal = resultatsFiltres[0].GUID.indexOf(resultatsAvecGUID[i]);

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
                nombre_resultats = `Territoire: ${nomPropriete} - Nombre de résultats : 0 <br>`;
            }

            document.getElementById('map').classList.add('reduced');
            divResultats.classList.remove('hidden');
            divResultats.classList.add('visible');

        } else if (dataRecherche) {
            miseAJourDataRecherche(response.results, response.minMax);
        } else if (nomPropriete) {
            let resultatsFiltres = response.results.filter(result => result.NAME === nomPropriete);
            if (resultatsFiltres.length > 0) {
                nombre_resultats = `Territoire : ${resultatsFiltres[0].NAME} | Nombre de résultats : ${resultatsFiltres[0].NombreResultats}<br>`;

                // Filtrer les résultats qui ont un GUID
                let resultatsAvecGUID = resultatsFiltres[0].GUID.filter(guid => guid); // Filtrer les GUID non vides

                // Logique pour la pagination basée sur les résultats avec GUID
                totalPages = Math.ceil(resultatsAvecGUID.length / resultatsParPage);
                const paginationHTML = creerPagination();
                const startIndex = (pageActuelle - 1) * resultatsParPage;
                const endIndex = Math.min(startIndex + resultatsParPage, resultatsAvecGUID.length);

                chaineResultats += '<table class="table table-hover" id="tableau_petit">';
                chaineResultats += '<tr><th>Titre</th><th>Lien GICO</th><th>Visionneuse</th><th>Date</th><th>Guid</th></tr>';

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
                nombre_resultats = `Territoire: ${nomPropriete} - Nombre de résultats : 0 <br>`;
            }

            document.getElementById('map').classList.add('reduced');
            divResultats.classList.remove('hidden');
            divResultats.classList.add('visible');
        } else {
            miseAJourDataRecherche(response.results, response.minMax);
        }

        if (nombre_resultats) {
            divResultats.innerHTML = `<h2>Résultats de la recherche</h2><h6>${nombre_resultats}</h6><p>${chaineResultats}</p>
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
            url_telechargement = response.download_url;
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





/**
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
    
    resultats.forEach(result => {
        if (window[layerActuel]) {
            window[layerActuel].eachLayer(function (layer) {
                if (layer.feature && layer.feature.properties && layer.feature.properties.NAME === result.NAME) {
                    var nombreResultats = result.NombreResultats || '';
                    var contenuPopup = `<div><h3>${result.NAME}</h3><p>Nombre de résultats : ${nombreResultats}</p></div>`;
                    layer.bindPopup(contenuPopup);
                    layer.on({ click: interactivite });
                    
                    if (layerActuel == "cantons" || layerActuel == "districts") {
                        console.log("LAYER", layerActuel);
                        
                        let etiquette = { nombreResultats, name: result.NAME };
                        
                        var labelAffichage = L.marker(layer.getCenter(), {
                            icon: L.divIcon({
                                className: 'label',
                                html: etiquette.nombreResultats,
                                iconSize: [65, 30]
                            })
                        }).addTo(window[layerActuel]);
                        
                        // Ajouter l'étiquette à la liste des étiquettes
                        etiquettes.push(labelAffichage);
                        
                        // Attacher l'événement click à l'étiquette
                        labelAffichage.on('click', function (e) {
                            nomPropriete = etiquette.name; // Mise à jour de nomPropriete
                            interactivite(e);
                        });
                    }
                }
            });
        }
    });
}
