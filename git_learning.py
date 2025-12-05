from dotenv import load_dotenv
from github import Github
import os
from github import Auth

load_dotenv()

auth = Auth.Token(os.getenv("GITHUB_TOKEN"))

a = Github(auth=auth)

for repo in a.get_user().get_repos():
    print(repo.name)


a.close()
