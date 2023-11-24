"use strict";

const highScore = {
  stockholm:    null,
  goteborg:     6168,
  malmo:        null,
  uppsala:      2416,
  vasteras:     1498,
  orebro:       null,
  london:       null,
  linkoping:     699,
  berlin:       null
}

const minCycle = 25;

let customIcon = {
 iconUrl:  "images/marker-icon.png",
 iconSize: [20,20]
};

let myIcon = L.icon(customIcon);

let iconOptions = {
 title:    "xxx",
 draggable: true,
 icon:      myIcon
}

let cfg = {
    radius:          0.005,
    maxOpacity:      .7,
    scaleRadius:     true,
    useLocalExtrema: true,
    latField:        'latitude',
    lngField:        'longitude',
    valueField:      'value'
  };

const generalData = {
    classicUnitData: { type: 'classic', co2PerUnitInGrams: 570, profitPerUnit: 0 },
    refillUnitData: { type: 'refill', co2PerUnitInGrams: 0, profitPerUnit: 130 },
    freestyle9100Data: {
      type: 'freestyle9100',
      leasingCostPerWeek: 1038,
      refillCapacityPerWeek: 438,
      staticCo2: 6330
    },
    freestyle3100Data: {
      type: 'freestyle3100',
      leasingCostPerWeek: 598,
      refillCapacityPerWeek: 70,
      staticCo2: 2110
    },
    locationTypes: {
      groceryStoreLarge: { type: 'Grocery-store-large', salesVolume: 373 },
      groceryStore: { type: 'Grocery-store', salesVolume: 121 },
      convenience: { type: 'Convenience', salesVolume: 15 },
      gasStation: { type: 'Gas-station', salesVolume: 24 },
      kiosk: { type: 'Kiosk', salesVolume: 3 }
    },
    competitionMapNames: [ 'stockholm', 'orebro', 'malmo', 'london', 'berlin', 's-sandbox' ],
    trainingMapNames: [ 'goteborg', 'uppsala', 'linkoping', 'vasteras', 'g-sandbox' ],
    co2PricePerKiloInSek: 1.06,
    willingnessToTravelInMeters: 200,
    constantExpDistributionFunction: 1.03,
    refillSalesFactor: 0.58,
    refillDistributionRate: 0.97,
    maxGroceryStoreLarge: 5,
    maxGroceryStore: 20,
    maxConvenience: 20,
    maxGasStation: 8,
    maxKiosk: 3
  };

  const iconSize = [30, 30];
  const icons ={
    'Gas-station':         L.icon({iconUrl: 'gas-station.png', iconSize: iconSize}), 
    'Kiosk':               L.icon({iconUrl: 'kiosk.png', iconSize: iconSize}), 
    'Grocery-store':       L.icon({iconUrl: 'grocery.png', iconSize: iconSize}),
    'Grocery-store-large': L.icon({iconUrl: 'supermarket.png', iconSize: iconSize}),
    'Convenience':         L.icon({iconUrl: 'convenience.png', iconSize: iconSize}),
    default: null
  };



function drawSolution(generalData, mapData, score, unused, options){
    $('#mapname').html(mapData.mapName);
    $('#score').html(score.gameScore.total);
    $('#relativescore').html((100*score.gameScore.total/highScore[mapData.mapName]).toFixed(2));
  

    let heatmapLayer = new HeatmapOverlay(cfg);
    let baseLayer = L.tileLayer( 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
    let map = new L.Map('map', {
      zoom: 4,
      layers: [baseLayer, heatmapLayer]
    }).fitBounds([
      L.latLng(mapData.border.latitudeMin, mapData.border.longitudeMin),
      L.latLng(mapData.border.latitudeMax, mapData.border.longitudeMax)
    ]);

  let circleType={
    color:       'red',
    fillColor:   'red',
    fillOpacity: 0.75,
    radius:      25
  };
  if(options.showHotspots){
    console.log('HEATMAP', options.showHotspots);
    let heatData = [];
    let marker = null;
    if(false){
      for(const [name, entry] of Object.entries(mapData.hotspots)){
        circleType.color = 'green'
        circleType.radius = entry.spread
        marker = L.circle([entry.latitude, entry.longitude], circleType).addTo(map);

        circleType.color = 'red'
        circleType.radius = generalData.willingnessToTravelInMeters; 
        marker = L.circle([entry.latitude, entry.longitude], circleType).addTo(map);
      }
    } else {
      let maxValue=-100000000000000000000000
      for(const [name, entry] of Object.entries(mapData.hotspots)){
        switch(options.showHotspots){
        case 'footfall':
          maxValue=Math.max(maxValue, entry.footfall);
          heatData.push({latitude: entry.latitude, longitude: entry.longitude, value: entry.footfall});
        break;
        case 'spread':
          maxValue=Math.max(maxValue, entry.spread);
          heatData.push({latitude: entry.latitude, longitude: entry.longitude, value: entry.spread});
        break;
        }
      }
      console.log('maxValue', maxValue);
      heatmapLayer.setData({max: maxValue, data: heatData});
    } 
  }

  for(const [name, entry] of Object.entries(mapData.locations)){
    console.log('DRAW', name);
    let tooltip = '';

    const neighbors = Object.keys(entry.neighbors || {}).length;
    const scoreEntry = score.locations[name] || entry;
    //{freestyle3100Count: 0, freestyle9100Count: 0, earnings: 0, revenue: 0, gramCo2Savings:0, salesVolume: 0};
    scoreEntry.salesVolume = scoreEntry.salesVolume!=null?scoreEntry.salesVolume:0;
    scoreEntry.freestyle9100Count = scoreEntry.freestyle9100Count!=null?scoreEntry.freestyle9100Count:0;
    scoreEntry.freestyle3100Count = scoreEntry.freestyle3100Count!=null?scoreEntry.freestyle3100Count:0;
    scoreEntry.revenue = scoreEntry.revenue!=null?scoreEntry.revenue:0;
    scoreEntry.earnings = scoreEntry.earnings!=null?scoreEntry.earnings:0;
    scoreEntry.total = scoreEntry.total!=null?scoreEntry.total:0;
    scoreEntry.gramCo2Savings = scoreEntry.gramCo2Savings!=null?scoreEntry.gramCo2Savings:0;
    //{freestyle3100Count: 0, freestyle9100Count: 0, earnings: 0, revenue: 0, gramCo2Savings:0, salesVolume: 0};
    const withRefill = (score.locations[name]!=null);

    if(entry.salesVolume< scoreEntry.salesVolume){
      console.log('SALES MOVED FROM NEIGHBORS', name, scoreEntry.salesVolume-entry.salesVolume);
    }

    switch(options.mode) {
      case 'score':
        circleType.radius = minCycle + Math.abs(scoreEntry.score/100);
        circleType.color = scoreEntry.score>0?'green':'red';
      break;
      case 'sales':
        circleType.radius = minCycle + Math.abs(Math.abs(scoreEntry.salesVolume));
        circleType.color = scoreEntry.salesVolume?'green':'red';
      break;
      case 'co2':
        circleType.radius = minCycle + Math.abs(Math.abs(scoreEntry.gramCo2Savings/100));
        circleType.color = scoreEntry.gramCo2Savings?'green':'red';
      break;
      case 'revenue':
        circleType.radius = minCycle + Math.abs(scoreEntry.revenue/100);
        circleType.color = scoreEntry.revenue>0?'green':'red';
      break;
      case 'earnings':
        circleType.radius = minCycle + Math.abs(scoreEntry.earnings/100);
        circleType.color = scoreEntry.earnings>0?'green':'red';
      break;
      case 'neighbors':
        circleType.radius = minCycle + (50 * neighbors);
        circleType.color = neighbors>0?'green':'red';
      break;
      case 'total':
        circleType.radius = minCycle + Math.abs(scoreEntry.total);
        circleType.color = scoreEntry.total>0?'green':'red';
      break;
      case 'units':
        circleType.radius = minCycle + 50 * (scoreEntry.freestyle3100Count + scoreEntry.freestyle9100Count);
        circleType.color = scoreEntry.freestyle9100Count>0?'red':(scoreEntry.freestyle3100Count>0?'orange':'blue');
      break;
      case 'distance':
        circleType.radius = generalData.willingnessToTravelInMeters; 
        circleType.color = (scoreEntry.freestyle3100Count + scoreEntry.freestyle9100Count)?'green':'red';
      break; 
    }

    if(withRefill) {
      circleType.fillColor = circleType.color;
    } else {
      circleType.fillColor = 'white';
    }

    let marker = null;
    if(options.mode == 'type'){
      const icon = icons[entry.locationType];
      if(icon){
        marker = L.marker([entry.latitude, entry.longitude], {icon: icon}).addTo(map);
      } else {
        marker = L.marker([entry.latitude, entry.longitude]).addTo(map);
      }
    } else {
      marker = L.circle([entry.latitude, entry.longitude], circleType).addTo(map);
    }

    tooltip += '<br/>F3100: ' + scoreEntry.freestyle3100Count;
    tooltip += '<br/>F9100: ' + scoreEntry.freestyle9100Count;
    const capacity = scoreEntry.freestyle3100Count * generalData.freestyle3100Data.refillCapacityPerWeek + scoreEntry.freestyle9100Count * generalData.freestyle9100Data.refillCapacityPerWeek;
    tooltip += '<br/>Refillcapacity: ' + capacity;
    tooltip += '<br/>Utilization: ' + (Math.round(100*entry.salesVolume/capacity)) + '%';
    tooltip += '<br/>CO2-saving: ' + scoreEntry.gramCo2Savings;
    tooltip += '<br/>Revenue: ' + scoreEntry.revenue;
    tooltip += '<br/>Earnings: ' + scoreEntry.earnings;
    tooltip += '<br/>Profitable: ' + (scoreEntry.isProfitable?'YES':'NO');
    tooltip += '<br/>Neighbors: ' + neighbors;
    tooltip += '<br/>Salesvolume: ' + entry.salesVolume;
    tooltip += '<br/>Refillvolume: ' + scoreEntry.salesVolume;
    tooltip += '<br/>Score: ' + Math.round(scoreEntry.total) + (withRefill?'':' no refill');
    marker.bindTooltip('<b>' + name + ' (' + entry.locationType + ')</b>' + tooltip);
  } 
}
  

$(function() {
  const solutionId = $.url.param('solution');
  const mode = $.url.param('mode');
  const showHotspots = $.url.param('showhotspots');

  console.dir('solutionId', solutionId, 'mode', mode, 'showHotspots', showHotspots);
 
  function showMap(mapData, score){
    console.log('showMap', mapData, score);
    let solution = {};
    let deleteLocations = {};

    var startTime = new Date();

    console.log(mapData.locations, Object.keys(mapData.locations).length);
    if(!mapData.locations || Object.keys(mapData.locations).length==0){
      console.log('NO LOCATIONS');
      mapData.locations = score.locations
      console.dir(mapData);
    }
    drawSolution(generalData, mapData, score, deleteLocations, {solutionId: solutionId, mode: mode, showHotspots: showHotspots});
    console.log(`GameScore: ${score.gameScore.total}`);
    console.log(mapData.mapName, (100*score.gameScore.total/highScore[mapData.mapName]).toFixed(2) + '%', highScore[mapData.mapName]);
  }

  fetch('../my_games/m' + solutionId + '.json')
  .then((response) => response.json())
  .then((mapData) => {
    fetch('../my_games/s' + solutionId + '.json')
    .then((response) => response.json())
    .then((solution) => {
       showMap(mapData, solution);
    })
  })
})
