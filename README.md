# Insta-puller
A Serverless (compute) approach to scraping Instagram feeds.
_Note that storing data in Cloud SQL isn't a truly serverless data solution_

## Automated deployment

### Setup

#### Duplicate repo
Before cloning this repo, copy it into your GitHub account. Click "Use this template" to make a copy. Call it "instapuller".

*Recommended: create a new GCP project before proceeding.*

#### Set some convenience vars
`export PROJECT=$(gcloud config list --format 'value(core.project)')`
`export PROJECT_NUMBER=$(gcloud projects list --filter="$PROJECT" --format="value(PROJECT_NUMBER)")`
`export GCB_SERVICE_ACCT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"`
`export RUN_SERVICE_ACCT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"`

#### Enable APIs and grant IAM permissions
```
gcloud services enable cloudbuild.googleapis.com run.googleapis.com sqladmin.googleapis.com
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$GCB_SERVICE_ACCT --role=roles/run.admin
gcloud iam service-accounts add-iam-policy-binding $RUN_SERVICE_ACCT --member=serviceAccount:$GCB_SERVICE_ACCT --role=roles/iam.serviceAccountUser
```

#### Create CloudSQL databases
```
export PASSWORD=$(openssl rand -base64 15)
gcloud sql instances create instapuller --zone=us-central1-c --root-password=${PASSWORD}
gcloud sql databases create instapuller-prod --instance=instapuller
gcloud sql databases create instapuller-staging --instance=instapuller
```

#### Create initial application container
```
docker build -t gcr.io/$PROJECT/instapull .
docker push gcr.io/$PROJECT/instapull
```

#### Create Cloud Run services
```
gcloud run deploy instapuller-prod --image=gcr.io/$PROJECT/instapull --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-prod,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller

gcloud run deploy instapuller-staging --image=gcr.io/$PROJECT/instapull --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-staging,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller
```

#### Verify that Cloud Build pipelines work
```
gcloud builds submit --substitutions=_DEPLOY_ENVIRONMENT=staging
gcloud builds submit --substitutions=_DEPLOY_ENVIRONMENT=prod
```

The deployed CR service will need all of the Environment Variables and the Cloud SQL Connection created

## Running Locally
### Setup Instructions (for working in Cloud Shell)

1. Clone (inside Cloud Shell)
   > `gcloud source repos clone insta-puller --project=serverless-ux-playground`
2. move into the new directory
   > `cd insta-puller`
3. Create and enable virtual environment
   > `python3 -m venv .env; source .env/bin/activate`
4. Install python requirements
   > `pip3 install -r requirements.txt`

### Setup Cloud SQL Proxy (do this in a separate terminal)

1. Download Cloud Sql Proxy
   > `wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy`
2. Make it executable
   > `chmod +x cloud_sql_proxy`
3. Create a root cloudsql dir
   > `sudo mkdir /cloudsql`
4. Start the Cloud SQL Proxy
   > `sudo ./cloud_sql_proxy -dir=/cloudsql -instances=serverless-ux-playground:us-west1:instadatabase`

### Run the Python app locally (different terminal from the SQL Proxy)

1. Setup the Env variables that let us connect to our Cloud SQL DB
   > `export DB_USER='root'; export DB_PASS='ab440c97193768e9b845abd25e57066e' ; export DB_NAME='insta' ; export CLOUD_SQL_CONNECTION_NAME='serverless-ux-playground:us-west1:instadatabase'`
2. Make sure you're in the insta-puller directory
   > `cd repos/insta-puller/`
3. Enable the virtual environment
   > `source .env/bin/activate`
4. Run the app
   > `python app.py`

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