const graphDiv = document.getElementById("graph");

fetch("http://localhost:3000")
    .then(async res => {
        Plotly.newPlot( graphDiv, [ await res.json() ]); 
    })

