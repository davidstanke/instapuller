# Insta-puller
A Serverless (compute) approach to scraping Instagram feeds.
_Note that storing data in Cloud SQL isn't a truly serverless data solution_

## Setup
This should only take about 5 minutes. It's mostly a ton of copying-and-pasting shell commands. You can run it from any terminal that has gcloud and docker, but the easiest way is to **run all the following commands in cloud shell**. You'll need a GitHub.com personal account. *Recommended: create a new GCP project before proceeding. Run `gcloud init` if needed to authorize your session to the project you'll use for this application.*

#### Set some convenience vars
```bash
export PROJECT=$(gcloud config list --format 'value(core.project)')
export PROJECT_NUMBER=$(gcloud projects list --filter="$PROJECT" --format="value(PROJECT_NUMBER)")
export GCB_SERVICE_ACCT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
export RUN_SERVICE_ACCT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
```

_Replace `<your_github_username>` with your account:_
```bash
export GITHUB_USER=<your_github_username>
```

#### Duplicate repo
Don't clone this repo directly; instead, click "Use this template" to make a copy. Call it `instapuller`. Then clone your copy of the repo:
```bash
git clone https://github.com/${GITHUB_USER}/instapuller && cd instapuller
```

#### Enable APIs and grant IAM permissions
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com sqladmin.googleapis.com
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$GCB_SERVICE_ACCT --role=roles/run.admin
gcloud iam service-accounts add-iam-policy-binding $RUN_SERVICE_ACCT --member=serviceAccount:$GCB_SERVICE_ACCT --role=roles/iam.serviceAccountUser
```

#### Create CloudSQL databases
```bash
export PASSWORD=$(openssl rand -base64 15)
gcloud sql instances create instapuller --zone=us-central1-c --root-password=${PASSWORD}
gcloud sql databases create instapuller-prod --instance=instapuller
gcloud sql databases create instapuller-staging --instance=instapuller
```

#### Create initial application container
```bash
docker build -t gcr.io/$PROJECT/instapull .
docker push gcr.io/$PROJECT/instapull
```

#### Create Cloud Run services
```bash
gcloud run deploy instapuller-prod --image=gcr.io/$PROJECT/instapull --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-prod,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller

gcloud run deploy instapuller-staging --image=gcr.io/$PROJECT/instapull --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-staging,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller

echo -e "======\nHere are the URLs of your Cloud Run services:\n-----\n$(gcloud run services list --platform=managed --format='value(URL)')\n====="
```
_Open both URLs in a browser to verify that they work!_

#### Verify that Cloud Build pipelines work
```bash
gcloud builds submit --substitutions=_DEPLOY_ENVIRONMENT=staging
gcloud builds submit --substitutions=_DEPLOY_ENVIRONMENT=prod
```

### Connect your repo
_For this, you'll use the Cloud Build Triggers page in the GCP console._

See the docs for [Connecting to source repositories](https://cloud.google.com/cloud-build/docs/automating-builds/create-manage-triggers#connect_repo)

1. Use the "Cloud Build GitHub App" option and grant access if asked to do so.
1. Select your copy of the `instapuller` repo
1. On the "create a push trigger" step, click **Skip for now** (we'll add the trigger via gcloud)

### Add triggers
#### On commit to `main`, deploy to prod:
```bash
gcloud beta builds triggers create github \
   --repo-name=instapuller \
   --repo-owner=${GITHUB_USER} \
   --branch-pattern="^main$" \
   --build-config="cloudbuild.yaml" \
   --description="On commit to branch: main, deploy to prod service" \
   --substitutions="_DEPLOY_ENVIRONMENT=prod"
```

#### On commit to `staging`, deploy to staging:
```bash
gcloud beta builds triggers create github \
   --repo-name=instapuller \
   --repo-owner=${GITHUB_USER} \
   --branch-pattern="^staging$" \
   --build-config="cloudbuild.yaml" \
   --description="On commit to branch: staging, deploy to staging service" \
   --substitutions="_DEPLOY_ENVIRONMENT=staging"
```

***Test it out!*** Make a commit to `staging` and you should see your changes reflected on your staging service; merge that to `main` and you should see the changes on prod.

-----------

## Running Locally
See [docs > runlocally.md](docs/runlocal.md)

[TODO: document the GCF functions]