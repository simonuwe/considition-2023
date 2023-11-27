export const SandboxMaps = ["g-sandbox", "s-sandbox"]

export const calculateScore = (mapName, solution, mapData, generalData) => {
  const scoredSolution = {
    mapName: mapName,
    teamId: '',
    teamName: '',
    locations: {},
    totalRevenue: 0,
    totalLeasingCost: 0,
    totalFreestyle3100Count: 0,
    totalFreestyle9100Count: 0,
    totalFootfall: 0,
    gameScore: {
      kgCo2Savings: 0,
      earnings: 0,
      total: 0,
      totalFootfall: 0
    },
  };
  if(!SandboxMaps.includes(mapName)){
    let locationListNoRefillStation = {};
    for(const [key, value] of Object.entries(mapData.locations)){ 
      if (solution.locations[key]) {
        const temp = {
          locationName: value.locationName,
          locationType: value.locationType,
          latitude: value.latitude,
          longitude: value.longitude,
          footfall: value.footfall,
          footfallScale: value.footfallScale,
          freestyle3100Count: solution.locations[key].freestyle3100Count,
          freestyle9100Count: solution.locations[key].freestyle9100Count,
       
          salesVolume: value.salesVolume * generalData.refillSalesFactor,
       
          salesCapacity: solution.locations[key].freestyle3100Count * generalData.freestyle3100Data.refillCapacityPerWeek +
              solution.locations[key].freestyle9100Count * generalData.freestyle9100Data.refillCapacityPerWeek,
       
          leasingCost: solution.locations[key].freestyle3100Count * generalData.freestyle3100Data.leasingCostPerWeek +
              solution.locations[key].freestyle9100Count * generalData.freestyle9100Data.leasingCostPerWeek
        };

        scoredSolution.locations[key] = temp;
        if(scoredSolution.locations[key].salesCapacity <= 0){
          throw Error("Sales capacity needs to be greater than 0")
        }
      } else {
        locationListNoRefillStation[key] = {
            locationName: value.locationName,
            locationType: value.locationType,
            latitude: value.latitude,
            longitude: value.longitude,
            salesVolume: value.salesVolume * generalData.refillSalesFactor
        };
      }
    }
    if(Object.keys(scoredSolution.locations).length == 0){
      throw Error("Locations in solution needs to be greater than 0")
    }

    scoredSolution.locations = getDistributeSales(scoredSolution.locations, locationListNoRefillStation, generalData);
  } else {
    scoredSolution.locations = initiateSandboxLocations(scoredSolution.locations, generalData, solution);
    scoredSolution.locations = calculateFootfall(scoredSolution.locations, mapData);
  }

  scoredSolution.locations = divideFootfall(scoredSolution.locations, generalData);

  for(const [key, value] of Object.entries(scoredSolution.locations)){
    value.salesVolume = Math.round(value.salesVolume);
    if(value.footfall <= 0 && SandboxMaps.includes(mapName)){
      value.salesVolume = 0;
    }

    let sales = value.salesVolume;
    if(value.salesCapacity < value.salesVolume){
      sales = value.salesCapacity;
    }

    value.gramCo2Savings = sales * (generalData.classicUnitData.co2PerUnitInGrams - generalData.refillUnitData.co2PerUnitInGrams)
      - value.freestyle3100Count * generalData.freestyle3100Data.staticCo2
      - value.freestyle9100Count * generalData.freestyle9100Data.staticCo2;
    scoredSolution.gameScore.kgCo2Savings += value.gramCo2Savings / 1000;

    if(value.gramCo2Savings > 0){
      value.isCo2Saving = true;
    }

    value.revenue = sales * generalData.refillUnitData.profitPerUnit;
    scoredSolution.totalRevenue += value.revenue;
    value.earnings = value.revenue - value.leasingCost;
    if(value.earnings > 0){
      value.isProfitable = true;
    }

    value.total = (value.gramCo2Savings/1000 * generalData.co2PricePerKiloInSek + value.earnings/1000);


    scoredSolution.totalLeasingCost += value.leasingCost;
    scoredSolution.totalFreestyle3100Count += value.freestyle3100Count;
    scoredSolution.totalFreestyle9100Count += value.freestyle9100Count;
    scoredSolution.gameScore.totalFootfall += value.footfall / 1000;
  }
  
  scoredSolution.totalRevenue = +scoredSolution.totalRevenue.toFixed(2)
  scoredSolution.gameScore.kgCo2Savings = +scoredSolution.gameScore.kgCo2Savings.toFixed(2);
  scoredSolution.gameScore.totalFootfall = +scoredSolution.gameScore.totalFootfall.toFixed(4);

  scoredSolution.gameScore.earnings = (scoredSolution.totalRevenue - scoredSolution.totalLeasingCost) / 1000;

  scoredSolution.gameScore.total = +((scoredSolution.gameScore.kgCo2Savings * generalData.co2PricePerKiloInSek + scoredSolution.gameScore.earnings) * (1 + scoredSolution.gameScore.totalFootfall)).toFixed(2);
  
  return scoredSolution;
};

export const initiateSandboxLocations = (locations, generalData, request) => {
  Object.entries(request.locations).forEach(([locationKey, location]) => {
    let sv = getSalesVolume(location.locationType, generalData);
    let scoredSolution = {
      longitude: location.longitude,
      latitude: location.latitude,
      freestyle3100Count: location.freestyle3100Count,
      freestyle9100Count: location.freestyle9100Count,
      locationType: location.LocationType,
      footfall: 0,
      footfallScale: 0,
      gramCo2Savings: 0,
      locationName: locationKey,
      salesVolume: sv,
      salesCapacity: request.locations[locationKey].freestyle3100Count * generalData.freestyle3100Data.refillCapacityPerWeek +
            request.locations[locationKey].freestyle9100Count * generalData.freestyle9100Data.refillCapacityPerWeek,
      leasingCost: request.locations[locationKey].freestyle3100Count * generalData.freestyle3100Data.leasingCostPerWeek +
            request.locations[locationKey].freestyle9100Count * generalData.freestyle9100Data.leasingCostPerWeek,
        
    }
    locations[locationKey] = scoredSolution;
  });
  Object.entries(locations).forEach(([locationKey, location]) => {
    let count = 1;
    Object.entries(locations).forEach(([locationSurroundingKey, locationSurrounding]) => {
      if(locationKey != locationSurroundingKey){
        let distance = distanceBetweenPoint(
          location.latitude, location.longitude, locationSurrounding.latitude, locationSurrounding.longitude
        );
        if(distance < generalData.willingnessToTravelInMeters){
          count++;
        } 
      }
    });
    location.salesVolume = location.salesVolume / count;
  });
  return locations;
};

export const divideFootfall = (locations, generalData) => {
  Object.entries(locations).forEach(([locationKey, location]) => {
    let count = 1;
    Object.entries(locations).forEach(([locationSurroundingKey, locationSurrounding]) => {
      if(locationKey != locationSurroundingKey){
        let distance = distanceBetweenPoint(
          location.latitude, location.longitude, locationSurrounding.latitude, locationSurrounding.longitude
        );
        if(distance < generalData.willingnessToTravelInMeters){
          count++;
        } 
      }
    });
    location.footfall = location.footfall / count;
  });
  return locations;
};

export const sandboxValidation = (inMapName, request, mapData) => {
  let countGroceryStoreLarge = 0;
  let countGroceryStore = 0;
  let countConvenience = 0;
  let countGasStation = 0;
  let countKiosk = 0;
  const maxGroceryStoreLarge = 5;
  const maxGroceryStore = 20;
  const maxConvenience = 20;
  const maxGasStation = 8;
  const maxKiosk = 3;
  const totalStores = maxGroceryStoreLarge + maxGroceryStore + maxConvenience + maxGasStation + maxKiosk;
  let mapName = inMapName.toLowerCase();
  let returnValue = null;
  Object.entries(request.locations).forEach(([locationKey, location]) => {
    let loc_num = locationKey.substring(8);
    if(!loc_num || loc_num.trim() === ''){
      returnValue = "Nothing followed location in the locationName";
    }
    var n = parseInt(loc_num, 10);
    if (isNaN(n)) {
      returnValue = numberErrorMsg + ' ' + loc_num + ' is not a number';
    }
    if (n <= 0 || n > totalStores)
    {
        returnValue =  "is not within the constraints";
    }
    if (mapData.border.latitudeMin > location.latitude || mapData.border.latitudeMax < location.latitude)
    {
        returnValue = `Latitude is missing or out of bounds for location: ${locationKey}`;
    }
    if (mapData.border.longitudeMin > location.longitude || mapData.border.longitudeMax < location.longitude)
    {
      returnValue = `Longitude is missing or out of bounds for location: ${locationKey}`;
    }
    if(location.locationType == ""){
      returnValue = "locationType is missing for location";
    }
    else if(location.locationType == "Grocery-store-large"){
      countGroceryStoreLarge += 1;
    }
    else if(location.locationType == "Grocery-store"){
      countGroceryStore += 1;
    }
    else if(location.locationType == "Convenience"){
      countConvenience += 1;
    }
    else if(location.locationType == "Gas-station"){
      countGasStation += 1;
    }
    else if(location.locationType == "Kiosk"){
      countKiosk += 1;
    }
    else{
      returnValue =  "not valid (check GetGeneralGameData for correct values) for location";
    }
    if (countGroceryStoreLarge > maxGroceryStoreLarge || countGroceryStore > maxGroceryStore ||
      countConvenience > maxConvenience || countGasStation > maxGasStation ||
      countKiosk > maxKiosk)
    {
        returnValue = "Number of allowed locations exceeded for locationType";
    }
  });
  return returnValue;
}

export const distanceBetweenPoint = (latitude1, longitude1, latitude2, longitude2) =>
{
    let r = 6371e3;
    let latRadian1 = latitude1 * Math.PI / 180;
    let latRadian2 = latitude2 * Math.PI / 180;

    let latDelta = (latitude2 - latitude1) * Math.PI / 180;
    let longDelta = (longitude2 - longitude1) * Math.PI / 180;

    let a = Math.sin(latDelta / 2) * Math.sin(latDelta / 2) +
        Math.cos(latRadian1) * Math.cos(latRadian2) *
        Math.sin(longDelta / 2) * Math.sin(longDelta / 2);

    let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    let distance = Math.round(r * c, 0);
    return distance;
}

const calculateFootfall = (locations, mapData) => {
  let maxFootfall = 0;
  for(const [key, value] of Object.entries(locations)){
    for(let i = 0; i < mapData.hotspots.length; i++){
      let hotspot = mapData.hotspots[i];
      let distanceInMeters = distanceBetweenPoint(hotspot.latitude, hotspot.longitude, value.latitude, value.longitude);
      let maxSpead = hotspot.spread;
      if(distanceInMeters <= maxSpead){
        let val = hotspot.footfall * (1 - distanceInMeters / maxSpead);
        value.footfall += val / 10;
      }
    }
    if(maxFootfall < value.footfall){
      maxFootfall = value.footfall;
    }
  }
  if(maxFootfall > 0){
    for(const [key, value] of Object.entries(locations)){
      if(value.footfall > 0){
        value.footfallScale = Math.round(value.footfall / maxFootfall * 10);
        if(value.footfallScale == 0){
          value.footfallScale = 1;
        }
      }
    }
  }
  return locations;
}

const getSalesVolume = (locationType, generalData) => {
  let returnValue = 0;
  Object.entries(generalData.locationTypes).forEach(([key, value]) => {
    if(locationType == value.type){
      returnValue = value.salesVolume;
    }
  });
  return returnValue;
}

const getDistributeSales = (xwith, without, generalData) => {
  Object.entries(without).forEach(([wihoutKey, withoutValue]) => {
    let distributeSalesTo = {};
    Object.entries(xwith).forEach(([xwithKey, xwithValue]) => {
      let distance = distanceBetweenPoint(withoutValue.latitude, withoutValue.longitude, xwithValue.latitude, xwithValue.longitude);
      if(distance < generalData.willingnessToTravelInMeters){
        distributeSalesTo[xwithValue.locationName] = distance;
      }
    });

    let total = 0;
    if(Object.keys(distributeSalesTo).length > 0){
      Object.entries(distributeSalesTo).forEach(([key, value]) => {
        distributeSalesTo[key] = Math.pow(generalData.constantExpDistributionFunction, generalData.willingnessToTravelInMeters - value) - 1;
        total += distributeSalesTo[key];
      });
      Object.entries(distributeSalesTo).forEach(([key, value]) => {generalData
        xwith[key].salesVolume += distributeSalesTo[key] / total *
          generalData.refillDistributionRate * withoutValue.salesVolume;
      });
    }
  });
  return xwith;
}