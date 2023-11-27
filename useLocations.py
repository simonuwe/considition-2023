from numba import njit

import math
from datetime import datetime
from pprint import pprint
from typing import Dict

from dataclasses import dataclass
from data_keys import (
    LocationKeys as LK,
    CoordinateKeys as CK,
    GeneralKeys as GK,
    ScoringKeys as SK,
    HotspotKeys as HK,
    MapNames as MN,
    MapKeys as MK,
)
from scoring import (
    calculateScore,
    distanceBetweenPoint,
    getSalesVolume,
    setNeighbors
)

import utils


def calcNeighbors(generalData, locations):
    neighbors = {}
    print('CALC-NEIGHBORS', datetime.now().strftime("%H:%M:%S"))
    for locationKey1, location1 in locations.items():
        neighbors[locationKey1] = {"neighbors": {}, "distributeSalesTo": 0, SK.total: 0}
        count = 1;
        for locationKey2, location2 in locations.items():
            # print(locationKey1, locationKey2)
            if location1!=location2:
                distance = distanceBetweenPoint(
                    location1[CK.latitude],
                    location1[CK.longitude],
                    location2[CK.latitude],
                    location2[CK.longitude],
                )
                if distance < generalData[GK.willingnessToTravelInMeters]:   # distance >0.0 and hotspot1[HK.spread]:
#                   print (f"{idx1}: {hotspot1[HK.name]} - {idx2}: {hotspot2[HK.name]} {distance}");
                    neighbors[locationKey1]["neighbors"][locationKey2] = {"distance": distance, "distributeSalesTo": 0} 
                    count += 1

        total = utils.calcTotal(generalData, location1[LK.salesVolume], round(location1[LK.footfall]* generalData[GK.refillSalesFactor]), False)
        neighbors[locationKey1][SK.total] = total

    return neighbors


def calcInitialSolution(generalData, mapData, neighbors):
    solution = { };
        # calc initial solution, which uses as many units as required to fullfill salesVolume
    print('CALC-INITIAL', datetime.now().strftime("%H:%M:%S"))
    for locationKey, location in mapData[LK.locations].items():
        salesVolume = location[LK.salesVolume] * generalData[GK.refillSalesFactor];
        units = utils.calcUnitsFromSalesVolume(generalData, salesVolume);
        maxUnits = units
        if len(neighbors[locationKey]["neighbors"])>0: # there are neighbors, calc max volume moved from them
            total = 1;
            for key, neighbor in neighbors[locationKey]["neighbors"].items():
                total += neighbor["distributeSalesTo"];
            additionalSales =0;
            for key, neighbor in neighbors[locationKey]["neighbors"].items():
                additionalSales += mapData[LK.locations][key][LK.salesVolume] *(neighbor["distributeSalesTo"]/total)
 
            if additionalSales>0:
                maxUnits = utils.calcUnitsFromSalesVolume(generalData, salesVolume+additionalSales);
                if units!=maxUnits:
                    print("MAXUNITS", units, maxUnits)
        if units[LK.f3100Count] + units[LK.f9100Count]>=0:
            solution[locationKey] = units;
 
    return {SK.mapName: mapData[SK.mapName], LK.locations: solution}

def useLocations(generalData, mapEntity):
    locations = mapEntity[LK.locations]
    starttime =  datetime.now()
    print('START', starttime.strftime("%H:%M:%S"))  
    print('LOCATIONS:', len(locations))
    solution = {SK.mapName: mapEntity[SK.mapName],
                LK.locations: {}
            }
    neighbors = calcNeighbors(generalData, locations)
    # pprint(neighbors)
    # save neighbors to speedup calculateScore
    setNeighbors(neighbors)

    # pprint(locations);

    # solution = calcInitialSolution(generalData, mapEntity, neighbors)
    # pprint(solution)

    solution = utils.optimizeSolution(generalData, mapEntity, neighbors, solution);
    
    totalFootfall = 0
    totalEarnings = 0
    totalCo2Savings = 0
    totalRevenue = 0
    totalSalesvolume = 0
    totalTotal = 0
    for locationKey, location in solution[LK.locations].items():
        total = utils.calcTotal(generalData, round(mapEntity[LK.locations][locationKey][LK.salesVolume]* generalData[GK.refillSalesFactor]), mapEntity[LK.locations][locationKey][LK.footfall], False)
        print(locationKey, total)
        totalFootfall += total[LK.footfall]
        totalEarnings += total[SK.earnings]
        totalCo2Savings += total[SK.co2Savings]
        totalRevenue += total[LK.revenue]
        totalSalesvolume += total[LK.salesVolume]
        totalTotal += total[SK.total]
    print('totalTotal', totalTotal, 'totalFootfall', totalFootfall, 'totalSalesvolume', totalSalesvolume, 'totalEarnings', totalEarnings/1000, 'totalRevenue', totalRevenue/1000, 'totalCo2', totalCo2Savings)
    

    # Data-patches
    # solution[LK.locations]["location2"][LK.f3100Count]=0
    # solution[LK.locations]["location2"][LK.f9100Count]=1


    endtime = datetime.now()
    print('FINISH', endtime.strftime("%H:%M:%S"), "DURATION", (endtime-starttime).total_seconds())
    # print("SOLUTION:")
    # pprint(solution)
    return solution