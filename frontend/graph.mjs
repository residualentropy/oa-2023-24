const graphDiv = document.getElementById("graph");

const urlparams = new URLSearchParams(window.location.search);
const backend_urls = { "local": "http://localhost:3000" };
const BACKEND_URL = backend_urls[urlparams.get("backendtype")];

fetch(BACKEND_URL).then(async res => {
    Plotly.newPlot( graphDiv, [ await res.json() ]); 
})
