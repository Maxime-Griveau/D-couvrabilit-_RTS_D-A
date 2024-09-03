console.log("Script chargé !");
var map = L.map('map').setView([46.8182, 8.2275], 8); // Réglage sur la Suisse

/* Création du fonds de carte et de ses attributs par défaut */
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
}).addTo(map);

/* Import des données */
var geojson_villes = geojsonVillesUrl;
var geojson_districts = geojsonDistrictsUrl;
var geojson_cantons = geojsonCantonsUrl;
var base_geojson_url = baseGeojsonUrl;

var villesLayer, districtsLayer, cantonsLayer;
var searchControls = {}; // Objet pour stocker les barres de recherche 
var activeSearchControl = null; // Variable pour stocker la barre de recherche du niveau courant
var minMax = {}; // Variable globale pour stocker les valeurs min/max

// Variables globales pour stocker l'état de la checkbox et le nom de l'entité géographique 
var isCheckboxChecked = false;

var featureName = null;

var metadatas = "False"; // Initialement, elle doit être à false 

var sliderValues = [1954, 2024]; // Valeurs initiales du slider



/* ==================== Calcul des valeurs statistiques ==================== */

/**
 * Fonction pour calculer les valeurs aux 5ème et 95ème percentiles de NombreResultats.
 *
 * @param {Object} data - Données GeoJSON.
 * @returns {Object} - Objet contenant les valeurs aux 5ème et 95ème percentiles.
 */
function getMinMax(data) {
    let values = data.features.map(feature => feature.properties.NombreResultats || 0); // Assurez-vous que les valeurs ne sont pas undefined

    // Tri des valeurs pour calculer les percentiles
    values.sort((a, b) => a - b);

    // Fonction pour calculer les percentiles
    function percentile(arr, p) {
        const index = (p / 100) * (arr.length - 1);
        if (Math.floor(index) === index) {
            return arr[index];
        } else {
            const lower = arr[Math.floor(index)];
            const upper = arr[Math.ceil(index)];
            return lower + (upper - lower) * (index - Math.floor(index));
        }
    }

    const min = percentile(values, 5);  // 5ème percentile
    const max = percentile(values, 95); // 95ème percentile

    return { min, max };
}

/* ==================== Gestion des couches et des fonctionnalités ==================== */

/**
 * Fonction pour gérer chaque feature de la couche GeoJSON.
 * Ajoute un popup affichant le nom et le nombre de résultats.
 *
 * @param {Object} feature - Feature GeoJSON.
 * @param {Object} layer - Layer Leaflet.
 */
function onEachFeature(feature, layer) {
    if (feature.properties) {
        let popupContent = '<div>';

        if (feature.properties.NAME) {
            popupContent += `<h3>${feature.properties.NAME}</h3>`;
        }
        
        if (feature.properties.NombreResultats !== undefined) {
            popupContent += `<p>Nombre de résultats: ${feature.properties.NombreResultats}</p>`;
        }
        popupContent += '</div>';

        if (popupContent) {
            layer.bindPopup(popupContent);
        }

        layer.on({
            click: interractivité,
        });
    }
}

/**
 * Fonction pour créer un layer GeoJSON avec un style personnalisé.
 *
 * @param {Object} data - Données GeoJSON.
 * @param {string} epaisseur - Épaisseur des traits.
 * @param {Object} map - Objet représentant la carte Leaflet.
 * @param {string} propertyName - Nom de la propriété à utiliser pour la recherche.
 * @returns {Object} - Layer GeoJSON créé.
 */
function creerLayer(data, epaisseur, map, propertyName) {
    return L.geoJSON(data, {
        onEachFeature: onEachFeature,
        style: function (feature) {
            return {
                fillColor: CouleursResultats(feature.properties.NombreResultats || 0, minMax),
                fillOpacity: 0.5,
                color: "Red",
                weight: epaisseur
            };
        }
    }).addTo(map);
}

/**
 * Fonction pour créer une barre de recherche associée à un layer.
 *
 * @param {Object} map - Objet représentant la carte Leaflet.
 * @param {Object} layer - Layer GeoJSON à utiliser pour la recherche.
 * @param {string} propertyName - Nom de la propriété à utiliser pour la recherche.
 * @returns {Object} - Contrôle de recherche créé.
 */
function barreRecherche(map, layer, propertyName) {
    var searchControl = new L.Control.Search({
        layer: layer,
        propertyName: propertyName,
        marker: false,
        moveToLocation: function (latlng, title, map) {
            map.setView(latlng, 12);
        }
    });

    searchControl.on('search:locationfound', function (e) {
        e.layer.openPopup();
    });

    return searchControl;
}

/* ==================== Gestion des couches et des fonctionnalités ==================== */

/**
 * Fonction qui change le layer de la carte en fonction de l'état de la case à cocher.
 * Si la case est cochée, le layer est ajouté à la carte, sinon il est retiré.
 *
 * @param {boolean} checked - État de la case à cocher.
 * @param {string} geojson - URL du fichier GeoJSON contenant les données à afficher.
 * @param {string} layerName - Nom du layer à créer ou à récupérer.
 * @param {string} epaisseur - Épaisseur des traits.
 * @param {string} propertyName - Nom de la propriété à utiliser pour la recherche.
 * @param {Object} map - Objet représentant la carte Leaflet.
 * @param {string} infoElementId - ID de l'élément d'information à afficher ou masquer.
 */
function changementLayer(checked, geojson, layerName, epaisseur, propertyName, map, infoElementId) {
    const infoElement = infoElementId ? document.getElementById(infoElementId) : null;

    if (checked) {
        if (!window[layerName]) {
            fetch(geojson)
                .then(response => response.json())
                .then(data => {
                    minMax = getMinMax(data); 
                    window[layerName] = creerLayer(data, epaisseur, map, propertyName);
                    updateLayerStyles(window[layerName], minMax);
                    if (!searchControls[layerName]) {
                        searchControls[layerName] = barreRecherche(map, window[layerName], propertyName);
                    }
                    toggleSearchControl(layerName);
                    if (infoElement) {
                        informationsDistricts(infoElement, true);
                    }
                });
        } else {
            map.addLayer(window[layerName]);
            minMax = getMinMax(window[layerName].toGeoJSON()); 
            updateLayerStyles(window[layerName], minMax);
            toggleSearchControl(layerName);
            if (infoElement) {
                informationsDistricts(infoElement, true);
            }
        }
    } else {
        if (window[layerName]) {
            map.removeLayer(window[layerName]);
        }
        if (searchControls[layerName]) {
            map.removeControl(searchControls[layerName]);
        }
        if (infoElement) {
            informationsDistricts(infoElement, false);
        }
    }
}

/**
 * Fonction pour basculer le contrôle de recherche actif.
 *
 * @param {string} activeLayer - Nom du layer actif.
 */
function toggleSearchControl(activeLayer) {
    if (activeSearchControl && map.hasLayer(activeSearchControl)) {
        map.removeControl(activeSearchControl);
    }
    activeSearchControl = searchControls[activeLayer];
    if (activeSearchControl) {
        map.addControl(activeSearchControl);
    }
}

/**
 * Fonction pour afficher ou masquer les informations des districts.
 *
 * @param {Object} element - Élément DOM à afficher ou masquer.
 * @param {boolean} show - Indicateur pour afficher (true) ou masquer (false).
 */
function informationsDistricts(element, show) {
    if (show) {
        element.classList.remove('info-hidden');
        element.classList.add('info-visible');
    } else {
        element.classList.remove('info-visible');
        element.classList.add('info-hidden');
    }
}

/**
 * Fonction pour mettre à jour les styles d'un layer avec les valeurs min et max calculées.
 *
 * @param {Object} layer - Layer GeoJSON.
 * @param {Object} minMax - Objet contenant les valeurs min et max.
 */
function updateLayerStyles(layer, minMax) {

    layer.eachLayer(function (layer) {
        let resultValue = layer.feature.properties.NombreResultats || 0;
        
        layer.setStyle({
            fillColor: CouleursResultats(resultValue, minMax),
            fillOpacity: 0.5,
            color: "Red",
            weight: layer.options.weight // Preserve original weight
        });
    });
}

/* ==================== Gestion des événements de changement de couche ==================== */

document.getElementById('villesCheckbox').addEventListener('change', function () {
    if (this.checked) {
        layerActuel = 'Communes';
    } else if (layerActuel === 'Communes') {
        layerActuel = '';
    }
    changementLayer(this.checked, geojson_villes, 'Communes', '0.5', 'NAME', map);
    if(this.checked){ console.log(`Le layer sélectionné est : ${layerActuel}`)}
});

document.getElementById('districtsCheckbox').addEventListener('change', function () {
    if (this.checked) {
        layerActuel = 'Districts';
    } else if (layerActuel === 'Districts') {
        layerActuel = '';
    }
    changementLayer(this.checked, geojson_districts, 'Districts', '1', 'NAME', map, 'info-districts');
    if(this.checked){ console.log(`Le layer sélectionné est : ${layerActuel}`)}
});

document.getElementById('cantonsCheckbox').addEventListener('change', function () {
    if (this.checked) {
        layerActuel = 'Cantons';
    } else if (layerActuel === 'Cantons') {
        layerActuel = '';
    }
    changementLayer(this.checked, geojson_cantons, 'Cantons', '2', 'NAME', map, 'info-cantons');
    if(this.checked){ console.log(`Le layer sélectionné est : ${layerActuel}`)}
});

/* Initialiser les cantons si la case est cochée par défaut */
if (document.getElementById('cantonsCheckbox').checked) {
    layerActuel = 'Cantons';
    changementLayer(true, geojson_cantons, 'Cantons', '2', 'NAME', map, 'info-cantons');
}


/* ==================== Gestion des interactions utilisateur ==================== */

/**
 * Fonction pour gérer les clics sur la carte
 *
 * @param {e} evenement - clic sur la carte.
 * 
 */
function interractivité(e) {
    var layer = e.target;
    featureName = layer.feature.properties.NAME;
    sendDataForMapClick(); // Envoyer les données lors du clic sur la carte
}

// Fonction pour envoyer les données à la route Flask lors du clic sur la carte
function sendDataForMapClick() {
    // La variable data prend la valeur de l'état de la checkbox
    var data = {
        excludeMetadata: isCheckboxChecked,
        slider: slider.noUiSlider.get() // Récupérer les valeurs du slider
    };
    // Et de la featureName si elle est présente (si clic sur la carte) 
    if (featureName) {
        data.name = featureName;
    }

    fetch('/carte_cliquee', { // Envoi à Flask via une requête fetch 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(response => {
        // Construction des résultats 
        let nombre_resultats = `Nombre de résultats : ${response.response}`;
        let resultsString = '';
        response.UMID.forEach(umid => {
            resultsString += `<p>UMID : ${umid}</p>`;
        });

        const resultatsDiv = document.getElementById('resultats');
        document.getElementById('map').classList.add('reduced');
        resultatsDiv.classList.add('visible');

        resultatsDiv.innerHTML = '';

        const h2 = document.createElement('h2');
        h2.textContent = 'Résultats de la recherche';
        resultatsDiv.appendChild(h2);

        const h6 = document.createElement('h6');
        h6.innerHTML = nombre_resultats;
        resultatsDiv.appendChild(h6);

        const p = document.createElement('p');
        p.innerHTML = resultsString;
        resultatsDiv.appendChild(p);
    });
}

// Fonction pour envoyer les données lors du changement du slider ou de la checkbox
function sendData() {
    var data = {
        excludeMetadata: isCheckboxChecked,
        slider: sliderValues  // Utilisez les valeurs stockées du slider
    };
    sendDataForMapClick(data);  // Envoyer les données et mettre à jour la carte
}


/* ==================== Gestion du slider ==================== */

// Slider double poignée 
var slider = document.getElementById('slider');
var rangeInput = document.getElementById('range');

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
            return Math.round(value); // Arrondir les valeurs affichées dans les tooltips
        },
        from: function (value) {
            return Number(value); // Convertir les valeurs de retour en nombre
        },
    }
});

// Déclencher l'actualisation des données lorsque le slider change
slider.noUiSlider.on('update', function (values, handle) {
    sliderValues = values.map(value => parseInt(value));  // Mettez à jour les valeurs du slider
});


// Bouton pour MAJ de la carte 
document.getElementById('applyYearChange').addEventListener('click', function () {
    updateData();  // Mettre à jour les données
    sendDataForMapClick();  // Envoyer les données et mettre à jour la carte
});


// Déclencher l'actualisation des données lorsque la case à cocher change
document.getElementById('flexCheckChecked').addEventListener('change', function () {
    isCheckboxChecked = this.checked;
    metadatas = isCheckboxChecked ? "True" : "False"; // Mise à jour de la variable

    console.log('Checkbox state updated:', isCheckboxChecked);
    console.log(`Variable metadatas: ${metadatas}`);
    updateData();  // Mettre à jour les données
    sendDataForMapClick();  // Envoyer les données et mettre à jour la carte
});


/**
 * Fonction qui met à jour les données en fonction des sélections 
 */
function updateData() {
    if (layerActuel) {  // Vérifier si layerActuel est défini
        const startYear = sliderValues[0];
        const endYear = sliderValues[1];

        let urls = [];
        for (let year = startYear; year <= endYear; year++) {
            let base_url = `${layerActuel}_${year}_Metadonnees.json`;
            let url = choixAnneesMetadonnee(layerActuel, base_url, year, metadatas);
            urls.push(`${base_geojson_url}${url}`);
        }

        Promise.all(urls.map(url => fetch(url).then(response => response.json())))
            .then(dataArray => {
                combinedResults = combineResults(dataArray);
                MAJgeojsonAvecResultats(combinedResults);
                minMax = getMinMax(window[layerActuel].toGeoJSON());
                window[layerActuel].eachLayer(function (layer) {
                    let resultValue = getResultForFeature(layer.feature.properties.NAME, combinedResults);
                    layer.feature.properties.NombreResultats = resultValue;
                    layer.setStyle({
                        fillColor: CouleursResultats(resultValue, minMax)
                    });
                });
            })
            .catch(error => console.error('Erreur:', error));
    }
}



/**
 * Fonction pour combiner les résultats des différentes années.
 *
 * @param {Array} dataArray - Tableau des résultats pour chaque année.
 * @returns {Array} - Tableau combiné des résultats.
 */

function combineResults(dataArray) {    
    let combinedResults = {};
    
    dataArray.forEach(data => {
        data.forEach(result => {
            if (combinedResults[result.NAME]) {
                combinedResults[result.NAME] += result.NombreResultats;
            } else {
                combinedResults[result.NAME] = result.NombreResultats;
            }
        });
    });
    
    return Object.keys(combinedResults).map(key => ({
        NAME: key,
        NombreResultats: combinedResults[key]
    }));
}


/**
 * Fonction qui permet à l'utilisateur de choisir son année et les métadonnées à afficher 
 *
 * @param {Object} layer - Objet représentant un layer de la carte.
 * @param {Object} url_de_base - url qui sera modifiée en fonction des sélections 
 * @param {int} annee - annee sélectionnée par l'utilisateur (récupérée depuis le slider)
 * @param {boolean} booleen - choix fait par l'utilisateur pour l'affichage des métadonnées, si True alors elle ne sont pas affichées 
 * @returns {string} url - url du fichier à atteindre  
 */
function choixAnneesMetadonnee(layer, url_de_base, annee, metadatas) {
    let url = url_de_base.replace('${territoire}', layer).replace('${year}', annee);

    if (metadatas === "True") {
        url = url.replace('Metadonnees', 'NoMetadonnees');
    }

    return url;
}

/* ==================== Mise à jour des données GeoJSON ==================== */

/**
 * Fonction qui met à jour le Geojson avec les résultats 
 *
 * @param {Object} results - Objet représentant les résultats (contenus dans le fichier json chargé dans updateData).
 */
function MAJgeojsonAvecResultats(results) {
    // Cette fonction met à jour les valeurs de NombreResultats dans les données GeoJSON
    let geojsonData = window[layerActuel].toGeoJSON();
    results.forEach(result => {
        let feature = geojsonData.features.find(f => f.properties.NAME === result.NAME);
        if (feature) {
            feature.properties.NombreResultats = result.NombreResultats;
        }
    });
}

/**
 * Fonction qui récupère le nombre de résultats et les associe au territoire concerné
 * @param {string} name - nom du territoire 
 * @param {object} results - nombre de résultats 
 * @return {integer} results - nombre de résultats si différent de zéro 
 */
function getResultForFeature(name, results) {
    // Cette fonction récupère la valeur de NombreResultats pour une feature donnée
    let result = results.find(r => r.NAME === name);
    return result ? result.NombreResultats : 0;
}


/* ==================== Gestion des couleurs ==================== */

/**
 * Fonction qui gère les couleurs 
 * @param {integer} value - valeur totale 
 * @param {object} minMax - Résultat de la fonction minMax  
 * @return {string} value - couleur sur une échelle de 7 en fonction des valeurs  
 */
function CouleursResultats(value, minMax) {
    const { min, max } = minMax;
    const range = max - min;
    const step = range / 7; // 7 intervales 
    return value > min + 6 * step ? '#800026' :
        value > min + 5 * step ? '#BD0026' :
            value > min + 4 * step ? '#E31A1C' :
                value > min + 3 * step ? '#FC4E2A' :
                    value > min + 2 * step ? '#FD8D3C' :
                        value > min + step ? '#FEB24C' :
                            '#FFEDA0';
}

/* ==================== Légende ==================== */
var legend = L.control({ position: "bottomleft" });

legend.onAdd = function (map) {
    var div = L.DomUtil.create("div", "legend");
    div.innerHTML += "<h4>Légende</h4>";
    div.innerHTML += '<i style="background: #800026"></i><span>Du plus foncé au plus clair,<br> nombre de médias disponibles <br> sur le territoire géographique.</span><br>';
    return div;
};

legend.addTo(map);
