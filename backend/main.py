
import json
import hashlib as h

import random as rv
import secrets as st
import string as s

def shuffle(p: str) -> str:
    char_list = list(p)
    st.SystemRandom().shuffle(char_list)
    return ''.join(char_list)

def hashFunction(data) -> str:
    # Random opaque identifier: do not hash untrusted input into logs or URLs.
    return st.token_hex(32)


# Do not load local secrets or invoke external paid APIs on module import.
def build_client():
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured; AI feature is optional")
    from openai import OpenAI
    return OpenAI(api_key=api_key)

question_types = {}
query = ""

def make_prompt(query: str):
    return ("""
    Respond to this prompt with a JSON object ONLY! No other output.
                    
    Consider the following query types with parameters:"""
    + str(question_types)
    + """
    The keys in the parameter list represent the paremeters, and the values of those keys
    represent the data types that those parameters are.
    
    Given the following query:"""
    +  query
    + """, identify which query type it is and what
        the relevant parameters are.

        Print the output as a JSON object of the following form:

        {
            "query_type": ....,
            "parameters": ....
        }

        If the query is empty or doesn't make sense, say that it is an unsupported query_type
    """)

def get_query_details(query: str) -> dict:
    response = build_client().completions.create(
        model = "gpt-3.5-turbo-instruct",
        prompt = make_prompt(query),
        max_tokens=1000
    )
    return json.loads(response.to_dict()['choices'][0]['text'])
if __name__ == "__main__":
    print("External AI calls are disabled by default. Configure OPENAI_API_KEY explicitly.")


