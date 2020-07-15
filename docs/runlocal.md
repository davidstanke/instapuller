## Running Locally
### Setup Instructions (for working in Cloud Shell)

1. Create and enable virtual environment
   > `python3 -m venv .env; source .env/bin/activate`
2. Install python requirements
   > `pip3 install -r requirements.txt`
3. Run application, using local sqlite database
   > `DB_TYPE=sqlite3 python3 app.py`

### Testing locally
> `PYTHONPATH=./env/lib python3 tests/main.py`

# Other bits

## Features to add

1. Download and store the associated media from posts.
1. Build an API to query for stored information (perhaps using the API Gateway)
   1. What usernames are being tracked?
   1. How many posts are stored?
   1. Return the data for a username (with time searches)
1. Maybe some unit-tests for code

## Features added

1. Automated recurring pulls for usernames in the database (Cloud Scheduler calls a Cloud Function)

## Cloud Functions

1. There are 2 cloud functions
   1. "Instapuller-nightly-updater" every 2 hours Hits the usernames endpoint and the requests a new pull for each username. Triggered by Cloud Scheduler
   1. "instapuller-media-download" pub/sub triggered cloud function on each successful DB insert for a new post. Stores the associated media in a Cloud Storage bucket.

### Cloud Functions testing

## Random notes

Direct post page <https://www.instagram.com/p/B82Cy69nDaQ/>
Example User page <https://www.instagram.com/danaherjohn>