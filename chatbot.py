# This code is Apache 2 licensed:
# https://www.apache.org/licenses/LICENSE-2.0
import json
import re
import traceback

import openai
import requests
import wikipedia
from openai import error

import riot_summoner_api
import settings

openai.api_key = settings.OPENAI_API_KEY


class ChatBot:
    def __init__(self, system=""):
        self.system = system
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4", messages=self.messages
            )
        except error.RateLimitError:
            traceback.print_exc()
            return "OpenAI Rate Limit Error", 0
        except error.InvalidRequestError:
            traceback.print_exc()
            return "Token limit reached", 0
        except error.APIError as e:
            print(str(e))
            return "OpenAI returned APIError"
        # Uncomment this to print out token usage each time, e.g.
        # {"completion_tokens": 86, "prompt_tokens": 26, "total_tokens": 112}
        # print(completion.usage)
        return completion.choices[0].message.content


prompt = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.
You must answer in the same language as the original question is presented.
You can use the pre-trained data to answer as well if you already know the answer or if there are no results from the Actions.
Do not tell what systems you are using to fetch the information.

Very important:
Do not write out the "Thought", "Question", "Answer" or "PAUSE" steps in the answer.

Your available actions are:

calculate:
e.g. calculate: 4 * 7 / 3
Runs a calculation and returns the number - uses Python so be sure to use floating point syntax if necessary

wikipedia:
e.g. wikipedia: Django
Returns a summary from searching Wikipedia

lolwiki:
e.g. lolwiki: Milio
Search LoLWiki for information about the video game League of Legends

riotapi:
e.g. riotapi: Vava euw1
Search Riot API for summoner match history and information on recent performance
Takes the summoner name and region as parameters

Always look things up on Wikipedia if you have the opportunity to do so.

Example session:

Question: What is the capital of France?
Thought: I should look up France on Wikipedia
Action: wikipedia: France
PAUSE

You will be called again with this:

Observation: France is a country. The capital is Paris.

You then output:

The capital of France is Paris

Example session 2:

Question: Mikä puolue voitti suomen eduskuntavaalit 2023?
Thought: Etsin eduskuntavaalien tulokset Wikipediasta
Action: wikipedia: Suomen eduskuntavaalit 2023
PAUSE

You will be called again with this:

Observation: Suomen 39. eduskuntavaalit järjestettiin sunnuntaina 2. huhtikuuta 2023, ja niissä valittiin kansanedustajat eduskuntaan vaalikaudelle 2023-2027. Oppositiopuolue kokoomus voitti vaalit saamalla 48 kansanedustajapaikkaa 20,8 % kannatuksella.

You then output:

Suomen eduskuntavaalit 2023 voitti Kokoomus (KOK).
""".strip()


action_re = re.compile("^Action: (\w+): (.*)$")


def query(
    question,
    bot=ChatBot(prompt),
    logger=None,
    max_turns=5,
) -> str:
    i = 0
    next_prompt = question
    while i < max_turns:
        i += 1
        result = bot(next_prompt)

        if logger:
            logger.info(result)
        else:
            print(result)

        actions = [action_re.match(a) for a in result.split("\n") if action_re.match(a)]
        if actions:
            # There is an action to run
            action, action_input = actions[0].groups()
            if action not in known_actions:
                raise Exception(f"Unknown action: {action}: {action_input}")

            if logger:
                logger.info(f" -- running {action} {action_input}")
            else:
                print(f" -- running {action} {action_input}")

            observation = known_actions[action](action_input)

            if logger:
                logger.info(" -- sending observation...")
            else:
                print(" -- sending observation...")

            next_prompt = f"Observation: {observation}"
        else:
            return result


def wikipedia_query(q: str) -> str:
    results = wikipedia.search(q)
    if len(results) > 0 and all([w in results[0] for w in q.split(" ")]):
        return wikipedia.summary(results[0])
    else:
        return "No search results"


def lolwiki(q: str) -> str:
    url = f"https://league-of-legends-champions.p.rapidapi.com/champions/en-us/{q}"

    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": "league-of-legends-champions.p.rapidapi.com",
    }

    response = requests.request("GET", url, headers=headers, timeout=30)

    assert response.status_code == 200

    response_json = json.loads(response.text)
    data_dragon_json = json.loads(response_json["champion"][0]["data_dragon_json"])

    champion_summary = {
        "lore": data_dragon_json["lore"],
        "abilities": data_dragon_json["spells"],
    }

    return str(champion_summary)


def riotapi(q: str) -> str:
    q_split = q.split(" ")
    summoner_name = q_split[0]
    region = q_split[1]
    return str(riot_summoner_api.get_summoner_match_info(summoner_name, region))


def calculate(q: str) -> str:
    return eval(q)


known_actions = {
    "calculate": calculate,
    "wikipedia": wikipedia_query,
    "lolwiki": lolwiki,
    "riotapi": riotapi,
}
