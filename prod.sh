echo "Installing deps"
pipenv install
echo "Starting server"
nohup pipenv run python tv.py &
