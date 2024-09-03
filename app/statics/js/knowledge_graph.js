console.log("script chargé !");
cacherChargement();

var valeursSlider = "";
var excludeMetadata = "";
var seulThesaurus = "";



initialiserSlider();

// Récupération des valeurs du slider 
document.getElementById('applyYearChange').addEventListener('click', function () {
    envoyerDonneesFlask();
});

document.getElementById('flexCheckChecked').addEventListener('change', function () {
    excludeMetadata = this.checked;
    envoyerDonneesFlask();
});
document.getElementById('seulThesaurus').addEventListener('change', function () {
    seulThesaurus = this.checked;
    envoyerDonneesFlask();
});


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
/**
 * Fonction pour envoyer les données au serveur Flask.
 */
function envoyerDonneesFlask() {
    afficherChargement();
    var entite1 = document.getElementById('Entite1').value;
    var entite2 = document.getElementById('Entite2').value;
    var entite3 = document.getElementById('Entite3').value;
    var entite4 = document.getElementById('Entite4').value;
    fetch('/recherche_knowledge_graph', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            Entite1: entite1,
            Entite2: entite2,
            Entite3: entite3,
            Entite4: entite4,
            slider: slider.noUiSlider.get(),
            excludeMetadata: excludeMetadata,
            seulThesaurus: seulThesaurus,
        })
    })
        .then(response => response.json())
        .then(data => {
            cacherChargement();
            // console.log(data, entite1, entite2, entite3, entite4)
            if (data && data.length > 0) {
                const graphData = data[0]; // Accéder au premier élément de la liste
                const jsonStructure = graphData.json_structure; // Extraire json_structure
                const urls = graphData.url; // Extraire les URLs
                const nombre_noeuds = graphData.nombre_noeuds;
                const collection = graphData.Collection; 
                const datePublication = graphData.DatePublication;

                document.getElementById("resultats").innerHTML = `<h3>Nombre de résultats communs : ${nombre_noeuds}</h3><p><i>Vous pouvez zoomer avec la molette et vous déplacer en cliquant.</i><p><b>Les noms de collections sont des URL vers la fiche GICO</b></p>`;

                KnowledgeGraph(jsonStructure, urls, collection, datePublication, entite1, entite2, entite3, entite4, nombre_noeuds);
            } else {
                console.error('Aucune donnée reçue depuis le serveur.');
            }
        })
        .catch(error => {
            cacherChargement();
            console.error('Erreur:', error);
        });
}

document.getElementById('recherche_form').addEventListener('submit', function (event) {
    event.preventDefault();
    envoyerDonneesFlask();
});

/**Recherche en cours : 
Valeur recherchée 

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

/*Génération d'un knowledgeGraph avec D3.JS*/
function KnowledgeGraph(graph, urls, collection, datePublication, entite1, entite2, entite3, entite4, nombre_noeuds) {
    const width = 1200;
    const height = 1000;

    const entityNodes = graph.nodes.filter(node => [entite1, entite2, entite3, entite4].includes(node.name));
    const guidNodes = graph.nodes.filter(node => ![entite1, entite2, entite3, entite4].includes(node.name));

    graph.nodes.forEach((node, index) => {
        node.url = urls[index];
        node.Collection = collection[index];
        node.DatePublication = datePublication[index] ? datePublication[index].slice(0, 10) : "Date inconnue";
    });

    document.getElementById('graph').innerHTML = '';

    const svg = d3.select("#graph").append("svg")
        .attr("width", width)
        .attr("height", height)
        .call(d3.zoom().on("zoom", function (event) {
            svg.attr("transform", event.transform);
        }))
        .append("g");

    const numGuids = nombre_noeuds;
    const linkDistance = Math.min(400, Math.max(100, 200 + numGuids * 4));
    const collisionRadius = Math.min(60, Math.max(30, 30 + numGuids * 2));
    const chargeStrength = Math.min(-50, Math.max(-300, -200 - numGuids * 0.5));

    const simulation = d3.forceSimulation(graph.nodes)
        .force("link", d3.forceLink(graph.links).id(d => d.id).distance(linkDistance))
        .force("charge", d3.forceManyBody().strength(chargeStrength))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(collisionRadius))
        .force("x", d3.forceX().strength(0.5).x(d => {
            if (d.name === entite1 || d.name === entite2) return width / 4;
            if (d.name === entite3 || d.name === entite4) return 3 * width / 4;
            return width / 2;
        }))
        .force("y", d3.forceY().strength(0.5).y(height / 2));

    const link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(graph.links)
        .enter().append("line")
        .attr("class", "link");

    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(graph.nodes)
        .enter().append("circle")
        .attr("class", "node")
        .attr("r", 5)
        .attr("fill", d => [entite1, entite2, entite3, entite4].includes(d.name) ? "darkred" : "darkblue");

    const label = svg.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(graph.nodes)
        .enter().append("text")
        .attr("class", "label")
        .attr("dx", 10)
        .attr("dy", ".35em")
        .each(function (d) {
            if (![entite1, entite2, entite3, entite4].includes(d.name)) {
                const labelText = `${d.Collection} | ${d.DatePublication}`;
                d3.select(this).append("a")
                    .attr("xlink:href", d.url)
                    .attr("target", "_blank")
                    .text(labelText);
            } else {
                d3.select(this)
                    .style("font-size", "24px")
                    .text(d.name);
            }
        });

    simulation.nodes(graph.nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(graph.links);

    function ticked() {
        link.attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node.attr("cx", d => d.x)
            .attr("cy", d => d.y);

        label.attr("x", d => d.x)
            .attr("y", d => d.y);
    }

    cacherChargement();
}
