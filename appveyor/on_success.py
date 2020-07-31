import sys
import os
import subprocess
import json
import requests

# based on script from Sankarsan Kampa (a.k.a. k3rn31p4nic)

if len(sys.argv) < 3:
    print('WARNING NEED AT LEAST TWO PARAMETERS: <STATUS> <WEBHOOK_URL>.'
          'See: https://github.com/DiscordHooks/appveyor-discord-webhook')

status = sys.argv[1]
webhook_url = sys.argv[2]

print('Generating webhook body...', file=sys.stderr)

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

repo_commit = os.environ["APPVEYOR_REPO_COMMIT"]
result = subprocess.run(['git', 'log', '-1', '--pretty=%H'], stdout=subprocess.PIPE)
if not repo_commit:
    repo_commit = result.stdout.decode('utf-8')

result = subprocess.run(['git', 'log', '-1', repo_commit, '--pretty=%aN'], stdout=subprocess.PIPE)
AUTHOR_NAME = result.stdout.decode('utf-8')

result = subprocess.run(['git', 'log', '-1', repo_commit, '--pretty=%cN'], stdout=subprocess.PIPE)
COMMITTER_NAME = result.stdout.decode('utf-8')

result = subprocess.run(['git', 'log', '-1', repo_commit, '--pretty=%s'], stdout=subprocess.PIPE)
COMMIT_SUBJECT = result.stdout.decode('utf-8')

result = subprocess.run(['git', 'log', '-1', repo_commit, '--pretty=%b'], stdout=subprocess.PIPE)
COMMIT_MESSAGE = result.stdout.decode('utf-8')


print(f'APPVEYOR_REPO_COMMIT -> {os.environ["APPVEYOR_REPO_COMMIT"]}')
print(f'REPO_COMMIT -> {repo_commit}')
print(f'AUTHOR_NAME -> {AUTHOR_NAME}')
print(f'COMMITTER_NAME -> {COMMITTER_NAME}')
print(f'COMMIT_SUBJECT -> {COMMIT_SUBJECT}')
print(f'COMMIT_MESSAGE -> {COMMIT_MESSAGE}')

'''
$AVATAR="https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Appveyor_logo.svg/256px-Appveyor_logo.svg.png"

if (!$env:APPVEYOR_REPO_COMMIT) {
  $env:APPVEYOR_REPO_COMMIT="$(git log -1 --pretty="%H")"
}

$AUTHOR_NAME="$(git log -1 "$env:APPVEYOR_REPO_COMMIT" --pretty="%aN")"
$COMMITTER_NAME="$(git log -1 "$env:APPVEYOR_REPO_COMMIT" --pretty="%cN")"
$COMMIT_SUBJECT="$(git log -1 "$env:APPVEYOR_REPO_COMMIT" --pretty="%s")" -replace "`"", "'"
$COMMIT_MESSAGE="$(git log -1 "$env:APPVEYOR_REPO_COMMIT" --pretty="%b")" -replace "`"", "'"

if ($AUTHOR_NAME -eq $COMMITTER_NAME) {
  $CREDITS="$AUTHOR_NAME authored & committed"
}
else {
  $CREDITS="$AUTHOR_NAME authored & $COMMITTER_NAME committed"
}

if ($env:APPVEYOR_PULL_REQUEST_NUMBER) {
  $COMMIT_SUBJECT="PR #$env:APPVEYOR_PULL_REQUEST_NUMBER - $env:APPVEYOR_PULL_REQUEST_TITLE"
  $URL="https://github.com/$env:APPVEYOR_REPO_NAME/pull/$env:APPVEYOR_PULL_REQUEST_NUMBER"
}
else {
  $URL=""
}

$CHANGE_LOG_LINES=(python ./appveyor/get_dev_changelog.py CHANGELOG.md) -join "\n" -replace "`"", "'"
Write-Output $CHANGE_LOG_LINES

$BUILD_VERSION = [uri]::EscapeDataString($env:APPVEYOR_BUILD_VERSION)
$TIMESTAMP="$(Get-Date -format s)Z"
$WEBHOOK_DATA="
{
  ""username"": """",
  ""avatar_url"": ""$AVATAR"",
  ""embeds"":
  [
    {
      ""color"": $EMBED_COLOR,
      ""author"": {
        ""name"": ""$env:APPVEYOR_REPO_NAME/deca_gui-b$env:APPVEYOR_BUILD_NUMBER.zip"",
        ""url"": ""https://ci.appveyor.com/api/buildjobs/$env:APPVEYOR_JOB_ID/artifacts/deca_gui-b$env:APPVEYOR_BUILD_NUMBER.zip"",
        ""icon_url"": ""$AVATAR""
      },
      ""title"": ""$COMMIT_SUBJECT"",
      ""url"": ""$URL"",
      ""description"": ""$COMMIT_MESSAGE $CREDITS\n\n$CHANGE_LOG_LINES"",
      ""fields"": [
        {
          ""name"": ""Commit"",
          ""value"": ""[``$($env:APPVEYOR_REPO_COMMIT.substring(0, 7))``](https://github.com/$env:APPVEYOR_REPO_NAME/commit/$env:APPVEYOR_REPO_COMMIT)"",
          ""inline"": true
        },
        {
          ""name"": ""Branch"",
          ""value"": ""[``$env:APPVEYOR_REPO_BRANCH``](https://github.com/$env:APPVEYOR_REPO_NAME/tree/$env:APPVEYOR_REPO_BRANCH)"",
          ""inline"": true
        }
      ],
      ""timestamp"": ""$TIMESTAMP""
    }
  ]
}"

Invoke-RestMethod -Uri "$WEBHOOK_URL" -Method "POST" -UserAgent "AppVeyor-Webhook" `
  -ContentType "application/json" -Header @{"X-Author"="k3rn31p4nic#8383"} `
  -Body $WEBHOOK_DATA `
  -Verbose

Write-Output "[Webhook]: Successfully sent the webhook."
'''