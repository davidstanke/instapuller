### Configure preview environments
Do the following, then whenever there's a pull request against branch `staging`, Cloud Build will create a Cloud Run revision specific to that PR. _NOTE: all preview deployments share a single Cloud SQL database._

#### Configure repo access for the build:
1. Make a GitHub personal access token
  * Visit your [Personal Access Tokens page](https://github.com/settings/tokens), create a token with **repo** scope, and copy it.
  * `export GITHUB_TOKEN=<paste_your_token_here>`

1. Enable Secret Manager and grant Cloud Build access
  ```bash
  gcloud services enable secretmanager.googleapis.com
  gcloud secrets create github_token --replication-policy automatic
  echo -n "${GITHUB_TOKEN}" | gcloud secrets versions add github_token --data-file=-
  gcloud secrets add-iam-policy-binding github_token --member serviceAccount:${GCB_SERVICE_ACCT} --role roles/secretmanager.secretAccessor
  ```

#### Run these commands:

```bash
gcloud sql databases create instapuller-preview --instance=instapuller --charset=utf8mb4

gcloud run deploy instapuller-preview --image=gcr.io/$PROJECT/instapuller --region=us-central1 --platform=managed --allow-unauthenticated --set-env-vars=DB_USER=root,DB_PASS=${PASSWORD},DB_NAME=instapuller-preview,CLOUD_SQL_CONNECTION_NAME=$PROJECT:us-central1:instapuller --set-cloudsql-instances=$PROJECT:us-central1:instapuller

gcloud beta builds triggers create github \
   --repo-name=instapuller \
   --repo-owner=${GITHUB_USER} \
   --pull-request-pattern="^staging$" \
   --build-config="preview.cloudbuild.yaml" \
   --description="For each PR against staging, deploy a preview environment" \
   --substitutions="_GH_USERNAME=${GITHUB_USER}"
```