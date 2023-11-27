"use strict";

import { calculateScore, distanceBetweenPoint } from "./scoring.js";

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

  const iconSize = [30, 30];
  const icons ={
    'Gas-station':         L.icon({iconUrl: 'gas-station.png', iconSize: iconSize}), 
    'Kiosk':               L.icon({iconUrl: 'kiosk.png', iconSize: iconSize}), 
    'Grocery-store':       L.icon({iconUrl: 'grocery.png', iconSize: iconSize}),
    'Grocery-store-large': L.icon({iconUrl: 'supermarket.png', iconSize: iconSize}),
    'Convenience':         L.icon({iconUrl: 'convenience.png', iconSize: iconSize}),
    default: null
  };


  function calcNeighbors(generalData, mapEntity){
    let neighbors = {};
    Object.entries(mapEntity.locations).forEach(([locationKey, location]) => {
      let count = 1;
      neighbors[locationKey] = {neighbors: {}}
      Object.entries(mapEntity.locations).forEach(([locationSurroundingKey, locationSurrounding]) => {
        if(locationKey != locationSurroundingKey){
          let distance = distanceBetweenPoint(
            location.latitude, location.longitude, locationSurrounding.latitude, locationSurrounding.longitude
          );
          if(distance < generalData.willingnessToTravelInMeters){
            neighbors[locationKey].neighbors[locationSurroundingKey]= {distance: distance};
          }
        }
      });
    });
    return neighbors;
  }

let heatmapLayer = new HeatmapOverlay(cfg);
let baseLayer = L.tileLayer( 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
let map = new L.Map('map', {
  zoom: 4,
  layers: [baseLayer, heatmapLayer]
});

function drawSolution(generalData, mapEntity, neighbors, topScore, score, options){
    let highScore = topScore[mapEntity.mapName];
    $('#mapname').html(mapEntity.mapName);
    $('#score').html(score.gameScore.total);
    $('#highscore').html(highScore);
    $('#relativescore').html((100*score.gameScore.total/highScore).toFixed(2));
  

    
    map.fitBounds([
      L.latLng(mapEntity.border.latitudeMin, mapEntity.border.longitudeMin),
      L.latLng(mapEntity.border.latitudeMax, mapEntity.border.longitudeMax)
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
      for(const [name, entry] of Object.entries(mapEntity.hotspots)){
        circleType.color = 'green'
        circleType.radius = entry.spread
        marker = L.circle([entry.latitude, entry.longitude], circleType).addTo(map);

        circleType.color = 'red'
        circleType.radius = generalData.willingnessToTravelInMeters; 
        marker = L.circle([entry.latitude, entry.longitude], circleType).addTo(map);
      }
    } else {
      let maxValue=-100000000000000000000000
      for(const [name, entry] of Object.entries(mapEntity.hotspots)){
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

  for(const [locationKey, entry] of Object.entries(mapEntity.locations)){
    console.log('DRAW', locationKey);
    let tooltip = '';
    let neighborKeys = {}
    if(neighbors[locationKey]){
      neighborKeys = neighbors[locationKey].neighbors|| {}
    }

    const neighborCount = Object.keys(neighborKeys).length;
    const scoreEntry = score.locations[locationKey] || entry;
    //{freestyle3100Count: 0, freestyle9100Count: 0, earnings: 0, revenue: 0, gramCo2Savings:0, salesVolume: 0};
    scoreEntry.salesVolume = scoreEntry.salesVolume!=null?scoreEntry.salesVolume:0;
    scoreEntry.freestyle9100Count = scoreEntry.freestyle9100Count!=null?scoreEntry.freestyle9100Count:0;
    scoreEntry.freestyle3100Count = scoreEntry.freestyle3100Count!=null?scoreEntry.freestyle3100Count:0;
    scoreEntry.revenue = scoreEntry.revenue!=null?scoreEntry.revenue:0;
    scoreEntry.earnings = scoreEntry.earnings!=null?scoreEntry.earnings:0;
    scoreEntry.total = scoreEntry.total!=null?scoreEntry.total:0;
    scoreEntry.gramCo2Savings = scoreEntry.gramCo2Savings!=null?scoreEntry.gramCo2Savings:0;
    //{freestyle3100Count: 0, freestyle9100Count: 0, earnings: 0, revenue: 0, gramCo2Savings:0, salesVolume: 0};
    const withRefill = (score.locations[locationKey]!=null);

    if(entry.salesVolume< scoreEntry.salesVolume){
      console.log('SALES MOVED FROM NEIGHBORS', locationKey, scoreEntry.salesVolume-entry.salesVolume);
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
        circleType.radius = minCycle + (25 * neighborCount);
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
      if(options.mode=="distance") {
        L.circle([entry.latitude, entry.longitude], {radius: 5, color: "black"}).addTo(map);
      }
    }

    tooltip += '<br/>F3100: ' + scoreEntry.freestyle3100Count;
    tooltip += '<br/>F9100: ' + scoreEntry.freestyle9100Count;
    const capacity = scoreEntry.freestyle3100Count * generalData.freestyle3100Data.refillCapacityPerWeek + scoreEntry.freestyle9100Count * generalData.freestyle9100Data.refillCapacityPerWeek;
    tooltip += '<br/>Refillcapacity: ' + capacity;
    tooltip += '<br/>Utilization: ' + (Math.round(100*scoreEntry.salesVolume/capacity)) + '%';
    tooltip += '<br/>CO2-saving: ' + scoreEntry.gramCo2Savings;
    tooltip += '<br/>Revenue: ' + scoreEntry.revenue;
    tooltip += '<br/>Earnings: ' + scoreEntry.earnings;
    tooltip += '<br/>Profitable: ' + (scoreEntry.isProfitable?'YES':'NO');
    tooltip += '<br/>Neighbors: ' + neighborCount;
    tooltip += '<br/>Salesvolume: ' + entry.salesVolume;
    tooltip += '<br/>Refillvolume: ' + scoreEntry.salesVolume;
    tooltip += '<br/>Score: ' + Math.round(scoreEntry.total,3) + (withRefill?'':' no refill');
    marker.bindTooltip('<b>' + locationKey + ' (' + entry.locationType + ')</b>' + tooltip);
  } 
}
 
$(function() {
  const solutionId = $.url.param('solution');
  const mode = $.url.param('mode');
  const showHotspots = $.url.param('showhotspots');

  $("#mapId").selectmenu({change: function( event, data ) {
      drawNewSolution(data.item.value );
    }
});

  console.dir('solutionId', solutionId, 'mode', mode, 'showHotspots', showHotspots);
 
  function showMap(generalData, highScore, mapEntity, solution){
    console.log('showMap', generalData, mapEntity, solution);
    let neighbors = calcNeighbors(generalData, mapEntity)
    if(!mapEntity.locations || Object.keys(mapEntity.locations).length==0){
      console.log('NO LOCATIONS');
      mapEntity.locations = solution.locations
      console.dir(mapEntity);
    }
    $('#status').html('Scoring', mapEntity.mapName, '...');
    score = calculateScore(mapEntity.mapName, solution, mapEntity, generalData);
    $('#status').html('');
    drawSolution(generalData, mapEntity, neighbors, highScore, score, {solutionId: solutionId, mode: mode, showHotspots: showHotspots});
    console.log(`GameScore: ${score.gameScore.total}`);
    console.log(mapEntity.mapName, (100*score.gameScore.total/highScore[mapEntity.mapName]).toFixed(2) + '%', highScore[mapEntity.mapName]);
  }

  function drawNewSolution(solutionId){
    $.when(
      $.getJSON('../my_games/generalData.json'),
      $.getJSON('../my_games/top.json'),
      $.getJSON('../my_games/m' + solutionId + '.json'),
      $.getJSON('../my_games/s' + solutionId + '.json?dummy=' + Math.round(Math.random()*100000))
    ).done(function(result1, result2, result3, result4){
      showMap(result1[0], result2[0], result3[0], result4[0]);
    }).fail(function(result){
      console.log(result.status, result.statusText);
      $('#status').html(result.status);
      $('#text').html(result.statusText);
    });
  }
/*  
  $.when(
    $.getJSON('../my_games/generalData.json'),
    $.getJSON('../my_games/top.json'),
    $.getJSON('../my_games/m' + solutionId + '.json'),
    $.getJSON('../my_games/s' + solutionId + '.json?dummy=' + Math.round(Math.random()*100000))
  ).done(function(result1, result2, result3, result4){
    showMap(result1[0], result2[0], result3[0], result4[0]);
  }).fail(function(result){
    console.log(result.status, result.statusText);
    $('#status').html(result.status);
    $('#text').html(result.statusText);
  });
*/
});
