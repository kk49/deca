import sys
import os
import subprocess
import datetime
import json
import requests

# based on script from Sankarsan Kampa (a.k.a. k3rn31p4nic)

if len(sys.argv) < 4:
    print('WARNING NEED AT LEAST TWO PARAMETERS: <STATUS> <CHANGELOG> <WEBHOOK_URL>.'
          'See: https://github.com/DiscordHooks/appveyor-discord-webhook')

status = sys.argv[1]
changelog_fn = sys.argv[2]
webhook_url = sys.argv[3]

print('Webhook setup...')

if status == 'success':
    embed_color = 3066993
    status_message = "Success"
elif status == 'failure':
    embed_color = 15158332
    status_message = "Failure"
else:
    embed_color = 0xFF0000
    status_message = "Unhandled Status: " + status

avatar_url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Appveyor_logo.svg/256px-Appveyor_logo.svg.png'

APPVEYOR_REPO_COMMIT = os.environ.get("APPVEYOR_REPO_COMMIT", None)
APPVEYOR_BUILD_VERSION = os.environ.get("APPVEYOR_BUILD_VERSION", None)
APPVEYOR_BUILD_NUMBER = os.environ.get("APPVEYOR_BUILD_NUMBER", None)
APPVEYOR_REPO_NAME = os.environ.get("APPVEYOR_REPO_NAME", None)
APPVEYOR_REPO_BRANCH = os.environ.get("APPVEYOR_REPO_BRANCH", None)
APPVEYOR_JOB_ID = os.environ.get("APPVEYOR_JOB_ID", None)


if not APPVEYOR_REPO_COMMIT:
    result = subprocess.run(['git', 'log', '-1', '--pretty=%H'], stdout=subprocess.PIPE)
    APPVEYOR_REPO_COMMIT = result.stdout.decode('utf-8').rstrip()

result = subprocess.run(['git', 'log', '-1', APPVEYOR_REPO_COMMIT, '--pretty=%aN'], stdout=subprocess.PIPE)
AUTHOR_NAME = result.stdout.decode('utf-8').rstrip()

result = subprocess.run(['git', 'log', '-1', APPVEYOR_REPO_COMMIT, '--pretty=%cN'], stdout=subprocess.PIPE)
COMMITTER_NAME = result.stdout.decode('utf-8').rstrip()

result = subprocess.run(['git', 'log', '-1', APPVEYOR_REPO_COMMIT, '--pretty=%s'], stdout=subprocess.PIPE)
COMMIT_SUBJECT = result.stdout.decode('utf-8').rstrip()

result = subprocess.run(['git', 'log', '-1', APPVEYOR_REPO_COMMIT, '--pretty=%b'], stdout=subprocess.PIPE)
COMMIT_MESSAGE = result.stdout.decode('utf-8').rstrip()

# print(f'APPVEYOR_REPO_COMMIT -> {APPVEYOR_REPO_COMMIT}')
# print(f'AUTHOR_NAME -> {AUTHOR_NAME}')
# print(f'COMMITTER_NAME -> {COMMITTER_NAME}')
# print(f'COMMIT_SUBJECT -> {COMMIT_SUBJECT}')
# print(f'COMMIT_MESSAGE -> {COMMIT_MESSAGE}')

if AUTHOR_NAME == COMMITTER_NAME:
    CREDITS = f'{AUTHOR_NAME} authored & committed'
else:
    CREDITS = f'{AUTHOR_NAME} authored & {COMMITTER_NAME} committed'

if os.environ.get("APPVEYOR_PULL_REQUEST_NUMBER"):
    COMMIT_SUBJECT = \
        f'PR {os.environ["APPVEYOR_PULL_REQUEST_NUMBER"]} - {os.environ["APPVEYOR_PULL_REQUEST_TITLE"]}'
    URL = f'https://github.com/{os.environ["APPVEYOR_REPO_NAME"]}/pull/{os.environ["APPVEYOR_PULL_REQUEST_NUMBER"]}'
else:
    URL = ''

# CHANGE LOG EXTRACT
with open(changelog_fn, 'r') as f:
    lines = f.readlines()

block_count = 0
second_block = -1
for i, line in enumerate(lines):
    if line.startswith('####'):
        block_count += 1

    if block_count >= 2:
        second_block = i - 1
        break

lines = lines[:second_block]
lines = [line.replace('\n', '') for line in lines]

while len(lines[-1]) == 0:
    lines = lines[:-1]

CHANGELOG = '\n'.join(lines)

result = subprocess.run(['git', 'log', '-1', APPVEYOR_REPO_COMMIT, '--pretty=%aN'], stdout=subprocess.PIPE)
AUTHOR_NAME = result.stdout.decode('utf-8').rstrip()

TIMESTAMP = datetime.datetime.now().isoformat() + 'Z'

WEBHOOK_DATA = {
    'username': '',
    'avatar_url': avatar_url,
    'embeds': [
        {
            'color': embed_color,
            'author': {
                'name': f'{APPVEYOR_REPO_NAME}/deca_gui-b{APPVEYOR_BUILD_NUMBER}.zip',
                'url': f'https://ci.appveyor.com/api/buildjobs/{APPVEYOR_JOB_ID}/artifacts/deca_gui-b{APPVEYOR_BUILD_NUMBER}.zip',
                'icon_url': avatar_url,
            },
            'title': COMMIT_SUBJECT,
            'url': URL,
            'description': f'{COMMIT_MESSAGE} {CREDITS}\n\n{CHANGELOG}',
            'fields': [
                {
                    'name': 'Commit',
                    'value': f'[{APPVEYOR_REPO_COMMIT[0:8]}](https://github.com/{APPVEYOR_REPO_NAME}/commit/{APPVEYOR_REPO_COMMIT})',
                    'inline': True,
                },
                {
                    'name': 'Branch',
                    'value': f'[{APPVEYOR_REPO_BRANCH}](https://github.com/{APPVEYOR_REPO_NAME}/tree/{APPVEYOR_REPO_BRANCH})',
                    'inline': True

                }
            ],
            'timestamp': TIMESTAMP
        }
    ]
}

print('---- WEBHOOK_DATA ----')
print(json.dumps(WEBHOOK_DATA, indent=2))
print('---- --------- ----')


print('Webhook Sending ...')

response = requests.post(
    webhook_url,
    data=json.dumps(WEBHOOK_DATA),
    headers={
        'Content-Type': 'application/json',
        'UserAgent': 'AppVeyor-Webhook',
    }
)

if response.status_code in {200, 204}:
    print('Webhook Complete')
else:
    print(f'Webhook Error: Request returned an error {response.status_code}, the response is:\n{response.text}')
