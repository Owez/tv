echo "Installing deps"
pipenv install
echo "Starting server"
nohup python3 tv.py &
