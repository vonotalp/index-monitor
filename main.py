import json
import requests
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from yaml import full_load


def get_path(filename):
    # Getting an absolute path for items in the same folder as the script
    here_path = os.path.dirname(os.path.realpath(__file__))
    path_to_file = os.path.join(here_path, filename)
    return path_to_file


def get_credentials():
    # Getting credentials for the luminati account from config.yaml
    config = full_load(open(get_path('config.yaml'), 'r', encoding='utf-8'))
    username = config['luminati_username']
    password = config['luminati_password']
    return username, password


def get_serp_results(domain):
    # getting Json with SERP results from luminati
    username, password = get_credentials()
    # TODO replace credentials with id from luminati
    proxies = {
        'http': f'http://{username}:{password}@zproxy.lum-superproxy.io:22225',
        'https': f'http://{username}:{password}@zproxy.lum-superproxy.io:22225'
    }
    base_url = 'http://www.google.co.uk/search'
    payload = {
        # Search query
        'q': f'site:{domain}',
        'lum_json': '1'
        # output '1' for Json and '0' for html
    }
    retries = Retry(
        total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    request_results = session.get(base_url, params=payload, proxies=proxies)
    results_json = request_results.json()
    print(f"Got SERP results for {domain}")
    return results_json


def get_results_count(domain):
    results = get_serp_results(domain)
    # Either getting status empty from the json or the amount of URLs found
    try:
        empty_status = results['general']['empty']
        if empty_status is True:
            results_count = 0
            print(f'{domain} has no results \n')
        else:
            print(empty_status)
    except KeyError:
        results_count = results['general']['results_cnt']
        print(f'{domain} has {results_count} results \n')
    return results_count


def get_domains():
    # Getting a list of domains that need testing from domains.yaml
    domains_to_test = []
    domains_file = full_load(open(get_path('domains.yaml'), 'r', encoding='utf-8'))
    for domain in domains_file['domains']:
        domains_to_test.append(domain)
    return domains_to_test


def check_domains():
    # Iterating through domain, creating a dictionary with {domain: how many results it has}
    domain_count_dict = {}
    for domain in get_domains():
        domain_count_dict[domain] = get_results_count(domain)
    return domain_count_dict


# TODO: Save past results and compare with them, reporting only changed statuses


def create_output_json(domain_count_dict):
    # Create an output message for slack, containing only domains that have results
    domain_count_dict_nonempty = {}
    for key, value in domain_count_dict.items():
        if value != 0:
            domain_count_dict_nonempty[key] = value
    domain_count_json = json.dumps(domain_count_dict_nonempty, indent=4)
    return domain_count_json


def post_to_slack(output_json):
    # Posting a message to a Slack channel
    header = {'Content-type': 'application/json', }
    config = full_load(open(get_path('config.yaml'), 'r', encoding='utf-8'))
    webhook_url = config['webhook_url']
    requests.post(webhook_url, json={"text": f' These domains have been indexed: {output_json}'}, headers=header)


if __name__ == '__main__':
    domain_count_dict = check_domains()
    # TODO: add an option to run test list
    output_json = create_output_json(domain_count_dict)
    post_to_slack(output_json)
    print(output_json)
