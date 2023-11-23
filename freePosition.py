from dataclasses import dataclass
import math
import pandas
import geopandas
from shapely.geometry import Polygon, LineString, Point

from pprint import pprint
from typing import Dict
import uuid
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
import numpy as np
from smallestenclosingcircle import make_circle

def nameMapping(solution):
    id = 0
    print('NAMEMAPPING')
    mappedSolution = {LK.locations: {}}
    for key in solution[LK.locations]:
        id +=1
        name = f"location{id}"
        # print ('MAPPING', key, name)
        mappedSolution[LK.locations][name] = solution[LK.locations][key]
    mappedSolution
    # print('SOLUTION')
    # pprint(mappedSolution)
    return mappedSolution

def numerical_stable_circle(points):
    pts = np.array(points)
    mean_pts = np.mean(pts, 0)
    # print('mean of points:', mean_pts)
    pts -= mean_pts  # translate towards origin
    result = make_circle(pts)
    # print('result without mean:', result)
    # print('result with mean:', (result[0] + mean_pts[0], result[1] + mean_pts[1], result[2]))
    return (result[0] + mean_pts[0], result[1] + mean_pts[1], result[2])


@dataclass
class SolutionLimits:
     name  = "name"
     start = "start"
     limit = "limit"

maxGroceryStoreLarge = 5
maxGroceryStore = 20
maxConvenience = 20
maxGasStation = 8
maxKiosk = 3
maxLocations = maxGroceryStoreLarge +maxGroceryStore + maxConvenience + maxGasStation + maxKiosk

solutionsLimits = [
    {"name": GK.groceryStoreLarge, "end":  5, "limit": maxGroceryStoreLarge, "freestyle9100Count": 2, "freestyle3100Count": 2},
    {"name": GK.groceryStore,      "end": 25, "limit": maxGroceryStore,      "freestyle9100Count": 2, "freestyle3100Count": 2},
    {"name": GK.convenience,       "end": 45, "limit": maxConvenience,       "freestyle9100Count": 2, "freestyle3100Count": 2},
    {"name": GK.gasStation,        "end": 53, "limit": maxGasStation,        "freestyle9100Count": 2, "freestyle3100Count": 2},
    {"name": GK.kiosk,             "end": 56, "limit": maxKiosk,             "freestyle9100Count": 2, "freestyle3100Count": 2}
]

def freePosition(generalData, mapEntity) -> int:
    hotspots = mapEntity[HK.hotspots]
    neighbors = {}
    maxFootfall = 0

    for idx1,hotspot1 in enumerate(hotspots):
        neighbors[idx1] = {
            CK.latitude: hotspot1[CK.latitude],
            CK.longitude: hotspot1[CK.longitude],
            "neighbors": {}, 
            LK.footfall: 0,
            HK.spread: 0
        }
        count = 1;
        optPosition = {}
        for idx2,hotspot2 in enumerate(hotspots):
            if idx1!=idx2:
                distance = distanceBetweenPoint(
                    hotspot1[CK.latitude],
                    hotspot1[CK.longitude],
                    hotspot2[CK.latitude],
                    hotspot2[CK.longitude],
                )
                if distance <= generalData[GK.willingnessToTravelInMeters]:   # distance >0.0 and hotspot1[HK.spread]:
#                   print (f"{idx1}: {hotspot1[HK.name]} - {idx2}: {hotspot2[HK.name]} {distance}");
                   neighbors[idx1]["neighbors"][idx2] = {"distance": distance}
                   count += 1

                if distance > generalData[GK.willingnessToTravelInMeters] and distance <=2 * generalData[GK.willingnessToTravelInMeters]:   # distance >0.0 and hotspot1[HK.spread]:
                    optPosition[idx2] = {"distance": distance}

                maxSpread = hotspot2[HK.spread]
                if distance <= maxSpread:
                    val = hotspot2[LK.footfall] * (1 - (distance / maxSpread))
                    neighbors[idx1][LK.footfall] += val / 10
                maxFootfall = max(maxFootfall, neighbors[idx1][LK.footfall])
        total = utils.calcTotal(generalData, 0, 0, False)
        neighbors[idx1][SK.total] = total
        neighbors[idx1][LK.salesVolume] = count
        neighbors[idx1]["optPosition"] = optPosition
        if count==1 and len(optPosition)==1:
            print ('in the middle', optPosition)

    setNeighbors(neighbors)
    # print('NEIGHBORS')
    # pprint(neighbors)
    print('NEW LOCATIONS')
    orderedLocations = sorted(neighbors, key=lambda x: (len(neighbors[x]["neighbors"]), neighbors[x][LK.footfall]), reverse=True)
    for loc in orderedLocations:
        print(loc, neighbors[loc][LK.footfall], len(neighbors[loc]["neighbors"]))

    newNeighbor = -1
    newNeighbors = {}
    for idx, entry in neighbors.items():
        if len(entry["optPosition"])==1 and len(entry["neighbors"])==0:
            for newId, newEntry in entry["optPosition"].items():
                print('NEW POSITION', newId, newEntry)
                newLocation = {
                    CK.latitude:  (neighbors[idx][CK.latitude] + neighbors[newId][CK.latitude])/2, 
                    CK.longitude: (neighbors[idx][CK.longitude] + neighbors[newId][CK.longitude])/2,
                    LK.footfall:  (neighbors[idx][LK.footfall] + neighbors[newId][LK.footfall])/2,
                    "neighbors": {
                        idx:  {"distance": newEntry["distance"]/2}, 
                        newId: {"distance": newEntry["distance"]/2}}
                }
                total = utils.calcTotal(generalData, 0, 0, False)
                newLocation[SK.total] = total
                newNeighbors[newNeighbor] = newLocation
                newNeighbor -=1
                print(newLocation)

    pprint(newNeighbors)
    neighbors.update(newNeighbors)

    print("MAXFOOTFALL", maxFootfall)
    if maxFootfall > 0:
        for idx, hotspot in enumerate(hotspots):
            loc = neighbors[idx]
            if loc[LK.footfall] > 0:
                loc[LK.footfallScale] = int(loc[LK.footfall] / maxFootfall * 10)
                if loc[LK.footfallScale] < 1:
                    loc[LK.footfallScale] = 1

    solution = {SK.mapName: mapEntity[SK.mapName], LK.locations: {}}
    solutionCount = 0
    locationType = 0;    

    # print("neighbors start")
    # pprint(neighbors)
    print("MAX-Loops", maxLocations)

    for i in range(0, maxLocations):
        if locationType >= len(solutionsLimits):
            break
        # sortedNeighbors = sorted(neighbors, key=lambda x: neighbors[x]["footfall"], reverse=True)
        sortedNeighbors = sorted(neighbors, key=lambda x: (len(neighbors[x]["neighbors"]), neighbors[x][LK.footfall]), reverse=True)
        for key in sortedNeighbors:
            print("first key", key, len(neighbors[key]["neighbors"]))
            type  = generalData[GK.locationTypes][
                    solutionsLimits[locationType]["name"]       # GK.groceryStoreLarge
                ][GK.type_]
            solutionCount +=1
            
            neighborCoords = [[hotspots[key][CK.longitude], hotspots[key][CK.latitude]]]
            
            for neighbor in neighbors[key]["neighbors"]:
            #     print("COORDS", key, neighbor)
                neighborCoords.append([hotspots[neighbor][CK.longitude], hotspots[neighbor][CK.latitude]])
            # pprint(neighborCoords)
            pprint(list(set(map(tuple,neighborCoords))))
            minCircle = numerical_stable_circle(neighborCoords)
            print("minCircle", neighborCoords[0], minCircle)


            print("add to solution", solutionCount, key, neighbors[key][LK.footfall], len(neighbors[key]), solutionsLimits[locationType]["name"])
            # newId = f"location{solutionCount}"
            solution[LK.locations][key] = {
                LK.f9100Count:   solutionsLimits[locationType][LK.f9100Count],
                LK.f3100Count:   solutionsLimits[locationType][LK.f3100Count],
                LK.locationType: type,
                CK.longitude:    neighbors[key][CK.longitude], # minCircle[0], # 
                CK.latitude:     neighbors[key][CK.latitude],  # minCircle[1], # 
                LK.salesVolume:  getSalesVolume(type, generalData)
            }
            # delete reference of all neigbors, do reduce neighbors#
            utils.deleteNeighbor(neighbors, key)
     
            # calc next solutiontype
            if solutionCount >= solutionsLimits[locationType]["end"]:
               locationType += 1
            if locationType >= len(solutionsLimits):
               break
            break
        # print(solution)
    # print("neighbors end")
    # pprint(neighbors)
    print("INITIAL SOLUTION")

    score = calculateScore(solution[SK.mapName], solution, mapEntity, generalData)
    print("INITIAL SCORE total:", score[SK.gameScore][SK.total])
    # adopt salesCapacity
    for location in score[LK.locations]:
        loc = solution[LK.locations][location]
        sales = score[LK.locations][location][LK.salesVolume];
        loc[LK.f9100Count] = math.trunc(sales/generalData[GK.f9100Data][GK.refillCapacityPerWeek])
        loc[LK.f3100Count] = math.ceil((sales - loc[LK.f9100Count] * generalData[GK.f9100Data][GK.refillCapacityPerWeek]) / generalData[GK.f3100Data][GK.refillCapacityPerWeek])
        if loc[LK.f9100Count] < 2 and loc[LK.f3100Count]* generalData[GK.f3100Data][GK.leasingCostPerWeek]>generalData[GK.f9100Data][GK.leasingCostPerWeek]:
            loc[LK.f9100Count] +=1
            loc[LK.f3100Count] = 0

    score = calculateScore(solution[SK.mapName], solution, mapEntity, generalData)
    savedTotal = score[SK.gameScore][SK.total]

    solution = utils.optimizeSolution(generalData, mapEntity, neighbors, solution);

    # DATA PATCH
    solution[LK.locations].pop(891)
    # solution[LK.locations].pop(31)

    return solution
