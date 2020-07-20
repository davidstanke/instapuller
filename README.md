# Insta-puller
A Serverless (compute) approach to scraping Instagram feeds. This application runs on Cloud Run and pulls images and captions from selected Instagram users. It stores these in a Cloud SQL database.

_Note that storing data in Cloud SQL isn't a truly serverless data solution._

## Setup

> 🥧 This looks like a lot of setup, but **it should only take about 5 minutes.** It's just a bunch of copy-and-paste scripts to run in cloud shell. 🍰

You can run these steps from any terminal that has gcloud and docker, but the easiest way is to **run all the following commands in cloud shell**. You'll need a GitHub.com personal account. *Recommended: create a new GCP project before proceeding.*

#### Prep
_Replace `<your_github_username>` with your account (e.g. `davidstanke`):_
```bash
export GITHUB_USER=<your_github_username>

```

#### Duplicate repo
**Don't clone this repo** directly; instead, click "Use this template" to make a copy (or [click here](https://github.com/davidstanke/instapuller/generate)). Call it `instapuller`. Then clone your copy of the repo, and add a "staging" branch:
```bash
git clone https://github.com/${GITHUB_USER}/instapuller && cd instapuller
git checkout -b staging
git push -u origin staging

```

> Alternative setup: you can use Artifact Registry instead of Container Registry:
> * enable artifact registry API and create a registry
> * configure docker (see "setup instructions") on [Artifact Registry UI](https://console.cloud.google.com/artifacts)
> * replace all instances of `gcr.io/$PROJECT/instapuller` with your `*.pkg.dev` registry 

#### Set everything up...
```bash
# set some convenience variables
export PROJECT=$(gcloud config list --format 'value(core.project)')
export PROJECT_NUMBER=$(gcloud projects list --filter="$PROJECT" --format="value(PROJECT_NUMBER)")
export GCB_SERVICE_ACCT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
export RUN_SERVICE_ACCT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Enable APIs and grant IAM permissions
gcloud services enable cloudbuild.googleapis.com run.googleapis.com sqladmin.googleapis.com sql-component.googleapis.com
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$GCB_SERVICE_ACCT --role=roles/run.admin
gcloud iam service-accounts add-iam-policy-binding $RUN_SERVICE_ACCT --member=serviceAccount:$GCB_SERVICE_ACCT --role=roles/iam.serviceAccountUser

# Create CloudSQL databases
export PASSWORD=$(openssl rand -base64 15)
gcloud sql instances create instapuller --zone=us-central1-c --root-password=${PASSWORD}
gcloud sql databases create instapuller-prod --instance=instapuller  --charset=utf8mb4
gcloud sql databases create instapuller-staging --instance=instapuller --charset=utf8mb4

# Create initial application container
docker build -t gcr.io/$PROJECT/instapuller .
docker push gcr.io/$PROJECT/instapuller

# Create Cloud Run services
gcloud run deploy instapuller-prod --image=gcr.io/$PROJECT/instapuller --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-prod,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller

gcloud run deploy instapuller-staging --image=gcr.io/$PROJECT/instapuller --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-staging,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller

echo -e "======\nHere are the URLs of your Cloud Run services:\n-----\n$(gcloud run services list --platform=managed --format='value(URL)')\n====="

```
_Open both URLs in a browser to verify that they work!_
> NOTE: the first load may be slow b/c the application will create the database on first request.

#### OPTIONAL: Verify that Cloud Build pipelines work
```bash
gcloud builds submit --substitutions=_DEPLOY_ENVIRONMENT=staging,SHORT_SHA=$(date +%Y%m%d_%H%M%S)
gcloud builds submit --substitutions=_DEPLOY_ENVIRONMENT=prod,SHORT_SHA=$(date +%Y%m%d_%H%M%S)

```
_Then revisit the application URLs. They should look unchanged._

### Connect your GitHub repo
_For this, you'll use the [Cloud Build Triggers page](https://console.cloud.google.com/cloud-build/triggers) in the GCP console._

> See the docs for [Connecting to source repositories](https://cloud.google.com/cloud-build/docs/automating-builds/create-manage-triggers#connect_repo)

1. Use the "Cloud Build GitHub App" option and grant access if asked to do so.
1. Select your copy of the `instapuller` repo
1. On the "create a push trigger" step, click **Skip for now** (we'll add the trigger via gcloud)

### Add triggers
```bash
# On commit to `main`, deploy to prod:
gcloud beta builds triggers create github \
   --repo-name=instapuller \
   --repo-owner=${GITHUB_USER} \
   --branch-pattern="^main$" \
   --build-config="cloudbuild.yaml" \
   --description="On commit to main, deploy to prod service" \
   --substitutions="_DEPLOY_ENVIRONMENT=prod"

# On commit to `staging`, deploy to staging:
gcloud beta builds triggers create github \
   --repo-name=instapuller \
   --repo-owner=${GITHUB_USER} \
   --branch-pattern="^staging$" \
   --build-config="cloudbuild.yaml" \
   --description="On commit to staging, deploy to staging service" \
   --substitutions="_DEPLOY_ENVIRONMENT=staging"
   
```

***Test it out!*** Make a commit to branch `staging` and push to GitHub; you should see your changes reflected on your staging service. Merge that branch to `main` and you should see the changes on prod.

_Bonus:_ [configure preview environments for each pull request](docs/pr-previews.md)

-----------

## Running Locally
See [docs > runlocally.md](docs/runlocal.md)

[TODO: document the GCF functions]
