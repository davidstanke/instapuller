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

### Testing locally against a cloud DB

#### Setup Cloud SQL Proxy (do this in a separate terminal)

1. Download Cloud Sql Proxy
   > `wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy`
2. Make it executable
   > `chmod +x cloud_sql_proxy`
3. Create a root cloudsql dir
   > `sudo mkdir /cloudsql`
4. Start the Cloud SQL Proxy
   > `sudo ./cloud_sql_proxy -dir=/cloudsql -instances=serverless-ux-playground:us-central1:instapuller`

#### Run the Python app locally (different terminal from the SQL Proxy)

1. Setup the Env variables that let us connect to our Cloud SQL DB
   > `export DB_USER='root'; export DB_PASS=$DB_PASS ; export DB_NAME='instapuller-staging' ; export CLOUD_SQL_CONNECTION_NAME='serverless-ux-playground:us-central1:instapuller'`
2. Make sure you're in the insta-puller directory
   > `cd repos/instapuller/`
3. Enable the virtual environment
   > `source .env/bin/activate`
4. Run the app
   > `python app.py`




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