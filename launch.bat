echo Checking for updates
git reset --hard
git pull origin master
echo Launching client
start venv/Scripts/python.exe rdisc.py
EXIT