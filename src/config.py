import os
from dotenv import load_dotenv
load_dotenv()


GITLAB_URL = 'https://your-gitlab-url.com'
GITLAB_TOKEN = os.getenv('LOGLADY_GITLAB_TOKEN')
GITLAB_GROUP_ID = '1' # project groupId

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
SLACK_CHANNEL = '#publication-channel'

BASE_URL = GITLAB_URL + '/groupUrl'
PRODUCT_1 = ['repo1', 'repo2']
PRODUCT_2 = ['repo3']
PRODUCT_3 = ['repo4', 'repo5', 'repo6']
PRODUCT = {
    'ProductLabel1': PRODUCT_1,
    'ProductLabel2': PRODUCT_2,
    'ProductLabel3': PRODUCT_3
}

def get_repositories():
    all_repositories = []
    repos_to_products = {}
    for product_name, product_url in PRODUCT.items():
        for repo in product_url:
            _project_url = f'{BASE_URL}/{repo}'
            repos_to_products[_project_url] = product_name
            all_repositories.append(_project_url)
    return all_repositories, repos_to_products

