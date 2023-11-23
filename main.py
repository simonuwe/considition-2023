import os
import json
from scoring import calculateScore
from api import getGeneralData, getMapData, submit
from data_keys import (
    MapNames as MN,
    LocationKeys as LK,
    ScoringKeys as SK,
    HotspotKeys as HK,
    GeneralKeys as GK,
    CoordinateKeys as CK,
)
from dotenv import load_dotenv
from freePosition import (freePosition,
                         nameMapping)
from useLocations import useLocations

load_dotenv()
apiKey = os.environ["apiKey"]
game_folder = "my_games"


def main():
    if not os.path.exists("my_games"):
        print(f"Creating folder {game_folder}")
        os.makedirs(game_folder)

    try:
        apiKey = os.environ["apiKey"]
    except Exception as e:
        raise SystemExit("Did you forget to create a .env file with the apiKey?")

    # User selct a map name
    print(f"1: {MN.stockholm}")
    print(f"2: {MN.goteborg}")
    print(f"3: {MN.malmo}")
    print(f"4: {MN.uppsala}")
    print(f"5: {MN.vasteras}")
    print(f"6: {MN.orebro}")
    print(f"7: {MN.london}")
    print(f"8: {MN.berlin}")
    print(f"9: {MN.linkoping}")
    print(f"10: {MN.sSandbox}")
    print(f"11: {MN.gSandbox}")
    print(f"12: {MN.gSandbox} local")
    option_ = input("Select the map you wish to play: ")

    mapName = None
    match option_:
        case "1":
            mapName = MN.stockholm
        case "2":
            mapName = MN.goteborg
        case "3":
            mapName = MN.malmo
        case "4":
            mapName = MN.uppsala
        case "5":
            mapName = MN.vasteras
        case "6":
            mapName = MN.orebro
        case "7":
            mapName = MN.london
        case "8":
            mapName = MN.berlin
        case "9":
            mapName = MN.linkoping
        case "10":
            mapName = MN.sSandbox
        case "11":
            mapName = MN.gSandbox
        case "12":
            mapName = MN.gSandbox
        case _:
            print("Invalid choice.")

    with open(f"{game_folder}/top.json", 'r') as f:
        topScores = json.load(f)

    if mapName or option_=='12':
        ##Get map data from Considition endpoint
        if option_ != "12":
            mapEntity = getMapData(mapName, apiKey)
            ##Get non map specific data from Considition endpoint
            generalData = getGeneralData()

            with open(f"{game_folder}/m{option_}.json", "w", encoding="utf8") as f:
                json.dump(mapEntity, f, indent=4)
            with open(f"{game_folder}/generalData.json", "w", encoding="utf8") as f:
                json.dump(generalData, f, indent=4)
        else:
            with open(f"{game_folder}/m11.json", 'r') as f:
                mapEntity = json.load(f)
            with open(f"{game_folder}/generalData.json", 'r') as f:
                generalData = json.load(f)
            print(generalData);

        if mapEntity and generalData:
            # ------------------------------------------------------------
            # ----------------Player Algorithm goes here------------------
            if int(option_) <= 9:
                solution = useLocations(generalData, mapEntity);
            else:
                solution = freePosition(generalData, mapEntity);

            # ----------------End of player code--------------------------
            # ------------------------------------------------------------

            # Score solution locally
            score = calculateScore(mapName, solution, mapEntity, generalData)
            if int(option_) > 9:
                solution = nameMapping(solution)
            print(f"Score: {score[SK.gameScore]}")
            try:
                print(f"       {round(100*(score[SK.gameScore][SK.total]/topScores[score[SK.mapName]]),2)}%")
            except:
                print("unknown competition", SK.mapName)
            id_ = score[SK.gameId]
            print(f"Storing game with id {id_}.")
            print(f"Enter {id_} into visualization.ipynb for local vizualization ")

            with open(f"{game_folder}/s{option_}.json", "w", encoding="utf8") as f:
                json.dump(score, f, indent=4)

            # Store solution locally for visualization
            with open(f"{game_folder}/{id_}.json", "w", encoding="utf8") as f:
                json.dump(score, f, indent=4)
            # quit()
            # Submit and and get score from Considition app
            print(f"Submitting solution to Considtion 2023 \n")
 
            scoredSolution = submit(mapName, solution, apiKey)
            if scoredSolution:
                print("Successfully submitted game")
                print(f"id: {scoredSolution[SK.gameId]}")
                print(f"Score: {scoredSolution[SK.gameScore]}")

if __name__ == "__main__":
    main()
