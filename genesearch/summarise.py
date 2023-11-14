import openai
import logging


def call_openai_chat_api(prompt, model="gpt-3.5-turbo"):
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return completion.choices[0].message.content


def divide_and_conquer_cgpt(paragraphs, gene, max_para=100):
    summaries = paragraphs

    while len(summaries) > 1:
        paragraphs = summaries
        summaries = []
        i = 0
        for p in paragraphs:
            gene_mentioned = gene.lower() in p.lower()
            response_text = ""
            has_appended = False

            if i >= 2 and not gene_mentioned:
                continue
            if i > max_para: continue
            # if not gene_mentioned: continue

            # Define your prompt (message)
            prompt = f'Please summarise the following paragraph in less than 200 words: "{p}".'
            if gene_mentioned:
                prompt += (
                    f" Focus on the description of the gene {gene} in the paragraph."
                )

            # Call the OpenAI Chat API
            response_text = call_openai_chat_api(prompt)

            if i % 2 == 1:
                summaries.append(prev + " " + response_text)
                has_appended = True
            else:
                prev = response_text

            i += 1

            logging.info(f"Summarising paragraph: {i}")

        if not has_appended:
            summaries[-1] = summaries[-1] + " " + response_text

    prompt = f'Please summarise the description of gene {gene} in the following paragraph: "{summaries[0]}".'

    # Call the OpenAI Chat API
    response_text = call_openai_chat_api(prompt)

    logging.info("Final paper summary:")
    logging.info(response_text)

    return response_text


def is_species(text, species):
    prompt = f'Does this paragraph focus on the species {species}? "'

    prompt += text

    prompt += '" Only answer with the words "Yes" or "No" and nothing else'

    # Call the OpenAI Chat API
    response_text = call_openai_chat_api(prompt)
    rtlower = response_text.lower()
    print(response_text)

    if "no" in rtlower:
        return False
    elif "yes" in rtlower:
        return True
    else:
        print("Did not answer with yes or no!")
        sys.exit(1)

    return None

def call_cluster_llm_api(json4api)->dict|None:
    """
    :param json4api:
    {
        "query": query,
        "texts": texts if isinstance(texts, list) else [texts],
        "temperature": temperature,
        "max_length": max_length,
        "min_length": min_length,
        "do_sample": do_sample
    }
    :return:
    {"text": text,
     "summary": text_summary,
    "score": get_similarity_score(text_summary)}
    """
    import requests
    import os
    # Call the summariser API
    api_url = os.getenv('CLUSTER_API_URL')
    response = requests.post(
        url=f"{api_url}/summarise",
        headers=['accept: application/json', 'Content-Type: application/json'],
        json=json4api
    )

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        return response.json()
    else:
        logging.error(f"Request failed with status code {response.status_code}")
        return None


def text_process_cluster_LLM(
        texts:str|list,
        query:str,
        temperature:float=0.2,
        max_length:int=150,
        min_length:int=100,
        do_sample:bool=None,
        similarity_threshold:float=0.5
):
    import sys
    response_json = call_cluster_llm_api({
        "query": query,
        "texts": texts if isinstance(texts, list) else [texts],
        "temperature": temperature,
        "max_length": max_length,
        "min_length": min_length,
        "do_sample": do_sample
    })

    relevant_summaries = [text_sum_dict["summary"] for text_sum_dict in response_json if text_sum_dict["score"] >= similarity_threshold]

    if len(relevant_summaries) > 1:
        logging.info("Merging paper summaries")
        final_summary = call_cluster_llm_api(
            {
                "query": query,
                "texts": [' '.join(relevant_summaries)],
                "temperature": temperature,
                "max_length": max_length,
                "min_length": min_length,
                "do_sample": do_sample
            }
        )

    elif len(relevant_summaries) == 1:
        logging.info("Only a single paper has been summarised.")
        final_summary = relevant_summaries[0]
    else:
        logging.warning("No relevant paper summaries found!")
        sys.exit(1)

    print(final_summary)
    return final_summary


def text_process_OpenAI(texts, gene, species, max_para):
    import sys
    # split into chuncks and recursively summarise using GPT-3
    paper_summaries = []
    for paper in texts:
        paper_summaries.append(divide_and_conquer_cgpt(paper, gene, max_para))

    relevant_summaries = []
    for summary in paper_summaries:
        if is_species(summary, species):
            relevant_summaries.append(summary)

    if len(relevant_summaries) > 1:
        logging.info("Merging paper summaries")
        final_summary = divide_and_conquer_cgpt(relevant_summaries, gene, len(relevant_summaries))
    elif len(relevant_summaries) == 1:
        logging.info("Only a single paper has been summarised.")
        final_summary = relevant_summaries[0]
    else:
        logging.warning("No relevant paper summaries found!")
        sys.exit(1)

    print(final_summary)