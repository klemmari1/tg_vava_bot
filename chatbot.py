# This code is Apache 2 licensed:
# https://www.apache.org/licenses/LICENSE-2.0
import json
import re

import openai
import requests
import wikipedia

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
        result, total_tokens = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result, total_tokens

    def execute(self):
        completion = openai.ChatCompletion.create(model="gpt-4", messages=self.messages)
        # Uncomment this to print out token usage each time, e.g.
        # {"completion_tokens": 86, "prompt_tokens": 26, "total_tokens": 112}
        # print(completion.usage)
        return completion.choices[0].message.content, completion.usage["total_tokens"]


prompt = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.
You must answer in the same language as the original question is presented.
You can use the pre-trained data to answer as well if you already know the answer or if there are no results from the Actions.
Do not tell what systems you are using to fetch the information.

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
        result, total_tokens = bot(next_prompt)

        if logger:
            logger.info(result)
        else:
            print(result)

        actions = [action_re.match(a) for a in result.split("\n") if action_re.match(a)]
        if actions:
            # There is an action to run
            action, action_input = actions[0].groups()
            if action not in known_actions:
                raise Exception("Unknown action: {}: {}".format(action, action_input))

            if logger:
                logger.info(" -- running {} {}".format(action, action_input))
            else:
                print(" -- running {} {}".format(action, action_input))

            observation = known_actions[action](action_input)

            if logger:
                logger.info(" -- sending observation...")
            else:
                print(" -- sending observation...")

            next_prompt = "Observation: {}".format(observation)
        else:
            return result, total_tokens


def wikipedia_query(q: str) -> str:
    results = wikipedia.search(q)
    if len(results) > 0:
        return wikipedia.summary(results[0])
    else:
        return "No search results"


def lolwiki(q: str) -> str:
    url = f"https://league-of-legends-champions.p.rapidapi.com/champions/en-us/{q}"

    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": "league-of-legends-champions.p.rapidapi.com",
    }

    response = requests.request("GET", url, headers=headers)

    assert response.status_code == 200

    response_json = json.loads(response.text)
    data_dragon_json = json.loads(response_json["champion"][0]["data_dragon_json"])

    champion_summary = {
        "lore": data_dragon_json["lore"],
        "abilities": data_dragon_json["spells"],
    }

    return str(champion_summary)


def calculate(q: str) -> str:
    return eval(q)


known_actions = {
    "calculate": calculate,
    "wikipedia": wikipedia_query,
    "lolwiki": lolwiki,
}
