from riotwatcher import LolWatcher
import settings


def get_summoner_match_info(summoner_name: str, region: str = "euw1") -> str:
    watcher = LolWatcher(settings.RIOT_API_KEY)

    summoner_json: dict = watcher.summoner.by_name(region, summoner_name)

    matches = watcher.match.matchlist_by_puuid(region, summoner_json['puuid'])

    all_match_details = []
    for match in matches:
        match_detail = watcher.match.by_id(region, match)["info"]

        game_mode = match_detail["gameMode"]
        if game_mode != "CLASSIC":
            continue

        game_id = match_detail["gameId"]
        match_info = []
        for row in match_detail['participants']:
            summoner_info = {}
            summoner_info['gameId'] = game_id
            summoner_info['teamId'] = row['teamId']
            summoner_info['summonerName'] = row['summonerName']
            summoner_info['champion'] = row['championName']
            summoner_info['win'] = row['win']
            summoner_info['kills'] = row['kills']
            summoner_info['deaths'] = row['deaths']
            summoner_info['assists'] = row['assists']
            summoner_info['totalDamageDealt'] = row['totalDamageDealt']
            summoner_info['goldEarned'] = row['goldEarned']
            summoner_info['champLevel'] = row['champLevel']
            summoner_info['totalMinionsKilled'] = row['totalMinionsKilled']
            match_info.append(summoner_info)

        all_match_details.append(match_info)

        if len(all_match_details) >= 3:
            break

    return str(all_match_details)

if __name__ == "__main__":
    get_summoner_match_info("Vava")
