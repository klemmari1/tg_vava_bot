import riotwatcher
from riotwatcher import LolWatcher

import settings


def get_summoner_match_info(summoner_name: str, region: str = "euw1") -> list:
    watcher = LolWatcher(settings.RIOT_API_KEY)

    try:
        summoner_json: dict = watcher.summoner.by_name(region, summoner_name)

        matches = watcher.match.matchlist_by_puuid(
            region, summoner_json["puuid"], type="ranked"
        )
    except riotwatcher.ApiError as e:
        print(str(e))
        return "APIError when querying Riot API"

    all_match_details = []
    for match in matches:
        match_detail = watcher.match.by_id(region, match)["info"]

        game_id = match_detail["gameId"]
        game_duration = match_detail["gameDuration"]
        match_info = []
        for row in match_detail["participants"]:
            summoner_info = {}
            game_summoner_name = row["summonerName"]
            if game_summoner_name == summoner_name:
                summoner_info["gameId"] = game_id
                summoner_info["teamId"] = row["teamId"]
                summoner_info["summonerName"] = game_summoner_name
                summoner_info["championName"] = row["championName"]
                summoner_info["teamPosition"] = row["teamPosition"]
                summoner_info["role"] = row["role"]
                summoner_info["win"] = row["win"]
                summoner_info["teamEarlySurrendered"] = row["teamEarlySurrendered"]
                summoner_info["kills"] = row["kills"]
                summoner_info["deaths"] = row["deaths"]
                summoner_info["assists"] = row["assists"]
                summoner_info["totalDamageDealtToChampions"] = row[
                    "totalDamageDealtToChampions"
                ]
                summoner_info["turretTakedowns"] = row["turretTakedowns"]
                summoner_info["damageDealtToTurrets"] = row["damageDealtToTurrets"]
                summoner_info["damageDealtToObjectives"] = row["damageDealtToObjectives"]
                summoner_info["goldEarned"] = row["goldEarned"]
                summoner_info["champLevel"] = row["champLevel"]
                summoner_info["totalMinionsKilled"] = row["totalMinionsKilled"]
                summoner_info["totalHealsOnTeammates"] = row["totalHealsOnTeammates"]
                summoner_info["totalHeal"] = row["totalHeal"]
                summoner_info["wardsKilled"] = row["wardsKilled"]
                summoner_info["wardsPlaced"] = row["wardsPlaced"]
                summoner_info["timePlayed"] = row["timePlayed"]
                summoner_info["largestMultiKill"] = row["largestMultiKill"]
                summoner_info["largestKillingSpree"] = row["largestKillingSpree"]
                summoner_info["dragonTakedowns"] = row["challenges"]["dragonTakedowns"]
                summoner_info["teamBaronKills"] = row["challenges"]["teamBaronKills"]
                summoner_info["teamElderDragonKills"] = row["challenges"][
                    "teamElderDragonKills"
                ]
                summoner_info["teamRiftHeraldKills"] = row["challenges"][
                    "teamRiftHeraldKills"
                ]
                summoner_info["soloKills"] = row["challenges"]["soloKills"]
                summoner_info["epicMonsterSteals"] = row["challenges"][
                    "epicMonsterSteals"
                ]
                summoner_info["gameDuration"] = game_duration

            if summoner_info:
                match_info.append(summoner_info)

        all_match_details.append(match_info)

        if len(all_match_details) >= 5:
            break

    return all_match_details


if __name__ == "__main__":
    details = get_summoner_match_info("Thebausffs")
    print(details)
