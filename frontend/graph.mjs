const graphDiv = document.getElementById("graph");

const BACKEND_URL = "https://oa-backend.residualentropy.repl.co";

const FOOD_SAFETY_TEMP_C = 4;
const AVG_TIME = 10 * 60 * 1000;

function setHeader(s) {
  document.getElementById("header").innerHTML = s;
}

function setAvgHeader(s) {
  document.getElementById("avgheader").innerText = s;
}

async function drawPlot() {
  let temps = fetch(`${BACKEND_URL}/api/r/temps_recent?cacheb=${Math.random()}`);
  temps = await (await temps).json();
  let names = fetch(`${BACKEND_URL}/api/r/sensor_names`);
  names = await (await names).json();
  let traces = {
    "_foodsafety": {
      name: "Maximum Food-safe Temperature",
      x: [],
      y: [],
      type: 'scatter',
      line: {
        color: 'red',
        width: 5,
      },
    },
  };
  let ids = [];
  let total_sum = 0;
  let total_count = 0;
  for (const [id, name] of Object.entries(names.names)) {
    traces[id] = {
      name,
      x: [],
      y: [],
      type: 'scatter',
    };
    if (name === "Evaporator") {
      traces[id].line = {
        color: 'gray',
        dash: 'dot',
      };
    }
    ids.push(id);
  }
  let now = new Date();
  for (const temps_instance of temps.recent) {
    let x = new Date(temps_instance.unixts * 1000);
    for (const id of ids) {
      let y = temps_instance.readings[id];
      traces[id].x.push(x);
      traces[id].y.push(y);
      if (traces[id].name !== "Evaporator" && (now - x) < AVG_TIME) {
        total_sum += y;
        total_count += 1;
      }
    }
    traces["_foodsafety"].x.push(x);
    traces["_foodsafety"].y.push(FOOD_SAFETY_TEMP_C);
  }
  console.log(total_sum, total_count);
  let total_avg = total_sum / total_count;
  console.log("Total Average Temperature (inside fridge, degs C):", total_avg);
  let traces_without_evaporator = Object.values(traces);
  let evaporator_trace;
  for (let i = 0; i < traces_without_evaporator.length; i++) {
    if (traces_without_evaporator[i].name === "Evaporator") {
      evaporator_trace = traces_without_evaporator.splice(i, 1)[0];
      break;
    }
  }
  console.log(traces_without_evaporator);
  console.log(evaporator_trace);
  Plotly.newPlot('graph1', traces_without_evaporator, {
    title: 'Temperatures Inside My Minifridge (Real Time)',
    width: window.innerWidth,
    height: window.innerHeight * (1 / 2),
    yaxis: {
      title: {
        text: 'Temperature (°C)',
      },
    },
  });
  Plotly.newPlot('graph2', [traces["_foodsafety"], evaporator_trace], {
    title: 'Temperature Of Evaporator (Real Time)',
    width: window.innerWidth,
    height: window.innerHeight * (1 / 3),
    yaxis: {
      title: {
        text: 'Temperature (°C)',
      },
    },
  });
  setAvgHeader(`Average over last 10 minutes: ${total_avg.toFixed(2)}°C`);
  if (total_avg <= FOOD_SAFETY_TEMP_C) {
    setHeader("Is my fridge working? <i><span style=\"color:green;\">YES!</i>");
  } else if (total_avg < 0) {
    setHeader("Is my fridge working? <i><span style=\"color:blue;\">KINDA? IT'S A FREEZER NOW!</span><i>");
  } else {
    setHeader("Is my fridge working? <i><span style=\"color:red;\">NO!</span><i>");
  }
}

setInterval(drawPlot, 2000);
