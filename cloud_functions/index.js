var fs = require("fs");
var https = require("https");

const instaPullerAddress = "https://instapuller.serverlessux.design/";
const userNamesEndPoint = instaPullerAddress + "usernames";
const profilePullEndPoint = instaPullerAddress + "?username=";
const CloudStorageBucket = "instapuller";
const localFilePath = "/tmp/tempFile.jpg";

var instaFileName;
/**
 * Summary.
 * This Cloud Function hits the usernames endpoint and then requests a new pull for each username known to the system.
 * Triggered by Cloud Scheduler
 */
exports.updateEachProfile = async (req, res) => {
  const fetch = require("node-fetch");

  const response = await fetch(userNamesEndPoint);
  const usersObj = await response.json();

  usersObj.forEach((username) => {
    fetch(profilePullEndPoint + username) //Request pull of username from Instapuller
      .then((res) => res.text())
      .then(console.log("Fetched: " + username));
  });

  res.json(usersObj);
};

/**
 * Summary.
 * This Cloud Function is triggered when new posts entries are created in the data store for a username. The triggering event contains
 * the Media source url, the media is then requested and saved to a Cloud Storage bucket.
 * Triggered by a Pub/Sub Event
 *
 * TODO: Save the new path back to the datastore as well.
 */
exports.saveMedia = (event, context) => {
  const messageString = Buffer.from(event.data, "base64").toString("utf8");
  const obj = JSON.parse(messageString);
  const mediaPath = obj.display_url;
  instaFileName = getMediaFileName(mediaPath);
  downloadContent(mediaPath).then(saveImageToCloudStorage);
};

/**
 * Summary.
 * Expecting a media path like
 *  'https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/e35/91024791_515116672723212_649083489558396095_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=100&_nc_ohc=ZuotofT8lC8AX_hLImL&oh=1f5e9d407b557027dca36c7c03d1842f&oe=5EABD3AF'
 * This function will return the media name at the end of the URL
 * 	'91024791_515116672723212_649083489558396095_n.jpg'
 */
function getMediaFileName(mediaPath) {
  var url = require("url");
  var q = url.parse(mediaPath, true);
  return q.pathname.split("/").pop();
}

const downloadContent = function (url) {
  return new Promise((resolve, reject) => {
    try {
      fs.unlinkSync(localFilePath);
    } catch (error) {}

    var file = fs.createWriteStream(localFilePath);
    var request = https.get(url, function (response) {
      response.pipe(file);
    });
    request.on("finish", function (response) {
      resolve();
    });
  });
};

function saveImageToCloudStorage() {
  const { Storage } = require("@google-cloud/storage");
  const storage = new Storage();

  async function uploadFile() {
    // Uploads a local file to the bucket
    await storage.bucket(CloudStorageBucket).upload(localFilePath, {
      // Support for HTTP requests made with `Accept-Encoding: gzip`
      gzip: true,
      destination: instaFileName,
      // By setting the option `destination`, you can change the name of the
      // object you are uploading to a bucket.
      metadata: {
        // Enable long-lived HTTP caching headers
        // Use only if the contents of the file will never change
        // (If the contents will change, use cacheControl: 'no-cache')
        cacheControl: "public, max-age=31536000",
      },
    });

    console.log(`${instaFileName} uploaded to Bucket: ${CloudStorageBucket}.`);
  }
  uploadFile().catch(console.error);
}

/**
 * Summary.
 * Used with the functions framework to enable local testing with the following start command
 * 	    "start": "functions-framework --target=testLocalEvents --type=event"
 * and then calling curl like so
 * 		curl -d "@testEvent.json" -X POST   -H "Ce-Type: true"   -H "Ce-Specversion: true"   -H "Ce-Source: true"   -H "Ce-Id: true"   -H "Content-Type: application/json"   http://localhost:8080
 */
exports.testLocalEvents = (data, context) => {
  this.saveMedia({
    data: data.body.message.data,
  });
};
