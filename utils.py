from datetime import datetime, timedelta
from pprint import pprint
import math
import copy
import signal
import random

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
    getSalesVolume
)


maxF9100 = 2
maxF3100 = 2
def deleteNeighbor(neighbors, key):
    print("delete location in neighbors", key)
    for neighbor in neighbors[key]["neighbors"]:
        # print("delete in", neighbor)
        neighbors[neighbor]["neighbors"] = {} # .pop(key)
    neighbors[key]["neighbors"]={}
    neighbors[key][LK.footfall]=0

def calcTotals(generalData, neighbors, solution):
    locations = 0
    footfall = 0
    revenue = 0
    leasingCost = 0
    earnings = 0
    co2Savings = 0
    total = 0
    for location in solution[LK.locations]:
        locations +=1;
        footfall += neighbors[location][SK.total][LK.footfall]/(1+len(neighbors[location]["neighbors"]))
        revenue += neighbors[location][SK.total][LK.revenue]
        leasingCost +=  neighbors[location][SK.total][LK.leasingCost]
        earnings += neighbors[location][SK.total][SK.earnings]
        co2Savings += neighbors[location][SK.total][SK.co2Savings]
        total += neighbors[location][SK.total][SK.total]
    return({SK.total: total, LK.locations: locations, LK.footfall: footfall, LK.revenue: revenue, LK.leasingCost: leasingCost, SK.earnings: earnings, SK.co2Savings: co2Savings})

stopProcessing = False

def signalHandler(sig, frame):
    global stopProcessing
    stopProcessing = True
    print('got Strg-C')
    signal.signal(signal.SIGINT, signalHandler)

def printRemaining(startTimestamp, loops, totalLoops):
    if(totalLoops!=loops):
        todo = round((datetime.now()-startTimestamp)/timedelta(seconds=1)*loops/(totalLoops-loops))
        print('todo', loops, 'of', totalLoops, todo, 'seconds', (datetime.now() + timedelta(seconds=todo)))

def adoptSalesCapacities(generalData, solution, locations):
    modified = False
    for locationKey, location in locations.items():
        if location[LK.salesCapacity]< location[LK.salesVolume]:
            # print('location needs more capacity', locationKey, location[LK.salesCapacity], location[LK.salesVolume])
            total = calcTotal(generalData, location[LK.salesVolume], location[LK.footfall], False)
            if(total[SK.total]>location[SK.total]):
                print('increase capacity of', locationKey, 'capacity', location[LK.salesCapacity], '<',  location[LK.salesVolume])
                units = calcUnitsFromSalesVolume(generalData, location[LK.salesVolume])
                solution[LK.locations][locationKey][LK.f9100Count] = units[LK.f9100Count]
                solution[LK.locations][locationKey][LK.f3100Count] = units[LK.f3100Count]
                solution[LK.locations][locationKey][LK.salesCapacity] = units[LK.salesCapacity]
                print(location)
                modified = True
    return modified 

def calcUnitsFromSalesVolume(generalData, salesVolume):
        # f9100 to fullfil salesVolume, max 5 of each
    salesVolume = round(salesVolume * generalData[GK.refillSalesFactor])
    f9100Count = min(maxF9100, math.floor(salesVolume/generalData[GK.f9100Data][GK.refillCapacityPerWeek]));
        # rest salesvolume with f3100
    restSalesVolume = max(0, salesVolume - f9100Count* generalData[GK.f9100Data][GK.refillCapacityPerWeek]);
    f3100Count = min(maxF3100, math.ceil(restSalesVolume/generalData[GK.f3100Data][GK.refillCapacityPerWeek]));
    # print('calcUnitsFromSalesVolume', f9100Count, f3100Count, salesVolume, restSalesVolume)
        # perhaps f9100 can replace several f3100 because leasing costs are lower
    while (f9100Count <maxF9100) and (f3100Count * generalData[GK.f3100Data][GK.leasingCostPerWeek]>generalData[GK.f9100Data][GK.leasingCostPerWeek]):
            # one more f9100
        f9100Count +=1
            # calc f3100 for the rest of the salesvolume
        restSalesVolume = max(0, salesVolume - generalData[GK.f9100Data][GK.refillCapacityPerWeek]);
        f3100Count = math.ceil(restSalesVolume/generalData[GK.f3100Data][GK.refillCapacityPerWeek]);
  
    f3100Count = min(maxF3100,f3100Count)
    salesCapacity = f3100Count* generalData[GK.f3100Data][GK.refillCapacityPerWeek] + f9100Count* generalData[GK.f9100Data][GK.refillCapacityPerWeek]
    return({LK.f3100Count: f3100Count, 
            LK.f9100Count: f9100Count, 
            LK.salesCapacity: salesCapacity,
            LK.salesVolume: salesVolume});


def withoutNeighbors(generalData, mapEntity, neighbors, locations, solution, score, options):
    print("withoutNeighbors")
    # Locations with no neighbors and earning>=0, keep these always
 
    loops = len(locations)
    locationCount = loops
    restLocations = []
    noNeighbors = {}
    totalLoops = loops
    startTimestamp = datetime.now()
    breakTimestamp = startTimestamp + options["maxLoopDuration"]
    stopProcessing = False
    for locationKey in locations:
        if datetime.now()>breakTimestamp: 
           restLocations.append(locationKey)
           continue
        if stopProcessing:
            break
        printRemaining(startTimestamp, loops, totalLoops)
        loops -=1
        if len(neighbors[locationKey]["neighbors"])==0: # no neighbors
            if neighbors[locationKey][SK.total][SK.total]>=0:
                print('always keep profit no neighbors', locationKey)
                units = calcUnitsFromSalesVolume(generalData, mapEntity[LK.locations][locationKey][LK.salesVolume])
                solution[LK.locations][locationKey] = {LK.f9100Count: units[LK.f9100Count], LK.f3100Count: units[LK.f3100Count]}
            else:   # try in last step to increase total
                print('no profit, no neighbors', locationKey)
                noNeighbors[locationKey] = locationKey
        else:
            restLocations.append(locationKey)

    locations = restLocations        
    print('remaining locations 1 (no neighbors profit):', len(locations) ,'of', locationCount)
    print('noNeighbor-list', len(noNeighbors))

    return ([score, restLocations, solution])

def with1Neighbors(generalData, mapEntity, neighbors, locations, solution, score, options):
    # Locations with one neighbors
 
    loops = len(locations)
    locationCount = loops
    totalLoops = loops
    startTimestamp = datetime.now()
    breakTimestamp = startTimestamp + options["maxLoopDuration"]
    stopProcessing = False

    restLocations = []
    noNeighbors = {}

    for locationKey in locations:
        foundNeighbor = None
        if datetime.now()>breakTimestamp: 
           restLocations.append(locationKey)
           continue
        if stopProcessing:
            break
        printRemaining(startTimestamp, loops, totalLoops)
        loops -=1
        if len(neighbors[locationKey]["neighbors"])==1: # 1 neighbors
            neighborKey = list(neighbors[locationKey]["neighbors"].keys())[0]
                # neighbor has higher salesvolume, so take them
            if len(neighbors[neighborKey]["neighbors"])>1:
                print("1 neighbor neighbors", locationKey, neighborKey)
                foundNeighbor = neighborKey
            else: # neighbor has one neighbor too, take the one with more salesVolume
                if mapEntity[LK.locations][locationKey][LK.salesVolume] < mapEntity[LK.locations][neighborKey][LK.salesVolume]:
                    print("1 neighbor sales", locationKey, neighborKey)
                    foundNeighbor = neighborKey
                else:
                            # neighbor has same salesvolume, take the one with the lower name
                   if mapEntity[LK.locations][locationKey][LK.salesVolume] == mapEntity[LK.locations][neighborKey][LK.salesVolume] and neighborKey>locationKey:
                        print("1 neighbor name", locationKey, neighborKey)
                        foundNeighbor = neighborKey
        if foundNeighbor!=None:
            units = calcUnitsFromSalesVolume(generalData, mapEntity[LK.locations][neighborKey][LK.salesVolume])
            solution[LK.locations][neighborKey] = {LK.f9100Count: units[LK.f9100Count], LK.f3100Count: units[LK.f3100Count]}
            deleteNeighbor(neighbors, foundNeighbor)
        else:
            restLocations.append(locationKey)


    locations = restLocations        
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)

    print('remaining locations 1 (no neighbors profit):', len(locations) ,'of', locationCount)
    print('noNeighbor-list', len(noNeighbors))
    return ([score, restLocations, solution])


def optimizeSolution(generalData, mapEntity, allNeighbors, solution):
    global stopProcessing
    score = None
    neighbors = allNeighbors.copy();
    locationCount = len(solution[LK.locations])
    options = {"maxLoops": 1000, "maxLoopDuration": timedelta(minutes=30)}

    # catch strg-C
    signal.signal(signal.SIGINT, signalHandler)

    locations = list(mapEntity[LK.locations].keys())
    [score, locations, solution] = withoutNeighbors(generalData, mapEntity, neighbors, locations, solution, score, options)

    [score, locations, solution] = with1Neighbors(generalData, mapEntity, neighbors, locations, solution, score, options)
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    return solution

    # calculate initial Score
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    bestScore = score
    print("OPTIMIZE-SOLUTION: score", bestScore[SK.gameScore][SK.total], datetime.now().strftime("%H:%M:%S"))
    pprint(score[SK.gameScore])
    totals = calcTotals(generalData, neighbors, solution)
    pprint(totals)
    sol = copy.deepcopy(solution[LK.locations])
    # print('SOL')
    # pprint(sol)
    # print ("NEIGHBORS")
    # pprint(neighbors)
    for locationKey, neighbor in neighbors.items():
        print(locationKey, 
            neighbor[SK.total][SK.total], 
            neighbor[SK.total][LK.footfall], 
            neighbor[SK.total][LK.salesVolume], 
            neighbor[SK.total][LK.salesCapacity],
            neighbor[SK.total][LK.leasingCost],
            neighbor[SK.total][LK.revenue],
            neighbor[SK.total][SK.co2Savings],
            neighbor[SK.total][SK.earnings],
            len(neighbor["neighbors"])
            # , (neighbor[SK.total][LK.revenue] - neighbor[SK.total][LK.leasingCost]  + neighbor[SK.total][SK.co2Savings]/1000 * generalData[GK.co2PricePerKiloInSek]) * (1+ neighbor[SK.total][LK.footfall])
            )
    for locationKey, neighbor in neighbors.items():
       print(locationKey, calcTotal(generalData, neighbor[SK.total][LK.salesVolume], neighbor[SK.total][LK.footfall], True)[SK.total])         

    locations = list(solution[LK.locations].keys())
    [score, locations, noNeighbors, solution] = withoutNoNeighbors(generalData, mapEntity, neighbors, locations, solution, score, options)

    # keep all location with full capacity
    restLocations = []
    stopProcessing = False
    for locationKey in locations:
        if neighbors[locationKey][SK.total][LK.salesVolume] == neighbors[locationKey][SK.total][LK.salesCapacity]: # optimal use
            print('always keep full', locationKey)
        else:   # try in last step to increase total
            restLocations.append(locationKey)
                
    locations = restLocations
    loops = len(locations)
    print('remaining locations 2 (full):', loops ,'of', locationCount)
    # pprint(solution)

    # locations with one neighbor could move to neighbor, revenue will not change, earnings will increase, footfall?
    restLocations = []
    startTimestamp = datetime.now()
    breakTimestamp = startTimestamp + maxLoopDuration
    totalLoops=loops
    stopProcessing = False
    for locationKey in locations:
        if datetime.now()>breakTimestamp: 
           restLocations.append(location)
           continue
        if stopProcessing:
             break
        printRemaining(startTimestamp, loops, totalLoops)
        loops -=1
        location = sol[locationKey]
        # print("neighbors", locationKey, len(neighbors[locationKey]["neighbors"]))
        if len(neighbors[locationKey]["neighbors"])==1:
            neighborKey = list(neighbors[locationKey]["neighbors"].keys())[0]
            print('1NEIGHBOR', locationKey, neighborKey, len(neighbors[neighborKey]["neighbors"]), 
                neighbors[locationKey][SK.total][LK.salesVolume], neighbors[neighborKey][SK.total][LK.salesVolume],
                neighbors[locationKey][SK.total][LK.footfall]> neighbors[neighborKey][SK.total][LK.footfall]/(1+len(neighbors[neighborKey]["neighbors"])))
            # print("1 neighbor", locationKey, neighborKey, mapEntity[LK.locations][locationKey][LK.footfall], mapEntity[LK.locations][neighborKey][LK.footfall])
            # print(neighbors[locationKey])
            if mapEntity[LK.locations][locationKey][LK.footfall] < mapEntity[LK.locations][neighborKey][LK.footfall] and neighbors[locationKey][SK.total][SK.total]<0:    
               print("remove neighbor", locationKey)
               solution[LK.locations].pop(locationKey)
               deleteNeighbor(neighbors, locationKey)
            else:
                restLocations.append(locationKey)
        else:
            restLocations.append(locationKey)
    
    locations = restLocations
    loops = len(locations) 
    print('remaining locations 3:', loops ,'of', locationCount)
    pprint(score[SK.gameScore])
    # pprint(solution)

    # try to remove location by location with negative total lowest first
    locations = sorted(locations, key=lambda x: (score[LK.locations][x][SK.total], score[LK.locations][x][LK.footfall]))
    print('SORTEDSCORE')
    # pprint(sortedScore)
    # print(sortedScore)
    restLocations = []
    loops = len(locations) 
    totalLoops = loops
    startTimestamp = datetime.now()
    breakTimestamp = startTimestamp + maxLoopDuration
    stopProcessing = False
    for location in locations:
        if datetime.now()>breakTimestamp or totalLoops>maxLoops: 
           restLocations.append(location)
           continue
        if stopProcessing:
             break
        printRemaining(startTimestamp, loops, totalLoops)
        loops -=1
        locationTotal = score[LK.locations][location][SK.total]
        if locationTotal<0: # or True:
            savedLocation = solution[LK.locations].pop(location)
            score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, bestScore)
            # print('delete', location, locationTotal, bestTotal, score[SK.gameScore][SK.total], score[SK.gameScore][SK.totalFootfall])
            if(bestScore[SK.gameScore][SK.total] <score[SK.gameScore][SK.total]):
                bestScore = score
                deleteNeighbor(neighbors, location)
                print('scored location removed', location)
            else:
                print('scored location NOT removed', location)
                restLocations.append(location)
                solution[LK.locations][location] = savedLocation
        else:
            restLocations.append(location)
    # print('NEIGHBORS')
    # pprint(neighbors)            

    locations = restLocations
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    print('remaining locations 4 negative total:', len(locations) ,'of', locationCount)
    pprint(score[SK.gameScore])
    # pprint(solution)

    
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    bestScore = score

        # try to remove location with most neighbors    
    restLocations = []
    startTimestamp = datetime.now()
    breakTimestamp = startTimestamp + maxLoopDuration
    locations = sorted(locations, key=lambda x: (len(neighbors[x]["neighbors"])))
    loops = len(locations) 
    totalLoops = loops
    stopProcessing = False
    for location in locations:
        if datetime.now()>breakTimestamp: 
           restLocations.append(location)
           continue
        if stopProcessing:
            break
        printRemaining(startTimestamp, loops, totalLoops)
        loops -=1
        locationTotal = score[LK.locations][location][SK.total]
        if locationTotal>0:
            savedLocation = solution[LK.locations].pop(location)
            score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, bestScore)
            # print('delete', location, locationTotal, bestTotal, score[SK.gameScore][SK.total], score[SK.gameScore][SK.totalFootfall])
            if(bestScore[SK.gameScore][SK.total] <score[SK.gameScore][SK.total]):
                bestScore = score
                deleteNeighbor(neighbors, location)
                print('location removed', location, bestScore[SK.gameScore][SK.total])
            else:
                print('location NOT removed', location, bestScore[SK.gameScore][SK.total])
                solution[LK.locations][location] = savedLocation
                restLocations.append(location)

    locations = restLocations
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    print('remaining locations 5:', len(locations) ,'of', locationCount)
    pprint(score[SK.gameScore])

    print ('negative locations:', len(noNeighbors))
    # pprint(noNeighbors)
    sortedNeighbors = sorted(noNeighbors, key=lambda x: (neighbors[x][SK.total][SK.total], neighbors[x][SK.total][LK.footfall]), reverse=True)
    loops = len(sortedNeighbors)
    totalLoops = loops
    startTimestamp = datetime.now()
    breakTimestamp = startTimestamp + maxLoopDuration
    stopProcessing = False
    for locationKey in sortedNeighbors:
        if datetime.now()>breakTimestamp: 
           restLocations.append(location)
           continue
        if stopProcessing:
            break
        printRemaining(startTimestamp, loops, totalLoops)
        loops -=1
        bestScore = score
        score = tryAddLocation(generalData, mapEntity, solution, locationKey, noNeighbors[locationKey], score)

    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    print('remaining locations 6:', len(locations) ,'of', locationCount)
    pprint(score[SK.gameScore])

    solution = tryRandomLocation(generalData, mapEntity, solution, score, 2000, datetime.now() + timedelta(minutes=5))
    score = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    return solution

def tryRandomLocation(generalData, mapEntity, solution, score, loops, endTimestamp):
    locations = list(solution[LK.locations].keys())
    global stopProcessing
    stopProcessing = False
    for i in range(loops):
        if stopProcessing:
            break
        if datetime.now()>endTimestamp:
            return(solution)
        locationsCount = len(locations)
        randomPos = random.randrange(locationsCount)
        locationKey = locations[randomPos]
        print('try random', i, locationKey)
        savedLocation = solution[LK.locations].pop(locationKey)
        newScore = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
        if(newScore[SK.gameScore][SK.total]<score[SK.gameScore][SK.total]): # lower score, undo delete
            solution[LK.locations][locationKey] = savedLocation
            print('location NOT removed', locationKey, score[SK.gameScore][SK.total])
        else:
            print('location removed', locationKey, newScore[SK.gameScore][SK.total])
            score = newScore
            locations.pop(randomPos)
    return solution

def tryAddLocation(generalData, mapEntity, solution, locationKey, location, score):
    print('tryAddLocation', locationKey)
    solution[LK.locations][locationKey] = location
    # pprint(solution)
    total = score[SK.gameScore][SK.total]
    newScore = scoreAdopt(solution[SK.mapName], solution, mapEntity, generalData, score)
    newTotal = newScore[SK.gameScore][SK.total]
    if newTotal>total: 
        print('higher score', locationKey, newTotal, total, 'footfall', newScore[SK.gameScore][SK.totalFootfall], score[SK.gameScore][SK.totalFootfall])
        print('location removed', location, newTotal)
    else: # result is not better, remove it again
        print('lower score', locationKey, newTotal, total, 'footfall', newScore[SK.gameScore][SK.totalFootfall], score[SK.gameScore][SK.totalFootfall])
        print('location NOT removed', location, newTotal)
        newScore = score
        solution[LK.locations].pop(locationKey)

    return(newScore)

def scoreAdopt(mapName, solution, mapEntity, generalData, score):
    newScore = calculateScore(mapName, solution, mapEntity, generalData)
    if(score != None and newScore[SK.gameScore][SK.total]>score[SK.gameScore][SK.total]):
        if adoptSalesCapacities(generalData, solution, score[LK.locations]):
            print('recalculateScore')
            newScore = calculateScore(mapName, solution, mapEntity, generalData)
    return newScore

def calcTotal(generalData, salesVolume, footfall, distribute):
    # salesVolume = round(salesVolume * generalData[GK.refillSalesFactor])
    units = calcUnitsFromSalesVolume(generalData, salesVolume)
    f9100Count=0
    f3100Count=0

    if(distribute==False):
        f3100Count = units[LK.f3100Count]
        f9100Count = units[LK.f9100Count]
    salesCapacity = f3100Count * generalData[GK.f3100Data][GK.refillCapacityPerWeek] + f9100Count * generalData[GK.f9100Data][GK.refillCapacityPerWeek]

    leasingCost = (f3100Count * generalData[GK.f3100Data][GK.leasingCostPerWeek] 
                  + f9100Count * generalData[GK.f9100Data][GK.leasingCostPerWeek])
    revenue = salesVolume * generalData[GK.refillUnitData][GK.profitPerUnit]

    earnings = revenue - leasingCost

    co2Savings = (
            salesVolume
            * (
                generalData[GK.classicUnitData][GK.co2PerUnitInGrams]
                - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
            )
            - f3100Count * generalData[GK.f3100Data][GK.staticCo2]
            - f9100Count * generalData[GK.f9100Data][GK.staticCo2]
        )
    
    total = co2Savings/1000 * generalData[GK.co2PricePerKiloInSek] + earnings/1000

    return {LK.salesCapacity: salesCapacity, LK.salesVolume: salesVolume, LK.footfall: footfall/1000, SK.total: total, SK.earnings: earnings, LK.revenue: revenue, LK.leasingCost: leasingCost, SK.co2Savings: co2Savings/1000, LK.f3100Count: f3100Count, LK.f9100Count: f9100Count}