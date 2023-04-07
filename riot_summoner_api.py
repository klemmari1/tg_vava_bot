from riotwatcher import LolWatcher

import settings


def get_summoner_match_info(summoner_name: str, region: str = "euw1") -> list:
    watcher = LolWatcher(settings.RIOT_API_KEY)

    summoner_json: dict = watcher.summoner.by_name(region, summoner_name)

    matches = watcher.match.matchlist_by_puuid(region, summoner_json["puuid"])

    all_match_details = []
    for match in matches:
        match_detail = watcher.match.by_id(region, match)["info"]

        game_mode = match_detail["gameMode"]
        if game_mode != "CLASSIC":
            continue

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
                summoner_info["champion"] = row["championName"]
                summoner_info["win"] = row["win"]
                summoner_info["kills"] = row["kills"]
                summoner_info["deaths"] = row["deaths"]
                summoner_info["assists"] = row["assists"]
                summoner_info["totalDamageDealtToChampions"] = row[
                    "totalDamageDealtToChampions"
                ]
                summoner_info["turretTakedowns"] = row["turretTakedowns"]
                summoner_info["damageDealtToTurrets"] = row["damageDealtToTurrets"]
                summoner_info["goldEarned"] = row["goldEarned"]
                summoner_info["champLevel"] = row["champLevel"]
                summoner_info["totalMinionsKilled"] = row["totalMinionsKilled"]
                summoner_info["totalHealsOnTeammates"] = row["totalHealsOnTeammates"]
                summoner_info["totalHeal"] = row["totalHeal"]
                summoner_info["wardsKilled"] = row["wardsKilled"]
                summoner_info["wardsPlaced"] = row["wardsPlaced"]
                summoner_info["timePlayed"] = row["timePlayed"]
                summoner_info["lane"] = row["lane"]
                summoner_info["doubleKills"] = row["doubleKills"]
                summoner_info["tripleKills"] = row["tripleKills"]
                summoner_info["quadraKills"] = row["quadraKills"]
                summoner_info["pentaKills"] = row["pentaKills"]
                summoner_info["killingSprees"] = row["killingSprees"]
                summoner_info["dragonTakedowns"] = row["challenges"]["dragonTakedowns"]
                summoner_info["teamBaronKills"] = row["challenges"]["teamBaronKills"]
                summoner_info["teamElderDragonKills"] = row["challenges"][
                    "teamElderDragonKills"
                ]
                summoner_info["teamRiftHeraldKills"] = row["challenges"][
                    "teamRiftHeraldKills"
                ]
                summoner_info["soloKills"] = row["challenges"]["soloKills"]
                summoner_info["gameDuration"] = game_duration

            if summoner_info:
                match_info.append(summoner_info)

        all_match_details.append(match_info)

        if len(all_match_details) >= 5:
            break

    return all_match_details


if __name__ == "__main__":
    all_match_details = get_summoner_match_info("Vava")
    print(all_match_details)
