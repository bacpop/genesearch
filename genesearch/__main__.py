from .summarise import text_process_OpenAI, text_process_cluster_LLM, write_summary
from .search import *
import yaml
import importlib
from importlib.metadata import version
import sys
import os
import argparse
import logging
import openai


def get_options(args):

    description = 'genesearch: A tool to summarise the literature for a particluar gene in a species.'

    parser = argparse.ArgumentParser(description=description,
                                     prog='genesearch')

    search_opts = parser.add_argument_group('Input/output')
    search_opts.add_argument(
        "-g",
        "--gene",
        dest="gene",
        required=True,
        help="The gene name.",
        type=str)

    search_opts.add_argument(
        "-s",
        "--species",
        dest="species",
        required=True,
        help="The species name.",
        type=str)

    search_opts.add_argument(
        "--use_open_api",
        dest="open_api",
        action="store_true",
        required=False,
        help="Use OpenAI to summarise the texts, otherwise uses local LLM API",
        )

    search_opts.add_argument("-n",
                         "--num-papers",
                         dest="number_papers",
                         help="Number of papers to summarise (default=3)",
                         default=3,
                         type=int)
    
    search_opts.add_argument(
                         "--max-paragraphs",
                         dest="max_para",
                         help="Maximum number of paragraphs to include per paper (default=10)",
                         default=10,
                         type=int)

     # Other options
    parser.add_argument('-l', '--loglevel', type=str.upper,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Set the logging threshold.')

    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s ' + version("genesearch"))

    args = parser.parse_args(args)
    return (args)


def main():

    # Load arguments
    args = get_options(sys.argv[1:])

    # set logging up
    logging.basicConfig(level=args.loglevel,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

    if args.max_para <= 3:
        logging.error("The maximum number of paragraphs must be > 3!")
        sys.exit(1)

    # Load API Keys
    apis = {}
    apis['google_api_key'] = os.getenv('GOOGLE_API_KEY')
    apis['google_engine_id'] = os.getenv('GOOGLE_ENGINE_ID')
    apis['openai_api_key'] = os.getenv('OPENAI_API_KEY')

    if None in apis.values():
        with importlib.resources.as_file(importlib.resources.files("genesearch").joinpath("api_keys.yaml")) as yaml_path:
            with open(yaml_path) as yaml_file:
                try:
                    apis = yaml.safe_load(yaml_file)
                except yaml.YAMLError as error:
                    print(f"Error reading YAML file: {error}")

    # Search for the gene and species
    # Define your search query
    query = f'"{args.gene}" {args.species}'

    # Call the custom Google Search API
    results = call_google_search_api(apis['google_api_key'], apis['google_engine_id'], query)

    # Download the text of the first 10 results
    texts = download_text_from_search_results(results, args.number_papers)
    #texts = [text for text in texts if args.gene.lower() in " ".join(text).lower()]

    # Decide on which api to use
    if args.open_api and apis['openai_api_key'] is not None:
        #Set the OpenAI API key
        openai.api_key = apis['openai_api_key']
        logging.info("Using OpenAI API")
        final_summary = text_process_OpenAI(texts, args.gene, args.species, args.max_para)
    else:
        logging.info("Using local LLM API")
        final_summary = text_process_cluster_LLM(
            texts=texts,
            query=query,
            api_url=os.getenv('CLUSTER_API_URL', apis['cluster_api_url']),
        )

    write_summary(final_summary, f"{args.gene}_{args.species}.txt")

    return


if __name__ == '__main__':
    main()
