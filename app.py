insta-puller/cloudbuild.yaml                                                                        0000644 0001750 0001750 00000001770 13670726436 020106  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            steps:
  # install Test requirements
- name: "docker.io/library/python:3.8"
  args: ['pip', 'install', '-t', '/workspace/lib', '-r', 'requirements.txt']
  # run tests
# - name: 'docker.io/library/python:3.8'
#   args: ["python", "tests/main.py"]
#   env: ["PYTHONPATH=/workspace/lib"]
#   # build the container image
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/instapull', '.']
  # push the container image to Container Registry
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/instapull']
  # deploy container image to Cloud Run
- name: 'gcr.io/cloud-builders/gcloud'
  args: ['run', 'deploy', 'instapull', '--image', 'gcr.io/$PROJECT_ID/instapull', '--region', 'us-west1','--platform', 'managed', '--quiet']
  # send a message into a hangouts chat room
- name: 'python:3.7'
  entrypoint: 'bash'
  args:
  - '-c'
  - |
    pip3 install httplib2
    python ./scripts/send_build_message.py
images: # is this one needed?
- gcr.io/$PROJECT_ID/instapull
        insta-puller/cloud_functions/                                                                       0000755 0001750 0001750 00000000000 13670726436 020265  5                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            insta-puller/cloud_functions/package.json                                                           0000644 0001750 0001750 00000000754 13670726436 022561  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "name": "cloud_functions",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1",
    "start": "functions-framework --target=testLocalEvents --type=event"
  },
  "author": "",
  "license": "ISC",
  "dependencies": {
    "@google-cloud/functions-framework": "^1.5.0",
    "@google-cloud/pubsub": "^0.18.0",
    "@google-cloud/storage": "^4.7.0",
    "node-fetch": "^2.6.0",
    "request": "^2.81.0"
  }
}
                    insta-puller/cloud_functions/index.js                                                               0000644 0001750 0001750 00000007601 13670726436 021736  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            var fs = require("fs");
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
                                                                                                                               insta-puller/cloud_functions/tests/                                                                 0000755 0001750 0001750 00000000000 13670726436 021427  5                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            insta-puller/cloud_functions/tests/curlcommand.sh                                                   0000644 0001750 0001750 00000000321 13670726436 024263  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            curl -d "@tests/testMarkEvent.json" -X POST \
  -H "Ce-Type: true" \
  -H "Ce-Specversion: true" \
  -H "Ce-Source: true" \
  -H "Ce-Id: true" \
  -H "Content-Type: application/json" \
  http://localhost:8080
                                                                                                                                                                                                                                                                                                               insta-puller/cloud_functions/tests/testEvent.json                                                   0000644 0001750 0001750 00000000274 13670726436 024306  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "message": {
    "attributes": {
      "key": "value"
    },
    "data": "",
    "messageId": "136969346945"
  },
  "subscription": "projects/myproject/subscriptions/mysubscription"
}
                                                                                                                                                                                                                                                                                                                                    insta-puller/cloud_functions/tests/testMarkEvent.json                                               0000644 0001750 0001750 00000002300 13670726436 025111  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "message": {
    "attributes": {
      "key": "value"
    },
    "data": "ewogICJ1c2VybmFtZSI6ICJtYXJrX19yb3VkZWJ1c2giLAogICJwb3N0X2lkIjogIkIyc2Z2OGlncF9IIiwKICAic2hvcnRjb2RlIjogIkItTmRISnZINmp4IiwKICAiZGlyZWN0X2xpbmsiOiAiaHR0cHM6Ly93d3cuaW5zdGFncmFtLmNvbS9wL0Iyc2Z2OGlncF9IIiwKICAiY2FwdGlvbiI6ICLwn5akXG5XaG8gY291bGQgYmUgc28gbHVja3k/XG4jY29udGF4ZzIgI3BvcnRyYTQwMCIsCiAgImRpc3BsYXlfdXJsIjogImh0dHBzOi8vc2NvbnRlbnQtc2pjMy0xLmNkbmluc3RhZ3JhbS5jb20vdi90NTEuMjg4NS0xNS9lMzUvNzAxOTk5NjVfNTQ3NDQ0ODA5MzI4NzE0XzgyMDk4NzM4Mzk4NDk5NDY3NDhfbi5qcGc/X25jX2h0PXNjb250ZW50LXNqYzMtMS5jZG5pbnN0YWdyYW0uY29tJl9uY19jYXQ9MTEwJl9uY19vaGM9cEU4UXgwTFlDQlVBWDhoMmYtSSZvaD04YTQ3ZWQ2YmU1NGUxNzJmNWU5MDc5ZmI1YTJhZDEyMSZvZT01RUI5MDYyNiIsCiAgInRodW1ibmFpbF9zcmMiOiAiaHR0cHM6Ly9zY29udGVudC1zamMzLTEuY2RuaW5zdGFncmFtLmNvbS92L3Q1MS4yODg1LTE1L3NoMC4wOC9lMzUvYzkwLjAuODk5Ljg5OWEvczY0MHg2NDAvNzAxOTk5NjVfNTQ3NDQ0ODA5MzI4NzE0XzgyMDk4NzM4Mzk4NDk5NDY3NDhfbi5qcGc/X25jX2h0PXNjb250ZW50LXNqYzMtMS5jZG5pbnN0YWdyYW0uY29tJl9uY19jYXQ9MTEwJl9uY19vaGM9cEU4UXgwTFlDQlVBWDhoMmYtSSZvaD05MjBkYWVhMTNhNjZjZmI1MjkzZDU4MzA1YTgxNGM4YiZvZT01RUI5QTA4OSIKfQo=",
    "messageId": "136969346945"
  },
  "subscription": "projects/myproject/subscriptions/mysubscription"
}
                                                                                                                                                                                                                                                                                                                                insta-puller/cloud_functions/tests/json.json                                                        0000644 0001750 0001750 00000002615 13670726436 023277  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "username": "danaherjohn",
  "post_id": "2273601421731408113",
  "shortcode": "B-NdHJvH6jx",
  "direct_link": "https://www.instagram.com/p/B-NdHJvH6jx",
  "caption": "There is a strong relationship between guard passing and taking an opponents back: We normally think of passing an opponents guard to the side, or occasionally to mount; but some of the most commonly occurring and profitable opportunities come in situations where opponents turn into defensive turtle positions to prevent giving up passing points. YOU MUST BE ABLE TO CAPITALIZE UPON THESE OPPORTUNITIES!! Not only can you potentially score more points with a back take than a guard pass, but in addition you are now in the single best finishing position in the sport. Keep you eyes open for the back when passing!!! Be ready to capitalize immediately upon the great opportunities in front of you!!",
  "display_url": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/e35/91024791_515116672723212_649083489558396095_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=100&_nc_ohc=ZuotofT8lC8AX_hLImL&oh=1f5e9d407b557027dca36c7c03d1842f&oe=5EABD3AF",
  "thumbnail_src": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/sh0.08/e35/c162.0.733.733a/s640x640/91024791_515116672723212_649083489558396095_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=100&_nc_ohc=ZuotofT8lC8AX_hLImL&oh=755d317167eb5c3ef4eaf982219fd2d0&oe=5EAE325A"
}
                                                                                                                   insta-puller/cloud_functions/tests/mark_r.json                                                      0000644 0001750 0001750 00000001402 13670726436 023572  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "username": "mark__roudebush",
  "post_id": "B2sfv8igp_H",
  "shortcode": "B-NdHJvH6jx",
  "direct_link": "https://www.instagram.com/p/B2sfv8igp_H",
  "caption": "🖤\nWho could be so lucky?\n#contaxg2 #portra400",
  "display_url": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/e35/70199965_547444809328714_8209873839849946748_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=pE8Qx0LYCBUAX8h2f-I&oh=8a47ed6be54e172f5e9079fb5a2ad121&oe=5EB90626",
  "thumbnail_src": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/sh0.08/e35/c90.0.899.899a/s640x640/70199965_547444809328714_8209873839849946748_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=pE8Qx0LYCBUAX8h2f-I&oh=920daea13a66cfb5293d58305a814c8b&oe=5EB9A089"
}
                                                                                                                                                                                                                                                              insta-puller/cloud_functions/tests/temp.jpg                                                         0000644 0001750 0001750 00000152701 13670726436 023104  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            ���� JFIF      �� |Photoshop 3.0 8BIM     _( ZFBMD230009820300000b1a00002d1a00007d1a0000254f00002e6e0000b67e0000b4a70000e9c30000c1d50000 ��ICC_PROFILE   lcms  mntrRGB XYZ �    ) 9acspAPPL                          ��     �-lcms                                               
desc   �   ^cprt  \   wtpt  h   bkpt  |   rXYZ  �   gXYZ  �   bXYZ  �   rTRC  �   @gTRC  �   @bTRC  �   @desc       c2                                                                                  text    FB  XYZ       ��     �-XYZ         3  �XYZ       o�  8�  �XYZ       b�  ��  �XYZ       $�  �  ��curv          ��c�k�?Q4!�)�2;�FQw]�kpz���|�i�}���0���� C 


		
%# , #&')*)-0-(0%()(�� C



(((((((((((((((((((((((((((((((((((((((((((((((((((�� �� " ��             	��                 ��      �\a1(�x��#Ύ�c�)-b8��IhZ<A	-��ǈ"���(�0��$8q�QXQ�K���|u��Gi�t�R	����L�]=9`��f[��vNR�z�����uZ��8���Mi�+I(J/���O	a����A����`��6�S��#Pd�	�ƪ5^���Ҵ ���SIOcƀ���5"�B�%/�+��Ê�v|��11GU�3Қ_cr�W���://���_8�4;a��#Mo|�}��>�1�$r��W�Ę��%Ǡ�*�F�?`D>4d&�8�͏$;�B2���PjE� 4*�-����F���O9{�=���sDp�7�xԟ�Zu��C
j��}t3i3 �t���A��#X���1Ԋ*��Y�����I�YH�^o���CȎq�(E���b���,jn����G���Q�j���|�Ȣ"��{Dr(��A}���{�C�'k�xo�x|�dO�s�)r�aE)J���`�{�f�Ժ"0��_�/n���� A��F�H��%�)�K� �YC(�fnOȧO���G6����C�oU�e�
NH�%z7�ĿGP���J�B�h���5�!�fS����'�aP��#)X+�����HA����ô|��ΥO��7Z攱�������FI{+���Q��6	O]>���@X�؜���T�hJX�����|_�4�S'�q# �I�:iy�Π�X#�K�;K��N�^㼗����>0�$<���2�D��уr�� zB��1Ho;��^t|P
��o�mK�L�٪2+�$.�q�:�����*�����_�	�Q�c�8n�x2���Q�/���	��Aa5�
H$H��c� p��qF�8|~��ΕR0�F�P� }�9l�x̸�<���&$�#�3�"9�Өp���[���f��d�c��|F�eM�A�u-�׬+lD�z�¸����2����j.ϛ^���!���`һ4�L��ִ���:��^�e������$o��ý���|t|�>���z��T�(����p�GX�����~b?ܨN �kss�%�d�8�FC�$��D�C��^�w�?��ÑD���>l��wGb���=��f|ed�ҙ�`K�s��1�с&��K,v����ɻ)�ӡ�� y�8��p������i/Ѡ��3؉b@�F*�ǥ_��pp��l-y�T2x���ΐtI��2�7��[�<��ܳ�N�|��>�˟����a#(9d�\�O�~�5ʾGyB|Ѽ�hN�i��.����|y"�Ui��|����[N���@������������󺢏�~ZQƊLv�	B��>�霟Nmi�>Y/,�~���3>�bM|����g�3hUd�r�|�-|�]����z�gN��ߢ�yް���|��~ߥ>Ag��X�c�����z�TL�8�~� :Piq[�ms`L����UX�Q����j�����_���;m��ͧ���z��RLhO	(�}m��=Љɺ�.'���%m��<��b�̆�Y�2�vsW��q�/s�=��J9�%���4�[p�?�o�Ȑ��+� ��%B�o�}�^|W׭,N�:4�0��T�\��v���v��5�8�u4:��K�lܳ�X
Yhz�����)*��4��2�J�P�<���y�9�o>����#�k+60��i�f�ě�!��AU��5Rg��O4v"Ҵ��c���1;�%�������s3F�B��s/��Hq����g(�S�E�ϖ���c�x�9K�!â�#>�Ŕx~$��l�A$�tc�0��XC������j�V���	��R{�Glř���L=OF�*�w-�4y)�FO�+���aU�#�y�d�^n�h��:�%�WF(G#���+�29%�|�64������6L�*g��9��Ӄ���}�����Z��pF�T7�]P(�`�?@0�-�=�ȗE�����S|��U�yR�:kzB'H��8�.�sy�A�HB�al@�6X�:+9ő��KbkR�И�����N|i�А��ʒv[�u�<uDd3�1���Y( ��Cj�)���ga�Ӈ�$ea�"����mhcP��[3�O��bF&tihk9����Q����wW�7�m��bM�z�� N7e�ܙrV�Ѷ���i���!b��,V������Ie��^��eܗ�*/�퉖�֥�j�M��x������X���lY�: ��A�V������s㕚�l����t�:;����V�9�3K�̉&%�J�P=�<�49^�q*.����i�et�CE^�2�m���tx$.� E��<�J�K[��e����h�1}&+��B� K�h�&�����;O��)eG�D��	��u���1��gw��|���3]�������S�)��Nl@��gԷ�*��h	��-1O���}#�����9����|{��@�Fߐ���pm/�cm�d;@��Rh�q`J#����Qri�2S�9�5���O�3WC�/�2������C[nJ��ϕ�$��ǆ<cx�I��h��{	�d#ߘϮ��]���n���O�r� �PR�e-�ț
3MrF�q���15�+8Sʭ�,��,Z#a!kUa����kTܦ1��t����ު>Ҋa���E�U��Y��M�x3JwQԃ�=��h�u� ��]R� �1fOm�#�|������#&�HrNP#E�I��~w�˅��z��[#!�P�t
\H��v� A���ɂc�3���̟�w+��1*T /x� w�i_G�M���d@�+ePid��01͵vWJ`�\��DC7�A���I,$��G�ϖV��� ml�$ F�߸�:��f��)�va�٢5�!t��-�L�����ńgYb��p�T	��6� ɩ�6"D=�y�ϸ�y��+�ZR�l��=N�K�O�v�S�M,���I0爡� H�_��s�E0*�\������`��ey⑔�'��H/k��]�ʚ-�;�t���b	)*����W�T��˔?Y|�e���979h*hݚR|ژ��b�D!�Ɠ�\���#xCA��3�Uf!���n�YM���J%�z������tL�"�9�O���8��8��g
������7UV�DR:i����g�����H1���*�a��9���� ��A��<�
�!Y�9xf��W���ҹ�h�@�(�k�j�
өun�=�]�$�.bs���T�Oo@s|Ĩ�
'0��"���ЎEQ^���[���6w|��ׇ1|oU4����-���@�bo��9A���R�.�;n�S��IO.���\\<j(��YS�*��.:\�O�p��9�"�������b�e��#9�G������\�� �E��$�rH�,bܨ	
ѯG�%�Y<2Ib�-u8�as��wu�X���P�5$#�΂�_�8���J(Ff�7Y�eqA
4%�`�3!k%�+�ʈI�|	��c��D	ܹZ-��ڝa�� *���	33��%rɕ#�����I�$I@"y�=[���漯� ^�	�; ���dZ����%U�� /�0�����o����&��s�+KF��9����r�t�I�kA�4 �C �Ǐ, ��-���a���B�g%�8��hVh6���!�ۣ�N�aº,�e}�(��B0_'�"x#���f�k]�4Z���т4P�}HhGg\I����_r���E�-N��T�ZI��@�!s>���7�8�ۚ0�ȍ��2���k�<5�40C�	%�@@��K2((�,��kl�NhL���#����b3�K|�@�XqgB�����V(�A��iimp� ���<��bW4����X
酟��h�f�Z
Ɨ@�G:,*��f[��$��\�]J2�`J�ZQh��Ē�x�Q�w@�6<� 28]u,��!�8�<��:^ ���9ޱYn�rE�^��!��S	���Vxp�dh��0D`�Yr^ىN7	�WЉ�
���C\�A�]8�]!s�WO�]g�_��/���֖�=>p�
� ��R|7�"����F���UF�e���U���/'E�(.GJ+�Ε ��'�ne�2�p$�����#���|�yX/K�� P���ޔڎ�S�����E:�*�^9�c�4�Q��l�+��	X��xO=c\����"i(�d�y?��pQ+�(���yS.qDbd	-�{L8	,�MH��O7��"s���++m+�ϭ�H(HOFz��	�{�6�S,�T w =�D�qf�*rE5���2�$&;�Z|��ێ0>�q���w��h?�@�Ǫ�s}�sF���{Ǖr+B��=��\��#��Itr���nh����\ВBZ�I�_�Xd4g��wç���.��S l���Nz�>%��]��FBs��Jte%8h)�aǳ�4r�jjJ�0O'�{ȣ՞�Q��A\���ã]�+�5��vE��i
���K�9���a9���� ģ�!-a(�I�Ů�#(��bzۭqD
�O4<�5�q�n.�LR̴�-=W���/�4����
�z�ma��x�P�ҘGS %���y�P^/�+��A�U��#x�P�@E��-�B&��&ڜ��yϲ�7�������X<��6O�Xi33������ώ����,��`!���Q�a�1J� %,��m�U��EjX����=%�OC<�������x7�����^g��b�\���bx3�Ȋ]'5vYr��Fr�o�xL
�(�C�Ux�
I"lS���;`�O8�:A�7f]��O4ry�� �isDlƐCjR�֥([��QǺ�*�NiZ;Q�8$f�B �0�٣"8�#$Ƒ%�t:�>D$q��5�������า�a� oq�5�R	� )��^=�y
��sb�%N�bU�a����YNI�6:x�ڡQ��p�;��AH�:�����R��mX��A+Acⱳ�
!���0戆�X�`�r�d� 
�F?�U���]S�֊̏�17b�D�K�]癙7Ц~�y���G'q���J�$�!<��l�o�I ������
�c�{���ȅ=�<G��:��)#^�)�ZW�(	<GC�dL�(F�"(��(/�����'�O?�H���h��bu��m!I!4��٠p$�b
��S�5�z�=*���h(��$��,��sL4�x7#�1��p79�&�� �H�s`��#H�Y!�v�.8�#�t�@J��I-�0���x���./q�������@��L�G'/hZ��֗;lO�9�e� SO<hMmSKX��Y�bA�J�� ��� ��i"���Q�dw�(*�0cK ��1*"��rEC��B�j?�|O ��FdƑRc���E8�}_;�:Dli��`痑��M��+9�.���[;Di_W(��\b���-�W0,��&ԕ寣H��LHt2�p���0�F� 2!�b �����x�᪊9�p�U�4W5G4�G��ѮD<����h/*�d��=`�{l�S@�<������V�q�XA2�"��|��`*!Kg��
�k�Rx�HIbH��ab,A�J�\(q� �Hъ�"4b��{�<���E��Z��Ұ�A��|��s�zJ��QH~��3����(	�HF)<DVrj�"�d��(b�G�4���                ��� ? H��                ��� ? H�� B     !1A "2Qa0q#3BR�@br��C�$4P���Sc������   ?��E4�V��j�o�J� ��ۿr�j�X�8�೹6R��tRQ��j)��Dz�<�rmH��e5���Ly�\�>�V����Co�~M�
�jիV����k��n����Z��c	��T��7E(Lp_�>`
�@���iX��ۀ�aE�V·�(C	H�Ð�m��>K�C�V�fMA�Z���˷~�voD�h��Z�R�腐Z��O��a^�V�nU�#^8/2��8
�/B�~IC�x�58;����n���IT�Υ,Ĩ�rd�jT��8�鸋Ϫ[SΪ ������`�EA(��.`uʹ�SeQ�>a(�9�=Z)��iR�9v��,1�G)ح�Ȼ�8�J��5�'�U��4# !H���v�[��gr/���,=��p�h�Nr.R8�5n���Ii��˷���+���I\�\�dD�Vr���g+1WêY�O����$(pzj���&����{��NR3TC��z�� Cr�߻T��e�+�J�q�8M�� �j^v#�D��|�#�(���Ę�?�n]���B��(�w�,5���g��h'8���(vC�.NG�U��P*բ�h���/�8�vլ���U��*|�=Ǣ�苔[!�ܜ���j�=Pǳ�|�ldh���mg����9��s���gY�e�fV�Z�jի�jի�Z�#�cq�"c#����Hr�WR�WeM�Ĭ;�Mz������j�]SVe�fV��e�깇��w�+�� �P�?��2~r�*OΆ2_ξ:_T1�!�������z�~��U���W��WǄ�sz����|t~��c���������ĳ��o���U���&jn�s��CU ��So�C��(wo����k6��T���֭Z%Z�jիY��Y�u�>�s��2�=;�\iR�]�0�)8RSc��T�E�ըq)��c�듓�O���3�;�j��&��| ��G��?h���ٸ��+�v#�W��G�O��H� �a1�"�Ƿ���ZqN�в��*ʩWv��0�J'��I��̬eR��kn��-C��.ҝ풂�����8.N�=J��h���W�mZ�;��̝(ɱ��P����bn�;�Jc6h-_V��	�B��
LA�aO�q��-Rv&%�W5�vf.��?�`�"�m��#�Y�γ"�fY��vT1�J�JN�PO�Zλ7�]�p*]�j}���*gs�rv��)B�7�t��u��_V���Q�̃:,N6���Ny>b�i�����?�aX�ת&���ߊ���em�ZwjA����'iH\�5�����\�g��z����vL����?T�с�O�_����No������,6'�5,-���M��ydk��._����K�?0��Z~�����"}�:|��@'99ɢ����J�eڟ|�3�}�S�O�9557�!RIK���Q�݊<�"l �Pjv��x��,{p6J�.�䷝7����W�s��a���,���N���|�÷�n��KhI+��a����p�ˏ�&�s���GG3#ڙ$g�cf�x�g����,^"hX̰�O@���&��>'�މ�ၟi��B��Z?�d��2}T�}�.� �t���}�S���/>�htD�蟆��nc=B��g\<���b;7�����oy�"�]i�M+]���T�.���ٛ(��Hi��	�����52J�UˤSZ\h!���Ң�M�l#+7Oŗ����>W������;%s��^]��l�Z%v�1̬<z� ��ܬ0�/��Xl�9�� Un�H{�����W�5)���9���;i���+C�w����M�H���G��&�1ܞ�H1y��L�����1�r��ZR1��ج9��>�M-�u'e�s�6z��蛑�+Fw�9���fw�R:6i&���A�@����;�l��n�,<��%Va���f�r��,_b���ѩ���8Q�(��4RqWevo��>�J�e�B�]��Q������蠚�{��zވ�h�3utL��5;��
����!e�4�����\Q6�V�,��zq_�l�!w�����N�����7�ӟ�XL��c5w?��1!ϣz�Wh�[�@6/��0�ry�=�����Y��=V3#Z�u.R���bm���~��T���<q����ˏX��z�w�C�����>�Da��抯v\�?����)��� �޷�M��L8����F�5����=�<@�#�`����Y\Մ���x���<��]S��N����|_�,wcχ�G��� �RcP�9Է)�`�3�ܛe���~�9,��7���*�)��rsё`�����U6�r�n�l&J/Uَ�<(����G��yB�RN��fV�Z%�~�gV&vA|���v�vL+@�*L;�Ϝ?��]����m�Aa�����k)b�lӾZ�;��Jc�<ثt����xP�,o}V/���'+��u�o+
����r�	`�eI��Ķ9<C�\�I�4I�X�+C����w�]��Y�Ɯ�?���̏��b¾ꨳd�{?�3�C�>��#���D���	;����csؽ�x�^|1���"����;�լ�8��Q�Xll�X��#���]�6x�'ķ8��=�:'G�/n��w1������e��sD.�o�,,u<S�9n�P�'�[��T�,tw"�@�;����2N騅;/��� S
s�ޜ���Ɉ
�eRK�(����fb9rj����,¬���p��t���U���-�[5Ԭ��߭#��I]���aխ4�ُ��4}Q���c�~�a��&S���n~&���=��#��$Ú=v\�`{A�ǳ6a�������2dg��Ol���|��^�ᑿ�2s��)Ԅ�,�֭2Lqe�}�\���I����&~n��'	�wf�.�3ǌ{b�F�������0��Ϫq���A�з��bok�f�3�CMg=vQMl~gUi����s��-�������±�Ԧv� jآ�WJ,|���v,�C��o#��;�1Xq�`X��v�g� ��<2���0������n*թ6SGz��V��'n�R��4�^��l�;4�`�!PcV'�4�b�Y�e2�E��:2�ӗἬ���f'�`��!R}�)��t]��8l�ѩ�~�ǖ)�$]!����;4u���2buPG& ����ݲvY13��iG�\_��d�7g����ekl���6L��l��C|.�?�7E���k����p;�͔�>;��<n.6]�;��V��o�O�+�� /�ܮ����Β0\���O�mj<K��.LC���i�vr���2�%�̖�]�e�(�CZ�\����7��)���G��9Gɇ�y��I��� ��r��"` ��p�� ���K��#���a��?��41�̲�8,Gbnp�� ���;,�-<;2�Ʉ�zx�R����I�V�H�㪐�J�WT�Ѫ�:�m"[Z���I�D�ܵ|o�����"?�,f�>��[����/��3A$ ��T{5�7+�h�#Z�|z�6f�R��Gb1ӹ�m���Ǎ�W�Ә3��H�.v!������Iou������[����C/
3e觩1�Ci�Ļ<�^#����#�����{#�|�������sp�<���R�]�d����wf�c$�T�̘h����>��UO�ie����`�@�m9��� 	�<��ܼ��uOk���kt ����J����6��0��{�s�ͮek]��<1��V����W�XL,�M�T�'�j���G��2[>�5̴�) i5�����9I*h�Pb�#�h�xڵj�݆r��Ev��E��X�t���T@������Sቲ�5N:.�k��� � ;�adk1��x�Tl�`�2�o-ڷ2�|x�Bj����,�j��T͆�E��ҋ�E����$�`q&��.#��aӿM6j�����-���/�v���C(?Uϗ��:?�^�|L8�Kd�Tq}�m�����vw}��9d�:k�9�\��ˑ��Tr�(6�A��5�z��H���A��5$t��j>�a��i6��~���Ai؏���d�)d�J� 
}�\�i�r�����O�GD�j,Ԝ�\�D4����j֋E��}��v\tG�~��#�����Mo+��c%>�L��������X�AX��_���R�Ge`昐h��/�;�-�W���>��$���蹏�M�J𛄋8��J�^�0=�fk7��apr�m}�hH%�5����/��hfd�>� �O�'�6zc�"�X��K�3W��2C#q�"bho��C���ˆh���Y���f�?1fpF���=�.w�G�M���'3�����֞�b����6�~̙��8;���ݵ��t@���� ��K�ܩ1M�Ԙ��G�3MƸ/�~� �aѳ�
<DO�+%��SZ���A�2/Y����� t�{���;&!��X�ۊ�7�� �A����-����G�8��I����Պ��v��� �Nd%�3��\�qO�6O�c}h�$�4Ӳ��%{�ޫ	���xi9H�h�Ǳ�ϪdD�,��̈��ش�L����k# ��O'�4o_t)�l,f��)t|��5X�#-Xh���c���I���a��.{� ���V�����c�q4��#�[���|�����������U�-ԏ���,lT����9-���4SLN���6�h���|5A�YU>H���G���#yA���0�ٙ����G����h���k����^��a_�jf��p$,ٙ��:@3��H�hg��yV\����B�S�-��B��vO�Ki)�Bس�5�����<E��):���>g�c�O�Gtm��a���db� k�T�?h�ٹ�e�'�^��~�ʞ��Kg�F�ś+H�d�[�+*�ד�y�Z��H����¹��D�H[����p�Zv��ҫ���N?g'�U�ؖ�Y=�X�/@�+u��ǥ���>��q�	�\��z'BÅ]����5)�Y�_d�4��,p�ws�����z�$���|mX� �w�჎�k�sKN�`&�1��Q69!{�(�p蛠�x�XO���S�*+c�N�E��\�ݬ}
��I�qx���!����!��<��!2j9g�G	� ������a�}�"k��E���I�]�d�[��Ʌ��S�#�Q��ff�!t�lы{<AaeB����~lL��U#�Ue\+�*]8�=�]�?��|n>f�J���Gq�����7M�ީ�����rشds}��I���+����7۽��͂-�R�ܻ=�%,O��3��T���v\͌I�ʰ�^"F��J���SI�g�͙�=�6rγ+F��;�XKE̝��� ����~�,k\l��'��΋��#�@���ʷ�-j�n��!^ʂ�GDM�<�n�:\��?E��2f����\~�#�qS7#�=
v�xQm���u_�X�^!�8�d����Or�24��(k���`��N�n�<�خe���u��n'��[��ZS�;��^=�%9�X�����j��((�M%O)x-�h7+�/Xwr�,+N�B��ss4��w�������MqY�e�+Y��ɮWaf�&�в��QnYY�t�|Ɠ� ���|S��0R��E(q3ԘWd1<Oo����r-F����s!2G�n�������VP;U��z��ɀ�M<DX�+�ֳP�_����躣����`�Y���N���Z�#�N��̠�� �$s���l��rx����� s���w����,V�*x╙dh>��hd�h�9s��9�i�|�G`����Xmb�@j'��ye�E��C��P�q�V���(94�:,ᦆ�g�Z�j�V� ���Ϟ`=T��7@��Z�����__�A���<^og!&1�v5�Xy��Sy3W ��#�Ь����� ����X�+��r�NGE6+�\���Vy\<�(g��5��>�W��O�dNd��K�w���#��t)Z����tӪ9���^WXN9Ϻ!Z�G1�P�ذ~�7e��`K�d�u����D;QE`��C���:�W�3�.��;Q��3�K3�Ί�¼���U��Ň?oJ�u��?�n�fY���ի@��Z}T���$��$�u*;Yؐ}�4>�==w_	�%��)�L��(��2l�.gD,�&�47!=z�4nֲ���s�� �g�QJ�[�?��6�wC�Ev�|]�1�yZ��֩�����{)��-�N�Nu]�'����E�r�
N�/�e
g�L:'J]^S:���2ЧyT�f\є�&�_�k��I�{U���g0�IQ<�h\|��i#}�k�)��˕���B���
���2s��"5�`N\G�M��`�pij��"�f�'~��Q��iS�)O:5,��Z�j�T^��wJE��� u���GL��5�d����M�y����Mx/�#˓��� y��xݥHƽ��_��������(�tn�\��GyOЦH�d��$Y�v�$B�\�$��� t���^�`�hX���(��S����e��\��ӷӅ�#���P]���D�P�
� �Zб�(=H��Q��)�7Who��N�,CCM1	�tN��Q�튑��:1�Qa��8����C�74� ���̼��<>Zp:Z�7�� ɘ̃ɪ.��1+)n%����� (�[<Jw:��2[�Sj��S���~8�Z>@�<�O�Y�ejӝ���0�L��	�#����Ѿg(�44�?�CŨ:�D�x\�E1�}P�6W�j��t(�����#	n����[L��n�5E&a�`:�
f	��}r�[����JkĻy׆�5�����F��3�_Q�P���?�s}TvO�'�|B�KO�#� ���-E��V^ZtA���{,�`�4A�]�CiN����f�Ng��c����E��F��4Ԭk�xL���7�Y�$ �F���-8&�9d�?/�E�v�*9e�V���1S;�.|��Lyv6���<?U0���;'�P�C]BoU�I��w��Fe5�r�fQA54��8.ia�-� �����.��F�L��7�z��g���7��V�%��1��Z�nú�1&�Y�
��� ��g�U���|2�����]�%o���'<9�6!v��rڀ��
qO@j�Zs�7u�6�S����k"�Z�R�.R�Da�ؠPu��h���PJ�G�E.c(�"=Q�L5��:�i�e#:��F�HsY�L��Q��&RtЦJ	��(yW��d�e7�G�9����xS�q�{\/5{'y���LG��F�8ZaA��{uoB��=���}V+s�`�����Ш���O����� ��p�8�+��� Б�vj���Dx5�˘$fa��N�~R��s1.=�95�2q@��D���+�xU���0 ��T���1r�-r�-r�ia9���-Zh���}T�k�(��˨@�Bw4�S�:&6Mۢf1���О)7Ч0���B{\�f[+��Ri��TBf����Pi@V����M4��z:�7Y\:�d�
��4�F�;Ur�;3M8,<����Oh]o��NÓ���� �V�f�M_��'��b��3~�7��������@�SJ�D�p!4p;"�=mâ�bcC#kF�RA�5eYU*T�R��?+�l�8r���u�~[s�ѕ�X��Nq�Ϣi�28��*^ln�8I!򣦅i�{'5�:�(����:�su��(�}�m��7�nְЉ��E��U'nN<Ki����	�ǣ�U#Dі<o�
9K����O�J{�=��i��!����9m�?^ �U�#��ި�Aȧ
�h$�7]��v7I(����R�_#�`�aMn83P���u�#��ZO�k�NaiZ��Q>�d�O_E$��<"�d~�����o�~���f�Cu�»�I|���;�����bƃ�Ny�]I�<�|)��N X)��K���ܧn�j����1������Kː���?�44�,i���)s33�n� 3��IN�$'�������8Zi[���*)oB��R>��p�z(0�]����an;N���:γ+Y��p��=V>.N)��c��<km�ݔB���͒�&Dχ/v����vj��1�^��;4rg�U6����$��T�r���"yƔ��^��a��|��<ҖFf���3$�p����VxVmQ�E�nyZ�u�nVp	�"��Y)7mx9=�H>�?��,C�ďG�!3�����+�� K�溛���+��1���B���3IM�T�6 c@Xn�S���VU��2̳,�2̻v+� �Y�M:�
6�.���Zq˕E)e��6C�â�l��J^�d�q,�J�o�����{ �f�vg�4����MǙp�=kU$�I-�}��g2�>�y@V�jj��<J��ة]�Kw����>�Ǫ�K�F�Q���J�&��V����P�=�؜���?����+��*�SD%���V�HAq��-sZ�W*2|�P��9�#D#��u�!���/ S�ݥ���2'�4/+We���Sż�8��T�N�G�ԩ&Ͳ$�~wB����UJ8v.�Ty��.Dn�V����qv�E4@�͔.�
�0��MP?6hY+i�,~����{�U�V�����@%d@p�W�X�U���u<�9��Z���R���� ��8�ED�����0DeM} ڍ��%R��M򦸷em']m��)����1g�7P��T�x�W'��w�n���(ǲ����u��%"IG��ǻ\�׍EWpp��FB]�Z��Щ<AG'B��[�F��k�mA�k߮5ܙ�ȋV'�[�p�T�R����;&a��,��D�~O�၏F�N�&�8��+IGB�v�k�K&�G�-��Z���3�J���q~�Íw���dJd�W6ʉĠi4��U�|�T��H��,v	��ܮ N�6d�7� �%;dJrr�`_�ݔ�?�x[##;�b�3=��Bܑ��)Zee7�z�f15�2��1��x�?���kAњ��~���$a��	� )O+�������<-����hh��11�rիW�&�J�ұ0�� �TU� ��BjJ)ȧ/��@��7&��&�BN� eŞ|�f���aZy��@yL��|�b1Q�P�K��lV;��f "K_w�{�h?@�]{��#�o�
;���FaJ��_t|���	Y}Bp�]�SJ�Jz(�<����=��١X�9ӗ���Qr`�0�Մ]�������A���.q�g���V�ajsO��n��C��u~�G琓�g|�w�P�FEp�ʻ֭Z�}��'jS���SJ��(�������m��,�����b��P�X�����Z�6�r�WB���C��EfZq:�M7�Z�N^i�/7�4އuJ�4xx��IC�TLQ�D��H��ZB<o���Z.��)^�@�p&� �;"��=��5'��z�,V�>�Q;)�,_�;� ��с�s>�=�,�.��j	���F9���yKUZ8R� ��M�P�<���ê�j�(�4Nu�i8�b�	�~�#O���D�/��]�N<�
Z�QE{�t�����*+�*���/q�x���a��{άf�e$�m� 읫O�6��t�T��}�sl���Û��I�c���*X_��O�A~x��I]TA11Z�S�{'2�"W�.�;���=�&iu,��DWUEQ��k}:��-r=�@�V�E�'o�����Q�X�7ի&GX� =T��AW������K�����b������H��˦�Uߢ�@w)�l�+ł��ga���P��	z��IQ�* �8Z����9��i� .z���l�
H⌄<���YN~��c�tٞ�5�\�f�&KR��յ����Sp��&I�(�����-���*�ڵ|O�<�n/��uS}�oDt(l��?UEU��7_�.��)�5�m6bՂĴ�����!1��H�T�;�S�f��x��IPL8���zAs�,�2ͪ����sX�1���gY�D�?t���(���M#Ci����v3�7[��j��&
�e����Ƌ�Qa"���'��)�a{=�G�G�}�9��!T���Ђ�d cG�b"��+��V�F��PY` �"�����,�d�
����&�7M6Nq��7 �w��'�	��͏)>1�v�>�8�HUuM4�x�o��g����(�h,<y��ԇ��TO�>T	*�5�|���	�.���7�]�U��Z�����Y:�6@��X���j8�&�[�m8虈�R�#�E�:n���jq�"֐�+��N�0��c�GWe�½Q5#�z!,�6������6��s_A���g��D^�t��N���ڻC')�O]��Gt
��ʔ9v��~��)Mf���p+�ȁ�ޚ�V����3�9fV�<�m^�-5�"uL}�fC�;*��Z{t��3&�vV��&���' �lh�q�`�45�����Kb�hQ'�"� �7��۝�Y2l���?��4@)����lS%�s䲢w��u��:,��k�']�k���k�X��`��6���j��l���u�#���І����|j��en���+dⰘC ����J�gT��:	)�ދ���u+fʬ9�n�+U����U�r�aک�.I����jl�;E���+2�+�Ns�X�;����ԄM��.�W�Qю'G�rf婆����A�� 	�n�Fc���<kJf��QU�S;�t6Q;�
A�4D?Ge�p~��6��e�
�QD٥����]��AdA��e
��,i蝅c�'�GE&F�µh;TJnb���r��xuA�
�V�6b�sS�Nz'����6���=O7����Â���v�a�u�]�Mo�u�ͪ�f����!��-u1��~ ���$�a�澺 ��A��Ls�vV, G�W!����05ۅ.	��I�{6Nc���h*��h���5:�a]O�vr<� yi��js�	�k�d���ě�b��}x:�ǽ)�o3m5+��u���p��Q�P]x?n���lM��S��c�~V,�q{�fY�e�gW߾�]�S`�p�G������k�4/�TZ���P��M���E��R9� ����u�\ܷ�+��{��i�n���5�Ƃ�!�WI��a0�b]�a�́���
��g��k2.V�ԘV?�� G��#{7��>�,�b�)�}W�p�m�K9Q9�T�z�c1��v)��3iK~���T^R�(#��q�PF���ȝe�ɲ��ci� N�G�"sx�W�����n�;ˢ�#6�9�����S�q�]�;ʹeR�Jw�mQ���!M�\:��V���b�p��F�Bn�=����1hm5�6�6K;&Pm�7O!XD�)8���dJ̭Z�j��j��)�S��|M%:*��#B蜫�GZ<�7��V�Gn�����5��!$ �頓y�j|~ݻD�N��� ����s ��\���
�	(�@�5��T[�p�2Rӻ|-h�,��5Nzt��'H�N����Gq������x�F-5�,~��T�VB�cEdw趂�X�T��U�޾�T�L�G3��u)6@�Ų���񵘬�2̳,�:/Y�EȽ"S�<
�J�p�J�R�]�n��S��Eu��DݩFKN����@W��s�!&x\<AK��kE<y�-�6���C�x0���k���9rzm��ƻ���|	EU*T��|�#��D*��
+V�꾪S�^�TE�G�mŤ�U�>F���`�|#�̓�8C�]����K�kK�G]��Zq�4��UJ�,�*ʲ��eYVTZ��jՠ�e[&>� l,�� ԕE�NRr��ե��:�E <~%�P}��m���@-�M@�Z߅Ɏ ɒx�V2K�Z������W(�Hw)R�J�
�U�dE�"Ȳ"őQ�J�*T��Ү6� �80�M���C�"�#|��� �^��	<��|!N�\�o�@*�f(h�Gd��腦�E�6���ݕ��xWȥ\+��ׅp>�ȣ��R��*T�R�_-�4��Nn���W�a߮bwO����Q��m��c5#»F?d�EJ�wiR�}&�����u�T�ܦ��D����~%�z��� �����M�hh�#^�ғ�"��H���L?�5׺��Cv�l��F�~���Fc�3!��k��WtܥJ��~���6M{���J��GUz���U!�"�}Q(ڮU*T�R�K*�]�Q?%��W��(�7���18�J,��Q�8�;Vދ	39�0�T}p9��T��D����i�G~JQ��d�,n��������ا�&g��=�S��z �Y�����
T���R�U*�h��*�'x���8zh��9��YVR�����M"�ҚPQ���Unѯu�: ����TĒ#�Q�c\���[�La�Z�r�"�TOE��2\�d[���ɮ˾��ԋS`�X�� 	�,yk��#�� x�xu�W�_��)m��ZuE�h��}UԪ#d}ͧWӻ|/�h�|��P�j���@�<��'h����	�4��@��;~��5B?D�)����>�F��<M�X���h�w)R�l��ZWݥ�D|;� ^�p����T>���_DO�u���<+�R#�u'>�Ewm_q�Q�7Uf�'����5�T�O��GE����R�7+C�!]-������P�B:����+#x��z���V��+j�*D[�k�<+�C���{R�Z�臷�_�u���k��k���W�Aߺ~�d�{ �#��+��������Uƿ���(��5��6�@X��N�i��%j�:&���z'A�p�w����jd��9h�s6)�:_E$�Ce�Vs�E�v��\���j�}|���a�� UR��?���󴏫Sq�_�s�?�� }�>�zh�+�C�Rmu�]n���ʯt*������]����/U�_���׏׉<\���|��֣r��m��'�s(�8Z�5G+}9�D��ɘ��hec9����h��c�p9g���9;���z����=�����᣽�~�=�_�ꇲ�ׇ�u�S쵿D��0T�4��8��#}6_�>��H�s˿��J�*T���hP�s16\�s-��	fFj�8��	��
��r̬����sH
۪��}-F��PZ_R�������'O^*�5zjQ�_Dw�G��OE��S�mQq;���J�*���,�"�}U9x��j�^%�(55�U���k���{+V�*���ވT�_U���'a�xQ��ʿM]5G�o��R'Ӄ��S�;� ~@�J�U�,���Y}xW �+߈_^u<zk��m��\5�t�Z�[{�s}�X�ֽ ��=7ݯ������7D8�许�Pj��j�_R�� �_u�]���~sAfp�f��0�)��S�%9��6�*T�R��eYVU�e@*T���<[�T��(W�}u_�� #       !1A Qaq0�@P���   
!g�8���1�Y�I$�����;MГ��}�n��n�ɞ^��1T�wvH�.z���-�'j��dɖ�'P���)ǁ���S�	g�?z��\�x�"<�� =^N}2�tw�G��N]������0�@��|d��x?&]^a���]��p���|k��,<N���?��e	��I�ën�{!�$�x�g8����/�3��K���G%�#�xY�pr>p �,��2�$�N,��,��?�j���\)���3�XzA��,��=�> ��� ͻ��$�ӫ@�Gm�3�[a��L��80�,��,��$�A�Y� xh��4��u��a_D�/C��<}���&�����XM�G���448�����31;�k�v�Ã����8?��ǉVꇐ��۽�-�O#�I��v��}�����j�Ov��`�G�A>_8�ӆݘ"��G� C�����g����)e����/����<��#���=�_4�Q,~o�����|qe����È-�o��,��.�Yp��q��ɾp��%����8�x6Ӎ���?�'�ٗX1�əԙ6�~��{ �f�����V,��y-x�b9x���y�c�qxo� v9l���?�ݛ?�6,q͘0y��Ɏm�ʄ�fN=L�ܒG\s�1�Hu��|�u��b�p�c�x�z������v�� ����y@l�?���?J}D�_f?b%��G�DZ7��D�˿˗��EN�n��/%����K� ,��p�ok�.��{����^x��<>^�캺�e�}���$[��^8&[�۵/��?�u�b�o�_Y�i�e��3�=/9�y!���u��`)�ë8y��>>^�l{OR
�#���m�8� 88�a���g�m��0��p���J0�"���Ww���k��y�w���b�����h[�9!�M���<���zC����w� ������|p���m��3k�( ��[���|t�����R���Ԉ�U=��H�#�޿��g��e���̡'����)�y��r�q/he�����/m��86���A��n��IDv�@��dYd�v�E ��}�*���%��T�8��X��yy���"UÌ`G(����</\������=�1�Z��~�g��]�]��t]H9D;�w�V� ��ul�[�~ ��3ɇB�J���5�~;[&��8g����2�G���<^��w��V$�>��]˾K��nϱ�B��oK����Y���~+�)�fd?e�����t�dA�.�w����8$����}�
9�	���Wۯ����#G/y$c����u	�\_L��8%��v[zEx��Ե�v�Sx�NLrl����a���͙�$��y��Q�R.����P�V+R�� ʶ�3W��xB���]�X�න�(<������X�	�Z^a��]Q���Ȳ��E03����a�ЦZ��\Hp��Fw�v�։�j�'EQ�m��*�T��Ki�S�N"!��D� 󁘳�!��̼�d���]���j���.J��#w�&��g&\eL['S`�i����f���4���Z(��D�6h�j+�ʴ�,
�Z�r|�rA``Czh,���0�!wP�0��w4���v��fj���*��eV1����e�!���e�qjw��e��� �7��ч�l#��9��>@���Y� H�ͱ�&ӌ���Wn���32�_��bIR~x��=�Nj���]ڻs׻]ps�q���W|u���xe;�L��VޥH2Ou�b�����Ŷ��G�Y��q���cp#�5?~�Ƥ������0�
V�&��JV�6x;��^�x�Ų[����������f��b�����g�p�Y��n�8޽�;z6Gn�k,��ۿżo=���
&ʊ���`��;�9�����d�B�!�)mk���d&��Fq���+}F�����ɴ��n�lJ뇾��@x�٘�X���-��������T6){�`�2"W�l(��cv�v8�����t��r;Ĺ��|,�=�g;�9i�Mx9��bn�U�蟙쁠�m��V?�/o��^�`J݆{��Շ�ɘ~YQ
 J˺�~2w��	\;�-�h�*uF(�J��K��^���b�uf �������5�-���I�ze�=�S��QS8n���IYL�Nx�3�S{%�[�g��)a��>I<�ݟ��ᮉ7�"�Ƈ�"�=Tv	��&z�\��m��� �pGF]����w��:7�n-�V�OBi�̷���˸����i�g�Z�Y��x{�M��m �Ӿ�iu+�;�,X��X�oD
,��/��g�02����T�R�9;�ol%f��)z	��3����֟�4�a��3�a����)�,��y�=�tz�r��$O\6[�g�/s P:�{~ZP�3�?�n[>�8Z�����C�#X����a݌����v]O�z7(c��v�	�&
%5������X~ӯd$���������}��u��� /�g[.[����A��D��,���X�E�/=E
s��9��eƼ�c�f[�1،9����B�؝����r{�X"�g3g��� A� �|1٤;��M�	��#�񅉗� �2���M���.�;�>�=����,���լ�0u��2�D�.��h�)µ��v�g����&Qe�,���ٝ̀��ӌ��+߆]��S��(?_(�&�Qj\Zvȃo�}����@a��s��{l�z�	�rvODr��l��|#���t�ڤy@��w:���22�<��a�];�d ����nˢL5e�w$�	��b�*������Ơ�,qv��$k�Z(/{�1zW���s��b`:̝��J���^���3�ȝ�Z�w����'���ʅ��VN(
 ;�ٻ�l�*�[Cɘ��Ωix)�k9m������Cn��'�`]���Fk,p�Q<�`Vۡ�=��¡��S��x>]�&^l��������K��A�*n[-�澓�ӭ�԰��xX�1�2���N��I٩zB&��r�+1µ���u	����3�n�8
mÝm�C�T&G�m��u5Ì;���(P��9h���|�]ί������k;����"�v;=�1�
�I�,+��������Lw	���v��[v�6��}���vI�3���C#Z7,;�"�zS/l��c<:��
 ��+
�`d���� wu�^�S����䇖�#c��xO_x���ŷX���DY�?���$�N�??���	>��m��!��x�ؾ��9�2��V�@��͑�w\J��gP���5/zK�7�y��;���Z0f;�P�m^1��<H	�Û�-�Ι�vo�=�����g��{1���;������:v���^�2�&ꌐ³^�@~p^�P&Coí">��/Q+� س��:�>��{�52���u/}�DJP�F�T�ʇ���[n�����=���`��*͗y?�ǫ���(8�r�.��0�:T AH�d����0cJ�O�$k ���ܚn�����@��e�g��y�> Xl'\dxw��nΥ��E�/�0P���wb�_dn�d�iZ���Hwi/��ux e���C��[ΰq�-�[��a^��SG����6*%�8�w��oF<�e�Eб� �劼�,o��Zun?�߳n�N�E���v <Y��vO��!9��Q}[�:�M�B_����,	�m!�Y8C)�xJ[��"�cb?�Լ.�<f�(A>)�:��l�}��Bdä�ٛ��c��yd�NY
����۸,4�,�1'oxnv���2|_X��S�l@�ո��Ľ���D�scl�3��\�r�1�ΐE� =t.˻vs�}�KEeԗ�eN��A�x��6���W*u�N]['q��Ylv�'�X�b����l�ዸ�  ,�� �� ���FI:(�X�#t�%u߀�ylE���h� +��C���ճ}-�w`_(�l��{�Ky� �rz��
H\m���B�F[,냌���'�<� �ݷn )v��m���I���z�^W���ˣ�aחg�#�� ͻ��y�����K�I:�ua����m�!;��Aܪ��9��嗕��;���[{���a�$��9}�������
sѷ�^=2��D���L�� 4p�:�ٵ"���	��]�,�"�O9�dmc[���xg?�Gvu�,���-������"W�pϛ��῎��i��'xrq kA�z����÷��C���O�N���2���4���1�x%��A�����C�FE��F�/|ﳍ�����ix=�b}Vi`K���m>5Ь6G����{���pE�<k
yM��n�@A�r!���Ȉ�����kȇ����v�]�6�rG(F�ߑt�׹�m��y$A�]�ep��\G=��0���|���ݗ.My��ؤio�o�GU���>�v�Cj�o|� :��;L�M��(ĲOҸ���ɠdl�ȂH������''�ɧ����|���~���0�:Y�,�Q0�i�0���o��/l�	����f�D��5�=�U�XF�! �1�r}�-�w��ߤ��M��ή���>�K�-/��o����dw�����y|��p���� \�'�R����BK����f�̛��H����;�I8D��Os�I�d��I�j����R� ��ͷ�c�;�m��`�Kd�f�l2���k)�<S���oS4�v�� ����v{�X��}�_0�f�� ��yF��x[2/t���SK�Q�w�2�;Kէ��(��S��yp������A�A�dT�&���fZ ���7-����%`���~q�ǿ�����8�o�ɢV����=قU1��Н< ���=l�;��ާ���nD?�Գ����,R8]&�á��������&쌈/.*c��%��	�����-�����q�+���ymݛ����M�,��%1S2.2�$Vœ��� �!�Ol�xc�zpu8��t��:�k��)ʼ+7]ݡZ�9.Y�=R�k��z���� �����]G���K׻š<��:.�%-l�{#d�vW�� =GE���b]�PX`#��嵝�~":fv#v?���.)ͨ0�o��bN�=�	�l��t��Ϝ�3l��������Fu{b.Ǆ�<��x�-��l�e��Om�<w4&�VM�ib�^v!mp]�!g��4�CP'��1e'���Z�}�l]R���D�Z麭�!뽤�����XvϮ4�+���W\�/A�v���98������E��#���J���A-:���Gs��{}��a����Fc΁����<�c���a��S������0bvۨZǴ:��;�t��S�b�l�Փ�|,�M=	�Nz��D�kt�����tv�M�]u9������dmm࿖�e��u�T��?���0��Nú�������f���V}q��3\'�hN���������wg�_,���;%�[<�����cl�����lr� ���l5�đ�{�n2��>?2�I�S��T2#M���߀x>�P">���/[y��ZXk�� ��[��n�Ep�$V:넂��{q��o_�� ��� x�w���Y1)�a��1!����{zٗ���a,��8eD$�vȀxO�#���!��^H���H�1�ҝ��uz�{�����pU�'�x���ȿa%�����p��{qYr�4�ԗ$�Iģ��B����x�����ݳ2���~���N�'��I�������?�����\ڌ�_��3l&SE�GGr������bYu�pc݋'6~��쟶/���K~yv3oW���W!���[����&N��w�u�刟��;O3:@���Ʊ<d�#t��٭6�������ovy0�!���C`vOK.�z��f>�\��Q������[��5���aƋ,�f���߮'�c�,&>yy��� g-������-���.F�	O�����+љ8;�w�f�������{��2+|�OG$Ӻ=�	sۯ�J]���~,���P�{�]�f�L�c��K�j���5��o��l�끼3��	ݛ����";�~���ϝ�_d�rkjFu�ܿD��C����'��Y����<8~�0F|&.�ǲ�) �Xc3��m�G���K��6�^"� �_���x'Ru=/�6.���c��_�ܿ��q��俓3V+����K�lGK�u˄�ߖb��smἎ�������v3����3=�q ��R�7���	��y�W/SCͧ�˺xC��~`d�s�g�lCcI����C�;���o���Y��\?��8x�p�w~�$6���v���G�ЭJ�����o|��I��ז���Xٓ���]��w�}���cue�L�,� �_&��X���Iո�q�$��m��/�<�D'�����
7�8��ôn��*3�{�q�:#���=w}��tZy:����Ťю,�����>�^�"����埂8d�/�yj����r ��I���v�_���_�T�{�'Q}%�>A}���?Q�������7�ț���{�5�w���X(��c���,G��D���,�ÿ�'�`�8�??vin��S�c�����uh��;�PC�|]Y�Q�B�y��}��@�u#cQ��c�b�� ힷN��ؑ{U�,����s�_�������8Yǉ?��n� �~˿��ZPYM�hJVj�DWj!VonD4�q`��z��a�[������/���,I��� �m��x�n���� ~��&/�.�si�=%�\[��?K$��K�����=���{6�ɟ���/�аq�ł��B7t��D��B�t���� w��>	��?���7o�0��e�;cm�6����~�<���׽�z0��u����G�F;���c���bn�/<��Rx�8�2�Y�������d����Po�P��`g��Cy$���x�bq[�(vQ&<)�,cVgΊblg�u���c1Ԕ{���t=���ؼ�9�Y���c{dN�_����6�_�����x4~��8e�Yg㟎�E����� �t�C�����t]aӨɝ�\�>�L�t\t=q�J��(�ֹ�
��N��1������ЗB�f��M�E��ak6{�7:/�cw�Zn��\��ok��|��Ŗq��{�Y�Oea��Q��:�/�{���D��ح_��N���7�4�g��ӵ~��^���Ѣ����wP�1�rGg�qb�,`�7�]/�T���Wˢ{���y�p~��9���g�&�_&�YF�O� �h�ݐw��ku���WR?�o�o�w���ya�)�2���,w���]����GN��bb1��w�v;o��׬y\�kUf(u;N��ǌ{��C���0x3�p,�,,��՟���~�}YSq�ף���O��;.���b)�� ��i����zzR���1ѯ�d<C��w�Cc�����_RozNx����Ӈ�K��Kv������d~?z����m���8�G��܃��ٞ�����=k�� � 7� fiԿ����A����;������u���:��tt_Ej�Y��2�#;������u?�Yg����y��fz���:�?�[a���q�����c6/��� ��k!���闾���|��|��z�sD^�����G��^@�Z�|/Ӧ�A�'M#�Y�����l�]�޹7�m�Ndf�~��o�~s�o��˯�,����6Y��^"^����r�� �pL��C63`dD�/���^}���� +      !1AQaq 0@��P���`������   ?!�D�G���?�W�^K� ���G���+�X� ���LǄӯE��k�H��`����!��?5�G��-�g�=�>Ͽ��}�~O�zg���׵�G��}�}�c�{Y��j��>ϳ�����`��R¦<R�R�hj��͏�S�8<��F�h�r~X�9��ѷ���6�`Q���G�Sea*]�1� 1$T�P.p��Hn�(Eʄ������=!�ȵ�8F��O��v���Б�w(N�~Ee2`h\	6E�6V��4B�N\�Sw��>F�O脲�оDO��r�m���"8�����kA���,m_G$ݎ�2�F����h���ػ�ݟ	�3.q�5t~F����%�)�$�������k�ɇ�}��d��jO�$��-?�=��.�d]��u�.�S�re+��n�6%p��z���Xr+4�3��er�B�D����YM�J���ڋFA[`&��ɇ��i(L��d����W�'eq��Сck[;�����,%�W�ƫ�jV٩�/���y)�����m$�L�K�I��@����p����,�U�*ɟ4�-�1-[c��I\M1�n��X�/��w-09L��ʖIT2�Ct!9^%`P�bΎ�ZmruܶRBYB������,p�j�tO$��6S� �������>�����V𷶵&��e���>���� �m;�v�ɤ݅W�#%�R� e���3�c���hɓ��F�(�RdBm�ح�҇6O��P܌r2kɚaV�O����Di��b�ҕ_��Bz`�?[��_�TK�	�4�6�����@��0Xp�.�sr��:'(z<I%���#�L��(w�/_&�G��7�����E�t	���1��w�)�'o����.�#�~'0C�+��y<>�Z���k%���E3�[��E�I�$M��N� ј���	�4��EC�놳,����5�e�m�ĩXKѶ�?�O�MN�va��F�H�N�׆�L���bq&�[IX#E�c]9f�w�`'%N��;/4� �>�Y�%��e�˰��7$�D3H����n��F �!�q�%�R��#`5���4vq��Wܞ��9}����,�:C��bW�kaܽ�j�R�l��g������(��Of8��: �t0���12A�,���Z�v�h\�t�Ҁm4�����v�!��8Q�d)�d����#�!bV/i�k�9�y&m�Q���g�gb䬜���z0�e�^�b�}?KK�XdIjĔM��ђ]�P)����;�9,wr�tSטs��<�Q�8�0SP�$���ӳh�־�5����F��X�!"�E��|�lD����|dgdOWZ`��M�;Ez+�����~���B"Y#��h��L���Ky�	,9n ��	�� HI������FH����6�x��ĳփс�7��E�&����d��`�͍n�NQ��I�nW$�j$�~VC1?%�o+�YW!�4�Q)�CYhmKr�Nh�qK:@�,���+с��azs.��_��� n�#Tᜢ\��C|BBu[�Eٜ�F������5�l[5M��$�{	��Y��ng"��B4dwI�.�bR�,�%�E����	@��Ю���C�bW�� #�~����h2}��l��zh��j�7卿��F� "^���,����i�K��p'I�n)+�+$#J��َ�C؁a��>][�c��.%�΃����#/z��ۿ�<F�dK7_�o3�@������ؽ4��,���{ܒ��+��\�Ҋ$�K@��CGɼ�KXM*6"vc�$ݠ�"�9�غ��"S4�$�IΑ�K�ǂN�_�&����K�]v)�l�B�ߩ�bO��/�;��͸�g� Л�Q��l�]D�E��x,Y}%{Ѫ!�5�#�ᣡ�I�������D�gl8�L�`Eņ�Y8l6�}���4��vJ�VU|�V�5B_�[��#�:�vp����9�n�J�e�b� �+�~������wH>��)�6��#���h�	-��^v�u,��ِ9ٝ@�oB�L�k\��� �2�k� ��"����&�79e��1�b��G��D5|C�?)�a7|},ȕf�DA4�S"-`f�h���0o⺨/��'�a=�|��^�1���M�FY�O��Js�&lK��_��'�5I��IxC\������ĆD������"���"lRk"[�:ϓ���MoZ>�d+gs�6l�� �]�=H~-����太5�r�6���!�r%wB�a8ʡ�m�~.������Y
��a�� �f�+B'D	�ȓ�ij��2|)�*����E�r֍d3Vb�,2�'93�`To��8�І^���r_#��`��BBGiz!�ޜRt�-��H/^٤Q7!��"e�,�l�m6h#ҩ����Ad|�<ax#c��ݠ�v�7=�V&F�r��$C~��k�]P��DbIռ��ˠ�MμՖ�.=dOa��I�|��I]z+��=���I�Ԗ��l8����l7�
�I����⩴�i����cr�hkR�Q�����"��H��lE'zǶ!/xϤ����/(�>�+�ˁ4��-��l���wG��d$���e��U�y1VI�uG�����v;O%�{B�� ,{��D����5?�������Wc�,��E�t܇�d�;�;P q׎=��'�}�+�H�	#�	��d���L%��T!t���q���`��]�ٻ�����-�rt�.F� �@��08�&:3v�l�A�Ad��$�����xci�>��˗��Һ��E7���F5�&�w�@m�޺Oa�����/o[Q�bu��p'��sф���*�?euIV�R�5�Ҹ5.Ex��ے��19�cg���Ky�j��F�U����.!14��6�ɸ"�.rM!�d���e�fD�"�H'	��K�C/�_�^�T����h�Z
��ܶ$i)4�K�H^��=x4�Q�w�(��ퟂ�ɹ��;޹�t��%��N�^3�Z<�
Gb䏡A:Oջ�[�m��˒k������\����3���0:.k�B��R�.B���R�z�F�Q����U�C�Z$��=OSa�"�?���˱�� ��b�ˢ��.�������Y&^�� ����(��3YWB�+��Mt�|�)L�b���^�E��$2Z��c�h_�(�5b��1d%v�lJ{���"ͯ.�E�9 Em��W���|PO�"b�����$ܟ�&�,A�=�>�e�Ȣ��O��U�fC���<@�4h�N�K�Ip%���V�A{��j>�� �fӪ>��������A��y6^�E�D{G�A��n�nȕf�$à��$���x�њ_�?5��W�[��dd+�l������W"�F�f��;	���=����"�}��F��R�������M ��ǜ�&i�J�Dr#��t=K{c��mh�FZ�/y'�?4�p\�&՞���Ռr������e�ǥEN?I/9��F����R��B��w���wDY[[��iǒ����*M#�����>(��Ϗh���u�d$ӷ�%�~����Ђ�UDQ�&>]c��{��7�z9#��X�v�\>R"ш&�1�r󲭬Oi�Ux�t.��%h�Tcv~�p.�D.�D?s91�_�H�6!�~�����&M�W#q�ᙒYN�ҋ����̎P�]n�\$0� s�q��,��;���W��I!8JK9$%�z���S�J�G�f�F���7D�I�c{3�sD�'�*�F�#���C�)p!�>F*1/��!	�q��LK7�U{�c>�Q���FD�v >��|7�;S�	3pn�%�M�Fĵ'I��n���
�à����'��u-MSRqh9�}��;<1x:�B�t6 �+��y9�{�n� �c�I�q�H0�D�F�_!��ˡ!�!�*6%Ǻ�F#a&^�b�j4°�D�X�Lƃ{�Ⱥ0����{��H>��/������������n�x����G�?4=����#�&�j7�m�',g�j���+D~�tQ��n�ݝ!7�c��?}�t_|:H�$v7���З#I�[��767���Е��Z����S���'J8�A�\�I1�{�{c:���>���#�������<����B4B�X��p��#���oEtEo�C�� !   !1AQa q�0���   
'�;���;1��dq�捿�Ě���6K� N�?�,{�e�=(���q5��@A�ַD[c[�.�?�4? �DTRIwc�⋰y����_�vz\��!?>�����?�(q�'�  ������_��3阧�$� ,,��G"!Ԇx{r@;*jsd �FHj1`3�k DD"B�YtP��QpOa����rM=|s��%���o�9./� ?���;��׍��������oV�����~m��|����`���mK~�QB   �B�=�螔֧Z���OGLm� d0�k��>�.���d�{b\�B�K�7�Ig��?ŏ�]���]ៗ����}�>�,�����!@I
C<x$k�� ��$	�5��7sv��@��*��F�;Ԑ����ɨ��L�����!�^�+�+_��h}S�Q?�+ㅣ!���,���Ye�}oK�K
8�Z{Pʳ�����a����C�Z� ����g@�pRX�e����x�;.o�̖&�ӪA����|f�ٟs�䜘�G?����� �82(6n�&::Ty��+�<��.~2�ӊR�rF�Bfo�O����\exf���[�&m��~/d�$Yg�?�� ��[o����!�yq�Gĵ��[����������WR�-�`tls�Y����
u<E�#�A���Թ�;;k���p`A���.�^Ayo��� ÿ[fτ9d� ߎ[�~�l�2-�`Og�48?	��Q�_ۋ�Љ9�7='�e��g^V�7	87 <�R�`� ����ρ��Eߙj�q�d:�3
{}� �A�������,-?����,,l#��c���d'π��?ndOdLEo�g����}!���%/^�o{c=�@�f���)��@�-������}%K]����`3zy'Q,M�;�G�<��~3��!�R��=�����$g��Q�� vd� ��؊���쉺��J�yi�s�!�Xr<%g��!׹��'=�3w-� $$��Jh5� �D���������Vj@�
tNu`Eq�Z���f���I��/��ߗe���!4R�O��*ޠy�jpI)��� �,'�8��A���.:��!.���8'lӄ�xq띓�A|�{8���l��=��#h�Dq'W��aߎ�j�ə��bW]]���~���x\'T;w�Y�ˣ�_����|P98x��E�F���nC�Y 7�o=�;8~;=oL�<xG<��� ��33]<���_���s-� -���踼������F�h�6��pƅ0?��p8AF��m������K�� ����e�qn2z�0!��e�H��\���#������{�:��u`���뷊��g�_,��F�m!� ��,���u6#��P2������&��H�~��uh]�|!�Ps>/��/=��[(����x��м"\��9y\/�Kq�| '��#�IO�/�ti�i��!�c��=l.�@T.�����FV�_j*��"7QD?D�� cz��f�~�� 5J������o��� .WJ8/�]�F���q��.%��������t^�O/�n�/�/,p��م�r��;z�.��օ�dζ1���y�����Y�w�Mn������,�����zU	B����VaT|A@L�ז������p�ɷ�2Íw�Q�[l�|K��o,oL��!���iաv�� ;۽@��q4���uk��9j	{��� ��I.>H�5D� 1<�����c�>	z'��Tg���6ҵ��IB�P'� �S��a�V {/�b���Y�4����4��� ��zr�W���R�ٷF]�<���6K���E�Y2��M1��޻��F�5,qؠ����M��L:}�v>�Ӑ��_9sT�w[ ��5��D&B"�)�[�'�$)��z%�$�lT�a���~�ς���]�=��o%�M�x�K�$���Zg%��ě�RK�[	� L-q��[�oG�r]p�� �M5�߅����ݗa��쉹���@$_�R���7/�(�d�3�U� ��ɋ�v�:1A�c��F<�.���H����,���;y�z[ ���Ù��g?[n��+�`�����Ae����o,q�̭�B�a�[�M"��0�C�wu:�O���3O�Ч��6!��ym��ᅿ��[�"H+����R[q3���,=���Q���c�	����I�م����H3VM�L-M��!5���&�������u�D�EJ�L7� ɂ� �[r$�,8H�nՇ�P�kE-�#H����5��9��H��VF0<\��6 ��/����R��<s<	fd5�!�M驮�{�MY
Dl4�W���#MjN�_1��5�|�<�w.�g�$'� �W� ��� ea�d&	_���:� �f����_�z,�#�"���_c?��� �JA��ա������zV9�,>L��P�j�l-?3f�M�ՠJ(��F�b;հ� [�`��� ����� NY����˰����[�q~��� �|%�e⎎��q}��D?+�xW�c`��лRȥ_࿰�ȯ��+y���D��Η���݌�v\ڎa2)'�41��FV��Z?�^�aU��rݐ$>OX �fBk[���!�Ο���7<-���X��"l&hq��Y�<J��q��vO١�_�\���5,7�E~{���~r�r�m�w!.�?�p{nxZ��p��j�����Y����� ۉ���� �gm^�!�ː�-��C�-�^D�>�<��n��.�S�e��^��|���δՙU��|"(R�	e��;T��F�V�'���>�����\#O.l��g�}�:��� ��������ǉ"M+i��ueT�����u�5�;aD�O���'�'V!��'V����2��� �R�/�\�Aq2+1dg(|�z_���Z������dGX[!��=�~&�!A ;P(g�
=I�����}E �Yz����	!:����Σ����!̓��}���1��G��۟��W`a�>���+�	- �6�|�E
�2� �G31�0b���NzpЧ���'�C���ٸ�+l�� &�� g�^Zf��tA�aH��/�rO�e"7�#�<�l���{h�S>'ƻ�_�	��ɏ���U�O�mF�<�׋����0���N�6X/�&��HX�b�!�� C����� ~?ͣ���������|q�M�p�wl9u^=��LfYS���~H�d���@ZG[{�@�ͩs�A� }�x�8����Lz�O`�Ӗ��a���� F`�b�Oı2�`�i����	 �duZ!L=UP��|��B%�2� )~3��|�`#:�u�lt$� z�:)�(�f�f�K1�<�gK9&�<��%P��ȑnQ�S��� H�d�`���pE�>�O]�TL�ȸ!�R�	H��>�YѢoa�a����ˁ��"iG���c�L��9�����n�`�ۍQ#t49�൚a�!da��U�D^D~͗��fh��6]`� �A���Z�3L���dt���(2��f�.��߲�@`�́P9��--dS#%t�^۶S� LB�
F��4���=��\l AA��ȴ���8_�`l�r�ex�3�P�$�D�3���V��r_ ���ZX�8�N��X�\���e�s1��4���Tm/&p�
,�\f)�.G�xk s8C��Պ#xy�Yp�4H�B��¤� ���Wt���>�:͕����fx��w!�$<$E8vzzc��!�B��T��3��b�'�2q!�z�����U
�	��T�282"���[G���U"o����l^��0�ɓ�g���>I$� ��M�E���Bf�X&^�ވ:�I�&�$ 8��)ɭ
X;�|D�Ax�,�1T��
`�ғ,	�s9�(������G����O4�3�R\�H��6�(+���튖��`;�&�/�d���8EQ(9�ۜ�������
 ф÷ �bH�����@V,{�u���HusS�	@*(mt_����%["�3G�u�)ʯ�k�9'Z4��EG�� ��8�������[��]O׉*�_�����i@��W�<`��b�`f,X.�׌.Y�@��� tY��P	^+��q�n�:9lt@�*| ��	΀(%ߗi�f��#4���hN�j�N��l� dͅ���	^u?��a�)�+o��6��0#�Z|B-�ʴ��|e���� ��6�@ݴ[�Bm%\	�a�
�4�:�3ߚ��,�n��i<�C�/fy�Q8m�m���-	U<�9�4&�I�u�Vp%2E�fA�I��qͣ�ZF��С��0�w����4 "Ao��&3$wG~,�9w�&$i���+읠`	#���Vn�T���0z�_��X���,N�{��Kq�A�:�e��(1�p�}���� �s�H&�
j|X��6_��. `���ds����a�N+3G�!��!8� �c�A � �P<o��4-��,���d�����t�H�p�{�ړq���s�S!����]t3����?W����"�����^�"�$� �W�*]Jt��s���^�@����Ђi�ga 0��
*|�o�eٰ	0ɄO�O�z���)G"g��󒟺� ���YCs.�G��Â��c���¾�0Zj&Ef�]��{)��Aɳ��AP\�qҘd��T��	 �.�P[_&�,��s��2��蝕�l��-�%�z��@!݂C4`H�+a�-	���z$қf&bXA����aO>'&� X��|���^��AJ�߹��(P��zBߠLq?�'�l��#	�&Ho��^B-2�ʡD�0$P�T}
_����$��u]Z���K��5���X`a�:�b�]y��c-eu��2R�}��ql�
ߊ��8s
�w�\츊��6P@�Q�#����Z/	����Z�#��Y� ���;�/����&�J�� Q�n�/�[�`�vr�����2��g~p���h(�#j�Ƅ� S8d��ΗN��	�\�y�Eǆ� �|K���ނT«e�/|� �I�C�Ѯ{�����*�G��|�	;� X�� vkW~�����n�[F��|��M�c�?��P�y���6ʹl���&J"I��j�Z2@���⮺����h �[���AZ�������BK(P ~X�"I��*"f�T7�� �#o�� A0���]��B�+���1��a��g�0f$��tD���13! \o�+��H ��zV��E��X!�HN�=3�G���:����@0��ď�:6�]���¨�6\ڦ\��q\�t~%y�u/�S)E�7,�π-#��������oMB�N!�'�4c���&���#�b�ĥ��~ơ������)~�a�ߑ�Ж�0��q�2C1��^�KXKB{����2� �{��ܜ��e��-�X�`��� `p#�O�]@�� �2��L�a��|�8_����u�h���G��;��dK.��ĿE�VI��,$@�χ�����%�M���%@��J���x�2@t7��8a<�����ly�?�6r��n!&t���{t�8H� �DbsR�ߙ�~u�u�ᙛ����/1�v>QN%��Ǚ��#a< ��@Y�7�X��S�!$ �F��X�R�8EIPIi��x.�"��O�Zw~�<�D��l^�q�.I����'�J̜[L�zxk��_��ږ��]��;������Ng������?�ձ�8q2��{nqxv�I���1��N�Z{%c��ݺ|�v ����c�$��7�E?#�NlkR��a����iu�o�������g!����/��K�٫�]�1x����(�`?�}�=��A���1��������<��C4�$=����:wx�K�S��*���Kܒߴ�a9GYO��<���С$D��0�&>�Q� �A��ld~%v�e{�{�� �߄�B�&'S0D��f%�X�d@v���4lkK�flSc�\�;H��Sb�NGz�'� �S@�k,v&��q]/��ۆ�5����8F+��A�p��%�x�Nj���m�C�gS,���om�K��ѹ/Ώ�8��2DN'S�³���U,�Έ��85����#��&��6M�v��^p����Y�`0.2H�T���L-7��r}�Gt 028m���G�ݕ���`�olY�!5�� ��PF=�v��t���{�vg�\<Ǌ1�//-΁��`�2�;��A0@��H��F%>k������eh�7Y��a�cbIT�c�7��`r� K�_�-N�l��K=m:���q) 1r0A'��0E�i��O�� tώ�nܡ��e���Yt�^9��̋�GW�bռB&���
Կ"���ȷ5@���@�Vć�%O@I����� ��c��n�ϲ���ђ��Ԉ�!J�V��@=K锵j�^a�X)�  �zԠڸH�� � �ۯ>!��t�������e��Gخ���v���1�pb�Oah5J��7Q��@WUh� DB��H��
~ �Qm�/`7��e��\�)�vo̱�RN0��d� }B����F����#I.�C�r�F��w��z@�{0�[!������wo�^$mYJb\Jj���Ө؊+oP��2mTd-���r��KW��<���	��% ��F" @��!��$�q/�q�^1��x�Ϯ�⑨�P�ycĸ���;?_�B����i��X���gB;��i$��,8�(Pt�2�LeA1�MKK
 ��҅6t �h��f(���U�Bcc���H8I��`l�L	7\/$Â	r���B�3��QE��Y( B�`[C
x�~	� �'� ��D9�`�Jp.��T�(�#!�¸�r��:8{��5հA#��\I�!� �j1��nn�A�1}�~Gh��y՝3�q%�IW�T�{�!5�h��2��I�,�A�*����HB@ϬsI����-d)�Hӱ(ALW�"����B�c���>Y@<�82�)�S&��-�aV�ɒi�v�WbX�83��{�� ��ߙD��H�m:�	W0���n	�ͧ�0p�Z�u�-��b�iU�]�(���Pomߜ0�:7lG�Z`�#˙8	�
<�m��O��4rv�]#VE������ڥ�0�C��d�67�F,�_ �1!� e��g�?�'� �Ւ0N�L z����?�1��������_=<81K%�0Axc��snW-�;�<�2�(LSY�?8/�����8 �;��&3�m�-����=����1J��� �y.��rw��p}��7?� 7��_�����Ń$����I���n]���_7ep�F&�:�·#���L�4Vl<^�~<��B�L���Pq`��-�]����0�7[��0_�&�w���sdV;,-	w]��#��fV]_�v�M�6���C2W9+C�����P1�@��33�2�|{i/ϗX[/�N��+��*����:��n���^ �9pa����e�	eB�x/�1�.��k������ ���'�[���V�I��HX��@oR5 A�sw��Bh'���[�<��ߟ�B�pJ�,*��-c�D�	q�U�S�v�O�̓��1\�ط���X�P���D�,�6m���>��� g�='&)��] �;F���@��"�`�:��-N�Qv^;l�@8�zR3i��f1��s%�.4aod=8��?l38v���!���z +�1G����`��ӕ�����g��6�/�/���ϣ���(j-�n'�(~�[ _	k���]� nZ\�<�b=$����?��ˍ7ȡα���ZIDj��&5�D��L)�Hh�����v�_+�������+�7�X,Y��bo��[�?��]2X�"&���C�pBc����J�����_-|0��g��>�Lr�2�²e�0FmDh�Vj�f��<��a:6X}b~^�0���$'�ݐ�v����n9z�fg� ���?�21���fz������>���yvM�/��J`��WaB�
�.�WI7���� S�m���#�>9��[���균�w�Uh�I��86������mŭ���q�C$k�򘹳s'䟗�J�c���u���d��ǭ�.��:�y`��mmw�?a���퍇Kw�A�>a ����AiҶ``9�*,����}������<�M!�e>�uW�?ObSB��X$��~� 
[w`�G��N�n,�{�r�8�����{�WV�R/^�F0Q]��f��۶7�>ϒ�e�&#f�Փ�կ����O���8&#��P�<����ؽ#�w��G#!z�Wt�t��Tk�(�)I��8�S�h.�B�k"#��" �X.���� �?���<54��$��5�1��=ۯe��km��������Z���.J~�~7�u�1#���kr� N߫#��a�O��z@�w��	 �Q��-���os�
�.�\��7�@і�&���4�<��1u%`�M|?D����	�C՗s�%�?�OI�`�L�X2�m����8�`��2���HW���%�7�5<�Հ@>Y��w�4By�8�w9�MV��1d�S<�1d��)���@�0Y+ӟ��l�IĮ=;���0�� u��>!�����A��02S��X28�)�۟A;�� �CVʫ�����hb
����O���#��7ߎ>���YK!Vv*f���a��z��S����F�I����š�b��cM�<�tj�@�W�/@n������1�,j��- �L�
�z����M ��C�Vz/�|�	D��2�I�����.Z��r��������~ap�0~�1�J\�~�<]*��@�&�\x�>��VET��;�OuV�Fpu����f�a�.kn�q���QWp��낐��cn=	��c�#]4� �f�F����'_ �Ff�E}ʸ��#��_����6�_��?��Y���4y���o���a�Ѩ�D0�>2� 3���ǝ_� �?�nQ�6�s�I���HwV�:
*���1P|������7�+"��������	����z��XBU�Hp,=ߝ8Z�����4���s�i�ϟ������	⏦��E�o��s����QǗ2��ީ�`�s*��%DY�-%̮�dj�`�p�񇩀`�WK�ưZ����&A��	Xj��Wt-C��=wg#
�&���:�C68��ܣ4��ߖ����"�~� �L��";�;�x��gvMt����d;�,�C�``�)fi`���d��d�1 �۷s*�fNO��u�`�Js~Z��H�wl ��ơ��tؐh؜�A�	}��.z��DP�%�0/I�V��x��Y���� p��t�>�^X���w|���K���px���?P5�� ���p�x�:7R�	�Jrߌ4��&2�;��.��MP// !x��G� `�U���ТV��>�n��úH�9NF�Ʉ!�`4B�$�������?�`𧥒J���.�K?�O�F��,d��3|ùw�ތ!<��?���c|(ۍ�����6ݰzs�SN�N p��C����"��	�1���*��H��h�Ѯ�L��Na��#o�Bx�Ի� �(�L�p3N�/t7��P�񅨮n���� ��^\�Yn��Ay��;�;g:����$��%<�%�k�i�����?�|n�I9?M�_t���:�)�K���F���8�P!����k��5 8�Ĳ��^�Ԥ 9ff p~�����ي�A�;�u���(щ��\1�puO�h<,ޫװ���D:q19��n�`B�rܵ�}��@���?-/�;��G����Hz���C' 4���� T0%N��U?(p0��3.r�t�݉� �59m�I�:%�p �^ݷ�N�����Q`k8+p�]��C���b�7���0[�����&�b�5� �1�5yt�?6uƸZ��������/��i�?� z�9 �Y���@�ۚ������2;� C��@3a�	��~��Mn[��w2�P�L�ac�":�GK�c&�HP��,
����˝
UY�ǖ�����O��u�s����3��ٱ3.��ưm��0�T�#��f�,_쎳M|;:ï��2��!�`*�<5@q���/,b��_�|.�/I< ���O��R�V���� "       !1A Qaq�0@P��   �Կ��72F��*�3#M\�{��8eU0�J����&v�� ��1� O�r��a�r�SS�ԿR�v�ĳQ�,b>��"z��8�(�� ��������3���2M�TE�Tb.�wl��e�&��=� �ծ1W*��UL���(��Y����0���N5r�r��?�� �7ق\���:J�e�����ҭR�C��&{��)���[�@ݕ����i35� ��J����z���r�yn}�b������&�V�b'��� _\k�����M�ϲ�Y�k��U�m�q+sY��{�� ����� �7.���Y��Y���˟�x�g���%>��������� ��mRǆK"��\^?9��8Q]ˎ`M���}����� ���p�|*W��1�̺��`�����5��:���]ne�&qg�����1�������j�k���๺��	ߋ2�4ԫ�S�F�*��������#y�z�g��&3._~?ؽ���|�ʃτB��-�}��Q����{���B�SvC���ׁ�� ��Lp�|��K�u�F���ǆ~qQ�������h�C%���Աq�-���٩\Q�'��<�12'��1V�Ӈ�� ���\6K�xx�L8�����n�z���~��=gP���w��͂?�ty|+�QCd���,�]W�q�+����
b���b3,�񻎳��tg�SS;g�=T�|�xJ����.�uX,i�墠���.�Ov��M���wmW�9t�2�px��\0�j�K���z�y�� ,����p�MÏوr|X��t0����n젨g^⸸��'|@x��D�D0J5���60W=�ȩ�{�˘���;⸶Tn���s����R��\W7?��&g|�  �J!e��Z�bZ�H�s�B��^&�=�G�����uJ"gZc3�G���:�!I���a3c��,M�+�R�s*�	r��P��Cʯ��\�%�bY�}���z�wiCi2�#�I�Y�Pڐ܅6�>�������|c��!Mɫ����C�rB"��E�,�2d�A.��TL9�[� %ܪ�}��2��$�!�ja��帏�8����U@����l�!ĺ��
-D�#Z���TV�*{e�T�1�];�U�xDS�s+QW#�Ul�:��M�d[��tǇ�:%ϯ,��P�u��xj$-�bPÜfW\~p�w3��|e���z㻪�@���e�j\j~�Yժ�VD��,$�2%�R�`<�%H��s�l�\��-��xR\�Pz�:�D�R��u.��ģp���x��̩q���[= gO����C�Aׇ�`w3Ȋ}��a�3Cmq��)��B^�g	�tEdMZG2b3zқ%xAu�=8_�9Q�.�ҍUG��ݭV'�jkz��*?����)b{��ө�����0o|n%@��*
��B"�\�@�Y���4�W��JA�Iv2HX��?�xB��-Dǎ�5�wә�G�Fcdfz��z��W�k�y<��>�X����F�2JU⋁B�+q�BQ��{�A�撦؀��FTx�G��nᗪ����bS�I]ϑ�"�-�����| ����(�bH�ô@Jj����eCG�	J�u���!6!�"4H��D���P|��`j�4I�W�õ'��e63"�.���|\>���SR��� ����W�(��yu(E��� �'_
�2[Ó!"l� ��E4�B�@r=@�`F'�=�r3��r&DKT%�+��E��T�z��.�*wu�Q��!�R?�\�x	��{#�<
[��,U7((��{Q#`bN�Q�pPa��q�9	`�Q�E���?n������LlIJs0� r"�"f9����B-A���HM��J�f�ST^�C^��8|1#`B�ʇ�c���u,n3+#����m0��Gs���)��Ua��0��>�yje�崢\(B�m"�����QL3OɖI�%�-���SߕM�k����e�IXY~x���#��ԥp!vD��0�⻊i�2���0����ؗ�V�l�N�H��SFdX�R@����=ǹK��q�dn.ɂt����f��q":a�-)��K|q��5ŔM��ʉ]�
V̙m��R�Yʪ�G2�K�f��{2�r�l���P����u�~�EaIn��DZ�������k$��P���������c��Z�⑹�5-�!b�3/�����ٳ{Mზft!)L@#2��
@�J�pe,`+�n]�l
	3�U{19���o��Y{�*[�V0�A����YH�+Ǭ���L�D	\���&�I�MjI�=KQ���*c)b� �77���P�0Y��.e
�tֆed؁uq�g"�Je"�_ph$
YIx�d耥y�FT��M��y���k9T���XR,� @�u$9���烫�;QZ�VVK*!�	��!ܧr��sR�OPj7�� VFŐ�#����*�{�e�t����Y�[�l(������T���
� �`+��Q���Ч `�,�eRn5�od��F���Ǫ	7��ي�iT���A���L��Ҵ�	R��L�1I� &��������ܪ�w��������
��`8�I����xV��l\
�Q� }WS2A&� l(�6� ig'�S�J-:M�h]U�Ӂ�(fT���I�����8�8�.F��6d���	��:�n��Vnz��-��a���A�#b�ssR������L��e�=@�˶�����QZ�vB8�}W�Վ�	i�gP�60�����U�?w�*�/�����h�+� �3�����U�
�$�!��3�~����/�_�*Y���A��D�E�q�s	�(����K�5�Df��)p��-ʪ]�j�D�J�����i�m��X��K�;��1k�Wu
��
����N���W�4�`������TI��s�Nxe�oS�_!ȠA/�.g��R� ^��w,+Օ1�[&%z��
�0�{@�J��P�6��N*�%�m:swp1�����q�.�ꎥ¶�I�BD�D�,@AR~J�=��V���Ի��X���V�qe8�E����!ᙒ��>F�2�
���O�d{ñ}��q �)����7�h�"���1J;�(e�0�܋��(��-���+Q��-���@*� ҀDS�pb�A��Ą�`���1EMt1+��F#.���|%V_v�ÝB�T!�T�@����8��f�X����r�l�q����.�P���l�#�;!��Gq��j]�)BZ(�P��7��sd�j	�kOpft���G@y\f~BY�|WQ�	���D)�����).�,a���(���s°j3��)
�P4�wi�?l~qIL�06�d��Z�U*�"@��1�.���a��-�Ha	ƣ�=A�-��&sZ���1/w+Ue�d�~���<~�rԇ�����ᝐ�{H�Q�j��,hC��4ړ��Dj��� �Y��Qy�Y��a���m�U���U�� �z��}rE��
ݦiQI�Жb��5�u.<$��_�Y�:��G���E3,Tox6�^���_�h��Kn>������F��n�@-�П	��$����1�?%�u��RdgD���
����`���	�7?bw�ʼg��Qw��_�R�u�Y.QZ9\�i�,���7=��qlJe*�� 끢_�'�C5:�;�)�4���atj_uQ*�j�Bfz��}�(�ڞ��G���2�R��B1~��0��E����T̫�����h�өQ�����0Z�{�F��|��7	��/<�r�&|�ͽu	������eP���qf	v��=��+`n"���MK<w|<cq�w*a�'��{C�K�}J���ы�c��e�;-m���<s�2� _Os)b,�e�$V�7�ɖ�":��-�<*��{��5��r��}������S�qp)f�y�T���8�M�\��x#Ua���Kq�J���9 @(qa�	p�jQ��~J��^T�q��K��Y��-�M��%��kPjx���n\�(���~Ę�52icޏZ�J�̦I�l_ ����)HV2�C��2f<�&����'��Uq^,.$�Ocs�>�d��2��e55��1a�jk�Ly_r.��%�'i � k�� �ְ�_C���r�O|���7/�R��f33,�>�!}��}�T�ϼg����%J���E�)�ז�p(��7q���AE�|�$c��� �l'���̼�ߕ�q�q�����L�����'$
�=�g���c�w���77w\bW�Q�Ծ:0NbDW0B�3�,�"��������5w7/��0�k-E|e��8�v�U�A�,X1N�Uv�=\��!����YK�Ye�r��q� G�+1(�D%DW2CF7�""ChV�A��/O?�|��7b-O�L� K����B:�����Le���RRض�>��?�%K��]Y�F	c+��`�b��%�j�6䂰dd���S�~�9�:�5Դ��(�r��w*\&�{bzyiC���X\4:*{�D�>�2P�p �mЕ�0�#����2�^Э���A���!�fN�%مG���j$K>���}��x�V���&����;@{��M/�]��ԿpK! ��PE6�T0VTs\S�N��fW"Ua=S�^�W9��X���L������UCh�G%�Y~���# :����Π�#uG�b���q�P�+��W��Wb���U���*`j�8SRv?O�+r�`Tm�S��b@T�&�v�TQv�	q�,�.�Ж��3��U��)("�da_7�ԟ��u.����=#[���}θ�H}�[��lAEM&W��W7����l�JՌ�w���2�[�Bl���R�c,U��_Q�QL��*{�`A�����a�,��p[M�F�bG�I��qoJm�T����p�� ���`�������(2�&�ؓ@!�`�LCr�kT�Xp�o�1��1S�cF� h�Ǆ����)�\]�X�Q�?��ܺ�IR�u1�ʌ��K���±����-O|j�R@�QkY�e�s��ZB����Y߅L����Pz�b��Կsw�8�2�s:I��jZA}�dg��?�_�S�����22��{��v�R�HFHh����up�e	�f\\=x�E"���z���f�~�51�W�u�O�w�o$�SW��TJ�5��ٙ��o�WYf���U4�!mA���3.��r���J������Ϋr��fp���=K:Hg������X@w)���p~� �V��x�l��ٌ�V�w! �*�h��	���R��4g[A���is�Ws3��ܼ1a�1ݙ��n�I�0��/�c�^YfqI�2�?��3�'�4M�B��	��o���L-��S-����nV�7p��ai7QI�m2�zLu+���W�ϸ� ř�F��+������0���*�g���+l̪�1�,KĴ��d1Ylӂ5�̻�{e��ܧs��9���7_��
���ޮg�	�#$���n����&u��2�z%��J� j�=��T��n����U�<o�G�_�r��#z�(B�HE��]����A��{Ul�·+�>B�	Neu5	w�����~�}����#+�ܯ�|�˞���_�C
.�$¸걯�ƹ�f��^��h.���D(��
��]�nS�|[��*vܱ���#[��0]�YZ����+����*��KYp����O��a�}A�*�?SԯPB	����Q��*�j+�bUU��Ww���E:(��x����y�b�=���%Op��x=C�Ǖ� ��#���(6,���`�/�˗��W��{-������B���ޜ0p�q��]K�7;`��Ժ���UP>i��^W2���b d`�@���}'��Q����/���1�(�B��1�0��m��%=�5e������k?a�w)�����k	���E���`sP�P�����VX]�U�*��/pV���o�7�s���fh����d�Y�R��bt(�n��v��b)��^cd�fQ.)��=b�G���v����sr�'�4���01�oDcL�bk��L*��ݐ]�>��UN��~幮�as�P=Ň���M";#P*�SؐQh [��+HbtX,��e�
6��_�}��po���P,��5�,�>� z�qJC��8������ ű[X��j�Ӫ_���'hU�/j��1ew���xa�Y�:"m`]�%�q6&d��k%�E1�� K���l Δ�(�pe;���@B���C8�{R�ԡWf��X� ����L�< I���]���o@{�[W��-a_����/���8x�q�G�l�Lp[h]
�ڏOTt���e��sҧ�:��;Zafo}�Ķ�sp�c�@��b�M%C0���$�����~n�	���i�}�W^�:^�	�;W,���"�A�ߋ�p�<
�Os�"�5 �F�Ǥ�������J�U/��]��Q���1�ԩk	������P��(��k��29��uR���(
{�t{����ߟq��[�����'�� �7���t�5��#�/T���R��H�AW��HL��}�\ m�iaj�!K��:��Bj.�'�X@gQ��n`ZI����t�`�&����>���`~�U���|���.���Z�e��>Ka���'�ca��*Tm��O���<�� �#P��/�%r��aP�b�YXX����p]��_����{YW����W|'��g���������+�>��5ی�qp���*��+�@g�"���Hb��n=�N��^�jH�W=K#V@�#V���5�N��h�ھ��F\8`���8a��"��\�=q������^1�(bg1:���b��=��Ҿ�aj��oT[V���	��G[-�Z�WfL�Z�f,����B���K��x�b#�/�]Y��pqU������gE;��������������#GkK������Q�}�o��mn;	�!��H�WY@�
`EJ/e�p����x_�d��g��^�[�,�x��?������� %���>��h�.��ܮ���n!��S��P�V;��>\���?�� +     !1AQa 0q�@���P����`���   ?�)�=g?�����uB1��P���?�0Vu�B�!v��]���w�3��1� 5��>�a�1
��㩌zTc�,­(V
t`z1��d_� ;_�1��F:����s&;O�&G�����V;��_j��,�c�еcQ���_!v���V�6�׏���v�]��+��4=q�{�z���zcM�
��^
��$���A�C�
��]���>>2��E^�����KK#���G���g�hG���E
�С���?��U�����ہ՗lVo�Lt4��v7�A�㛦M�&�%BV<�
�</���,Q�q�X�:f�O��.$vBh��:	e�P�������
�/���K=/��$)K��"�`����C�v�*3��O�d`BWRDn�eRydN�;��.�� ÑO�$��T��/��Ģ���G�H5���q��[\G&LX�z��a
Z.�%/x�R*�4K)a$���]&����n�'�*��IL�$�t��b
���Ұ��I�Ve�&0F��ݙ#�HW�g򒾐�a��|���4��к<u+�%}2o�D?s�t]����� ���]-�m�evdR�L���r�(�E��%[T���*��?��J��$�+&��)��Q]�+�Z\$� ����O}"%�����-���m�?衦Q��:��>��c$�G���f��2:IV9i� ��Լ�Bl�
[�A���F�p���E2I��z<�@�3I1UHdَ�a��d��l��_<�U�0�X�ɥ��h�P�� ��T�L��v�߸����WFC������FV��E�B�q���lʣ	7+�U�!���i�h�oD�����pP�l(>%�݊6���FeK�*h�G�տ� �T��͖�<N������T��*h���	,���*W�8�xb� ��f���U��������dc��MK�O':�lP:o6�C'	�_BpW�P\"
f�mR�	�wB��ZW-u�+��M?��Y���mR쩫�NxF��Ee	�%B�,����S�v���Ė�1��K�7?�S�I@x���&U�X~��*��S�2�z܂T*�N%��n�P�
7/���I#�T�o(�=��?f�0�a�'gq�(���ΏL���7cP�$�����NÈ�2*�Q2���i���,D��O,�.�^Eh�� U ���;_eUC��E��6�cb��/2*)ݯhR��>D�X��ec�C��F+�¨�YȮ*t>��Hp6��5}Ȣث�#��(l�!��Y ��md�#u�ʜ����R�B�儑�W�%)o"A��ȕ{�<1R^w��T�Jr(H�MK}��L-�(�� >�i��\���*������)"ܤ
�)�$P��6HS
Q�G-{��O<I�DM�B*���@��Ҝ1I����� 7-�hɍ9�$���<��cLi���Rp���8ԻN��z�=��]|zX3!#�E~Q!y6�M�m*�岃������.ں0�ףc&��U]?˿�w�cΊP�&�;�L�F�m�C����᎒Z�1��B�1��l�GG�M�3S��tnaǾ���4b�?��PRd(hQ:��o���B���<����L�+���I;�_�E�F���)��ʣ����1C�.Y�{��WL�!�R�+�ʋ\y��i��"�}hι�=bI�*\����s+D9��4Ӎ,�,3��0��g��!��$���?4���� u�>Ô`�R��H�4��dX���ƻ�r������!\��9i�+�91�x6*;��Qi��vie����m	�\;\>EH�J�_�����

�R�Lώsgb��!���:�i���:�,2�39B�44A^<�53�R�Y�%ك�WS2�t�2���U��V?��o<%�������Iy=a��<B�\�Ⱥ�L���,��Ǒ�]�I�����gL�F��A��K��\��)U��.4��,�:��'\=71��ג�,� ^�w�,4�l3e-��q̓���8AKyC�o���尡����u=�`�d�!׽�����c-U8���*MX���-(EHbO��4��My��6�&␰���%�j����}�)�����de��/�^��Vw#�U���Uܿ��� ��l!\Ə��2���3�:�����1ȇ�2�ai��SN��zq������:�~ Rׄ�k��08:��9���4Y�J�r9x3����U��B�1������@�Ϊ{
�`q:��0��ΨR�c,9n�o��§"�C�8����,ds�<&[�2��\��X6���Y�u�WWB�?شtB�Ő��GÞ��t1��l`�֔HZъ�_���/���
�*�����%�i��<�C����)m��罰����EUF
�u�*U������9��KZ�_��R��7?�e���xj�0^V1��ߩ�*���y1�ߣfl+���VZ!՗�]�4R4IK��ae�>����҂2��tk�w�_B�D�Ŝ��M�)���Y�
�*��:_C���2]��3(�qK^Eqs\4:�G�Vct���3i�Z8O�D��]�+�Hb�����K.̡�GV*�[��f4Ζ�:dvїe�R��[K���񢆅Z���Ҫ~WeW���ɍK���i����{���-��/��WB�nWLi�~���1߷�F4��]3��к�쮋���[Z%�d$ڼn(~��<�嫖�Q�C���Ⱦ��E�G�tˍ�%"�d�U���I..W¬(C6bj8Ky%7�g�R^�u>>;/Dg�X���i[���̗mg�c�>�,�TA5� GUw6fʟ����}�;���yf[� 
)�F{|���u��u2�T��'��,>M�����U�� �T�1�
D9���m�������N"�!~�������������;~D�O"�_Yz&���\Q#�8�W��e�!?e�]��^h{��\	J���Z�#JTZ08h��#�~�)���?����FD-TO�T�R���<m*���O��%�/(p�ط�Լf]�SaU?��1��1ίJȴ#�XP��>����7X�a����Iٔl�,���a�+V�+ ������o��ɒ�B�(�$lQ �qwp�2�b��UC���/asO�<y,�Y�Iv`��4��qh���F;9���άΊ��b����C::��`�pļ��F��75b�MC�2C΋$j�ӹ�BΙ��G�Z��F_E$�i���dtKO�� �Q�Ч��	����yOj[?'�(OU���O�Vn��]�L�q�h�Ӎr;k�Kh�����r\,��3t<�0�ͅ�� BM~�4�+ЛI�2���*`P޼���L��B��/�V>�����]��Tq�EY�G��v#a��\=1�]��c��!iF���La�~�<R�rQr��l� �d�S����d]�t/����z\E�h��[���kL�aU.M�F��I�X\1Nvf��ƙ��j.�D)B��m����첨]-���y� ��9ȣ�+i}�q�����]�B����SUУ�;�-s�p�c��o���e���a�(c��о683Ѹ�q�fAî$g3�T]r�p��Z[WԵZ�ȴr>���NtC���y?�C1��V%���o�f.�t1��ѝ��=rg�D�D�Y��Tn�d�~�����Q�o>�����h��Ej�A�ݣ��U�u*���2��.D.������k�[���W&Vɸ��nic�$4�|+b�d(JB�}t.����0�-��U�xIG*��yjdWL�|�Zeɂ���=V7�Z�,cK��D������1'U���Vjݼj��#�t���b�t���s%��-3�4���\R�"����JI�L{m�x���F-P�A��0#}�08^;6�FX��Hw�A�E�k}3�������PU��T�G>���G�y#�	�(C"�%��@[�����c(!G�Ƭ��J����WL����!Y2X�},�B�����3���=��7W�੷;h�xPr2���	�g���`v�<�����irQf*��Xd�X�y���tP��AZ�Z[�c�c�۟B�ۉN
�,�$�*������8B���Ǒ\dBK�P~ʎ*9�����a���z)#��u,�]O����뒥��mw.�V��e2�y�� �(�}���:�����d�P���
�+"UC�*}� P�ErLqDE���� S
IqQ����Z>�h�.��o"�&hQ���3���]�P����t�\U$����yB��}�,=��,D������hb����qUy.�9h�䠅��=2+i��TV�]6�[u3�+B�e!U���pP8ls��@�E	���d:�T��)B�.����E� EQ�����������z�t�v*A��
4e�R%
SȠ�h�r(ߡ���uȥ���)�1�G��z(���h�.�е�[�����F+
�\}"�0*�]����c��ه��r��E2R<��,Iq�D8%Һ^��ت(9��шq:�z!
�1E<�D�ϑEP�� Q�w���.YE;���y�Ɣ0*��4B��e��1_��*���Y}�&D�b��h��Pʊ��K�}kEЌ��p3z����                                                               insta-puller/cloud_functions/package-lock.json                                                      0000644 0001750 0001750 00000465025 13670726436 023515  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "name": "cloud_functions",
  "version": "1.0.0",
  "lockfileVersion": 1,
  "requires": true,
  "dependencies": {
    "@google-cloud/common": {
      "version": "2.4.0",
      "resolved": "https://registry.npmjs.org/@google-cloud/common/-/common-2.4.0.tgz",
      "integrity": "sha512-zWFjBS35eI9leAHhjfeOYlK5Plcuj/77EzstnrJIZbKgF/nkqjcQuGiMCpzCwOfPyUbz8ZaEOYgbHa759AKbjg==",
      "requires": {
        "@google-cloud/projectify": "^1.0.0",
        "@google-cloud/promisify": "^1.0.0",
        "arrify": "^2.0.0",
        "duplexify": "^3.6.0",
        "ent": "^2.2.0",
        "extend": "^3.0.2",
        "google-auth-library": "^5.5.0",
        "retry-request": "^4.0.0",
        "teeny-request": "^6.0.0"
      }
    },
    "@google-cloud/functions-framework": {
      "version": "1.5.0",
      "resolved": "https://registry.npmjs.org/@google-cloud/functions-framework/-/functions-framework-1.5.0.tgz",
      "integrity": "sha512-u95PdiIapih9a3TTpN1UO0scBr7B+OmqBClYQ1/33dv4zOMvoNqWFxWdLOAjVrC3ThhTh0wtS3qpW5R2096UBw==",
      "requires": {
        "body-parser": "^1.18.3",
        "express": "^4.16.4",
        "minimist": "^1.2.0",
        "on-finished": "^2.3.0"
      }
    },
    "@google-cloud/paginator": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/@google-cloud/paginator/-/paginator-2.0.3.tgz",
      "integrity": "sha512-kp/pkb2p/p0d8/SKUu4mOq8+HGwF8NPzHWkj+VKrIPQPyMRw8deZtrO/OcSiy9C/7bpfU5Txah5ltUNfPkgEXg==",
      "requires": {
        "arrify": "^2.0.0",
        "extend": "^3.0.2"
      }
    },
    "@google-cloud/projectify": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/@google-cloud/projectify/-/projectify-1.0.4.tgz",
      "integrity": "sha512-ZdzQUN02eRsmTKfBj9FDL0KNDIFNjBn/d6tHQmA/+FImH5DO6ZV8E7FzxMgAUiVAUq41RFAkb25p1oHOZ8psfg=="
    },
    "@google-cloud/promisify": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/@google-cloud/promisify/-/promisify-1.0.4.tgz",
      "integrity": "sha512-VccZDcOql77obTnFh0TbNED/6ZbbmHDf8UMNnzO1d5g9V0Htfm4k5cllY8P1tJsRKC3zWYGRLaViiupcgVjBoQ=="
    },
    "@google-cloud/pubsub": {
      "version": "0.18.0",
      "resolved": "https://registry.npmjs.org/@google-cloud/pubsub/-/pubsub-0.18.0.tgz",
      "integrity": "sha512-5on1I+x6jr8/cbqAO6N1GINRA81QlpzdXnonQvTkJrTz5b5FU0f4j7Ea9bdRNV5q/ShsdcIagCAO+0vL2l7thA==",
      "requires": {
        "@google-cloud/common": "^0.16.1",
        "arrify": "^1.0.0",
        "async-each": "^1.0.1",
        "delay": "^2.0.0",
        "duplexify": "^3.5.4",
        "extend": "^3.0.1",
        "google-auto-auth": "^0.9.0",
        "google-gax": "^0.16.0",
        "google-proto-files": "^0.15.0",
        "is": "^3.0.1",
        "lodash.chunk": "^4.2.0",
        "lodash.merge": "^4.6.0",
        "lodash.snakecase": "^4.1.1",
        "protobufjs": "^6.8.1",
        "through2": "^2.0.3",
        "uuid": "^3.1.0"
      },
      "dependencies": {
        "@google-cloud/common": {
          "version": "0.16.2",
          "resolved": "https://registry.npmjs.org/@google-cloud/common/-/common-0.16.2.tgz",
          "integrity": "sha512-GrkaFoj0/oO36pNs4yLmaYhTujuA3i21FdQik99Fd/APix1uhf01VlpJY4lAteTDFLRNkRx6ydEh7OVvmeUHng==",
          "requires": {
            "array-uniq": "^1.0.3",
            "arrify": "^1.0.1",
            "concat-stream": "^1.6.0",
            "create-error-class": "^3.0.2",
            "duplexify": "^3.5.0",
            "ent": "^2.2.0",
            "extend": "^3.0.1",
            "google-auto-auth": "^0.9.0",
            "is": "^3.2.0",
            "log-driver": "1.2.7",
            "methmeth": "^1.1.0",
            "modelo": "^4.2.0",
            "request": "^2.79.0",
            "retry-request": "^3.0.0",
            "split-array-stream": "^1.0.0",
            "stream-events": "^1.0.1",
            "string-format-obj": "^1.1.0",
            "through2": "^2.0.3"
          }
        },
        "arrify": {
          "version": "1.0.1",
          "resolved": "https://registry.npmjs.org/arrify/-/arrify-1.0.1.tgz",
          "integrity": "sha1-iYUI2iIm84DfkEcoRWhJwVAaSw0="
        },
        "concat-stream": {
          "version": "1.6.2",
          "resolved": "https://registry.npmjs.org/concat-stream/-/concat-stream-1.6.2.tgz",
          "integrity": "sha512-27HBghJxjiZtIk3Ycvn/4kbJk/1uZuJFfuPEns6LaEvpvG1f0hTea8lilrouyo9mVc2GWdcEZ8OLoGmSADlrCw==",
          "requires": {
            "buffer-from": "^1.0.0",
            "inherits": "^2.0.3",
            "readable-stream": "^2.2.2",
            "typedarray": "^0.0.6"
          }
        },
        "readable-stream": {
          "version": "2.3.7",
          "resolved": "https://registry.npmjs.org/readable-stream/-/readable-stream-2.3.7.tgz",
          "integrity": "sha512-Ebho8K4jIbHAxnuxi7o42OrZgF/ZTNcsZj6nRKyUmkhLFq8CHItp/fy6hQZuZmP/n3yZ9VBUbp4zz/mX8hmYPw==",
          "requires": {
            "core-util-is": "~1.0.0",
            "inherits": "~2.0.3",
            "isarray": "~1.0.0",
            "process-nextick-args": "~2.0.0",
            "safe-buffer": "~5.1.1",
            "string_decoder": "~1.1.1",
            "util-deprecate": "~1.0.1"
          }
        },
        "retry-request": {
          "version": "3.3.2",
          "resolved": "https://registry.npmjs.org/retry-request/-/retry-request-3.3.2.tgz",
          "integrity": "sha512-WIiGp37XXDC6e7ku3LFoi7LCL/Gs9luGeeqvbPRb+Zl6OQMw4RCRfSaW+aLfE6lhz1R941UavE6Svl3Dm5xGIQ==",
          "requires": {
            "request": "^2.81.0",
            "through2": "^2.0.0"
          }
        },
        "through2": {
          "version": "2.0.5",
          "resolved": "https://registry.npmjs.org/through2/-/through2-2.0.5.tgz",
          "integrity": "sha512-/mrRod8xqpA+IHSLyGCQ2s8SPHiCDEeQJSep1jqLYeEUClOFG2Qsh+4FU6G9VeqpZnGW/Su8LQGc4YKni5rYSQ==",
          "requires": {
            "readable-stream": "~2.3.6",
            "xtend": "~4.0.1"
          }
        }
      }
    },
    "@google-cloud/storage": {
      "version": "4.7.0",
      "resolved": "https://registry.npmjs.org/@google-cloud/storage/-/storage-4.7.0.tgz",
      "integrity": "sha512-f0guAlbeg7Z0m3gKjCfBCu7FG9qS3M3oL5OQQxlvGoPtK7/qg3+W+KQV73O2/sbuS54n0Kh2mvT5K2FWzF5vVQ==",
      "requires": {
        "@google-cloud/common": "^2.1.1",
        "@google-cloud/paginator": "^2.0.0",
        "@google-cloud/promisify": "^1.0.0",
        "arrify": "^2.0.0",
        "compressible": "^2.0.12",
        "concat-stream": "^2.0.0",
        "date-and-time": "^0.13.0",
        "duplexify": "^3.5.0",
        "extend": "^3.0.2",
        "gaxios": "^3.0.0",
        "gcs-resumable-upload": "^2.2.4",
        "hash-stream-validation": "^0.2.2",
        "mime": "^2.2.0",
        "mime-types": "^2.0.8",
        "onetime": "^5.1.0",
        "p-limit": "^2.2.0",
        "pumpify": "^2.0.0",
        "readable-stream": "^3.4.0",
        "snakeize": "^0.1.0",
        "stream-events": "^1.0.1",
        "through2": "^3.0.0",
        "xdg-basedir": "^4.0.0"
      },
      "dependencies": {
        "mime": {
          "version": "2.4.4",
          "resolved": "https://registry.npmjs.org/mime/-/mime-2.4.4.tgz",
          "integrity": "sha512-LRxmNwziLPT828z+4YkNzloCFC2YM4wrB99k+AV5ZbEyfGNWfG8SO1FUXLmLDBSo89NrJZ4DIWeLjy1CHGhMGA=="
        }
      }
    },
    "@mrmlnc/readdir-enhanced": {
      "version": "2.2.1",
      "resolved": "https://registry.npmjs.org/@mrmlnc/readdir-enhanced/-/readdir-enhanced-2.2.1.tgz",
      "integrity": "sha512-bPHp6Ji8b41szTOcaP63VlnbbO5Ny6dwAATtY6JTjh5N2OLrb5Qk/Th5cRkRQhkWCt+EJsYrNB0MiL+Gpn6e3g==",
      "requires": {
        "call-me-maybe": "^1.0.1",
        "glob-to-regexp": "^0.3.0"
      }
    },
    "@nodelib/fs.stat": {
      "version": "1.1.3",
      "resolved": "https://registry.npmjs.org/@nodelib/fs.stat/-/fs.stat-1.1.3.tgz",
      "integrity": "sha512-shAmDyaQC4H92APFoIaVDHCx5bStIocgvbwQyxPRrbUY20V1EYTbSDchWbuwlMG3V17cprZhA6+78JfB+3DTPw=="
    },
    "@protobufjs/aspromise": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/aspromise/-/aspromise-1.1.2.tgz",
      "integrity": "sha1-m4sMxmPWaafY9vXQiToU00jzD78="
    },
    "@protobufjs/base64": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/base64/-/base64-1.1.2.tgz",
      "integrity": "sha512-AZkcAA5vnN/v4PDqKyMR5lx7hZttPDgClv83E//FMNhR2TMcLUhfRUBHCmSl0oi9zMgDDqRUJkSxO3wm85+XLg=="
    },
    "@protobufjs/codegen": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/@protobufjs/codegen/-/codegen-2.0.4.tgz",
      "integrity": "sha512-YyFaikqM5sH0ziFZCN3xDC7zeGaB/d0IUb9CATugHWbd1FRFwWwt4ld4OYMPWu5a3Xe01mGAULCdqhMlPl29Jg=="
    },
    "@protobufjs/eventemitter": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/eventemitter/-/eventemitter-1.1.0.tgz",
      "integrity": "sha1-NVy8mLr61ZePntCV85diHx0Ga3A="
    },
    "@protobufjs/fetch": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/fetch/-/fetch-1.1.0.tgz",
      "integrity": "sha1-upn7WYYUr2VwDBYZ/wbUVLDYTEU=",
      "requires": {
        "@protobufjs/aspromise": "^1.1.1",
        "@protobufjs/inquire": "^1.1.0"
      }
    },
    "@protobufjs/float": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/float/-/float-1.0.2.tgz",
      "integrity": "sha1-Xp4avctz/Ap8uLKR33jIy9l7h9E="
    },
    "@protobufjs/inquire": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/inquire/-/inquire-1.1.0.tgz",
      "integrity": "sha1-/yAOPnzyQp4tyvwRQIKOjMY48Ik="
    },
    "@protobufjs/path": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/path/-/path-1.1.2.tgz",
      "integrity": "sha1-bMKyDFya1q0NzP0hynZz2Nf79o0="
    },
    "@protobufjs/pool": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/pool/-/pool-1.1.0.tgz",
      "integrity": "sha1-Cf0V8tbTq/qbZbw2ZQbWrXhG/1Q="
    },
    "@protobufjs/utf8": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/utf8/-/utf8-1.1.0.tgz",
      "integrity": "sha1-p3c2C1s5oaLlEG+OhY8v0tBgxXA="
    },
    "@tootallnate/once": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/@tootallnate/once/-/once-1.0.0.tgz",
      "integrity": "sha512-KYyTT/T6ALPkIRd2Ge080X/BsXvy9O0hcWTtMWkPvwAwF99+vn6Dv4GzrFT/Nn1LePr+FFDbRXXlqmsy9lw2zA=="
    },
    "@types/bytebuffer": {
      "version": "5.0.40",
      "resolved": "https://registry.npmjs.org/@types/bytebuffer/-/bytebuffer-5.0.40.tgz",
      "integrity": "sha512-h48dyzZrPMz25K6Q4+NCwWaxwXany2FhQg/ErOcdZS1ZpsaDnDMZg8JYLMTGz7uvXKrcKGJUZJlZObyfgdaN9g==",
      "requires": {
        "@types/long": "*",
        "@types/node": "*"
      }
    },
    "@types/long": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/@types/long/-/long-4.0.1.tgz",
      "integrity": "sha512-5tXH6Bx/kNGd3MgffdmP4dy2Z+G4eaXw0SE81Tq3BNadtnMR5/ySMzX4SLEzHJzSmPNn4HIdpQsBvXMUykr58w=="
    },
    "@types/node": {
      "version": "10.17.18",
      "resolved": "https://registry.npmjs.org/@types/node/-/node-10.17.18.tgz",
      "integrity": "sha512-DQ2hl/Jl3g33KuAUOcMrcAOtsbzb+y/ufakzAdeK9z/H/xsvkpbETZZbPNMIiQuk24f5ZRMCcZIViAwyFIiKmg=="
    },
    "abort-controller": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/abort-controller/-/abort-controller-3.0.0.tgz",
      "integrity": "sha512-h8lQ8tacZYnR3vNQTgibj+tODHI5/+l06Au2Pcriv/Gmet0eaj4TwWH41sO9wnHDiQsEj19q0drzdWdeAHtweg==",
      "requires": {
        "event-target-shim": "^5.0.0"
      }
    },
    "accepts": {
      "version": "1.3.7",
      "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.7.tgz",
      "integrity": "sha512-Il80Qs2WjYlJIBNzNkK6KYqlVMTbZLXgHx2oT0pU/fjRHyEp+PEfEPY0R3WCwAGVOtauxh1hOxNgIf5bv7dQpA==",
      "requires": {
        "mime-types": "~2.1.24",
        "negotiator": "0.6.2"
      }
    },
    "acorn": {
      "version": "5.7.4",
      "resolved": "https://registry.npmjs.org/acorn/-/acorn-5.7.4.tgz",
      "integrity": "sha512-1D++VG7BhrtvQpNbBzovKNc1FLGGEE/oGe7b9xJm/RFHMBeUaUGpluV9RLjZa47YFdPcDAenEYuq9pQPcMdLJg=="
    },
    "acorn-es7-plugin": {
      "version": "1.1.7",
      "resolved": "https://registry.npmjs.org/acorn-es7-plugin/-/acorn-es7-plugin-1.1.7.tgz",
      "integrity": "sha1-8u4fMiipDurRJF+asZIusucdM2s="
    },
    "agent-base": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-6.0.0.tgz",
      "integrity": "sha512-j1Q7cSCqN+AwrmDd+pzgqc0/NpC655x2bUf5ZjRIO77DcNBFmh+OgRNzF6OKdCC9RSCb19fGd99+bhXFdkRNqw==",
      "requires": {
        "debug": "4"
      },
      "dependencies": {
        "debug": {
          "version": "4.1.1",
          "resolved": "https://registry.npmjs.org/debug/-/debug-4.1.1.tgz",
          "integrity": "sha512-pYAIzeRo8J6KPEaJ0VWOh5Pzkbw/RetuzehGM7QRRX5he4fPHx2rdKMB256ehJCkX+XRQm16eZLqLNS8RSZXZw==",
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "ms": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
          "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
        }
      }
    },
    "ajv": {
      "version": "4.11.8",
      "resolved": "https://registry.npmjs.org/ajv/-/ajv-4.11.8.tgz",
      "integrity": "sha1-gv+wKynmYq5TvcIK8VlHcGc5xTY=",
      "requires": {
        "co": "^4.6.0",
        "json-stable-stringify": "^1.0.1"
      }
    },
    "ansi-regex": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-2.1.1.tgz",
      "integrity": "sha1-w7M6te42DYbg5ijwRorn7yfWVN8="
    },
    "arr-diff": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/arr-diff/-/arr-diff-4.0.0.tgz",
      "integrity": "sha1-1kYQdP6/7HHn4VI1dhoyml3HxSA="
    },
    "arr-flatten": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/arr-flatten/-/arr-flatten-1.1.0.tgz",
      "integrity": "sha512-L3hKV5R/p5o81R7O02IGnwpDmkp6E982XhtbuwSe3O4qOtMMMtodicASA1Cny2U+aCXcNpml+m4dPsvsJ3jatg=="
    },
    "arr-union": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/arr-union/-/arr-union-3.1.0.tgz",
      "integrity": "sha1-45sJrqne+Gao8gbiiK9jkZuuOcQ="
    },
    "array-filter": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/array-filter/-/array-filter-1.0.0.tgz",
      "integrity": "sha1-uveeYubvTCpMC4MSMtr/7CUfnYM="
    },
    "array-flatten": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/array-flatten/-/array-flatten-1.1.1.tgz",
      "integrity": "sha1-ml9pkFGx5wczKPKgCJaLZOopVdI="
    },
    "array-union": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/array-union/-/array-union-1.0.2.tgz",
      "integrity": "sha1-mjRBDk9OPaI96jdb5b5w8kd47Dk=",
      "requires": {
        "array-uniq": "^1.0.1"
      }
    },
    "array-uniq": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/array-uniq/-/array-uniq-1.0.3.tgz",
      "integrity": "sha1-r2rId6Jcx/dOBYiUdThY39sk/bY="
    },
    "array-unique": {
      "version": "0.3.2",
      "resolved": "https://registry.npmjs.org/array-unique/-/array-unique-0.3.2.tgz",
      "integrity": "sha1-qJS3XUvE9s1nnvMkSp/Y9Gri1Cg="
    },
    "arrify": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/arrify/-/arrify-2.0.1.tgz",
      "integrity": "sha512-3duEwti880xqi4eAMN8AyR4a0ByT90zoYdLlevfrvU43vb0YZwZVfxOgxWrLXXXpyugL0hNZc9G6BiB5B3nUug=="
    },
    "ascli": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/ascli/-/ascli-1.0.1.tgz",
      "integrity": "sha1-vPpZdKYvGOgcq660lzKrSoj5Brw=",
      "requires": {
        "colour": "~0.7.1",
        "optjs": "~3.2.2"
      }
    },
    "asn1": {
      "version": "0.2.4",
      "resolved": "https://registry.npmjs.org/asn1/-/asn1-0.2.4.tgz",
      "integrity": "sha512-jxwzQpLQjSmWXgwaCZE9Nz+glAG01yF1QnWgbhGwHI5A6FRIEY6IVqtHhIepHqI7/kyEyQEagBC5mBEFlIYvdg==",
      "requires": {
        "safer-buffer": "~2.1.0"
      }
    },
    "assert-plus": {
      "version": "0.2.0",
      "resolved": "https://registry.npmjs.org/assert-plus/-/assert-plus-0.2.0.tgz",
      "integrity": "sha1-104bh+ev/A24qttwIfP+SBAasjQ="
    },
    "assign-symbols": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/assign-symbols/-/assign-symbols-1.0.0.tgz",
      "integrity": "sha1-WWZ/QfrdTyDMvCu5a41Pf3jsA2c="
    },
    "async": {
      "version": "2.6.3",
      "resolved": "https://registry.npmjs.org/async/-/async-2.6.3.tgz",
      "integrity": "sha512-zflvls11DCy+dQWzTW2dzuilv8Z5X/pjfmZOWba6TNIVDm+2UDaJmXSOXlasHKfNBs8oo3M0aT50fDEWfKZjXg==",
      "requires": {
        "lodash": "^4.17.14"
      }
    },
    "async-each": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/async-each/-/async-each-1.0.3.tgz",
      "integrity": "sha512-z/WhQ5FPySLdvREByI2vZiTWwCnF0moMJ1hK9YQwDTHKh6I7/uSckMetoRGb5UBZPC1z0jlw+n/XCgjeH7y1AQ=="
    },
    "asynckit": {
      "version": "0.4.0",
      "resolved": "https://registry.npmjs.org/asynckit/-/asynckit-0.4.0.tgz",
      "integrity": "sha1-x57Zf380y48robyXkLzDZkdLS3k="
    },
    "atob": {
      "version": "2.1.2",
      "resolved": "https://registry.npmjs.org/atob/-/atob-2.1.2.tgz",
      "integrity": "sha512-Wm6ukoaOGJi/73p/cl2GvLjTI5JM1k/O14isD73YML8StrH/7/lRFgmg8nICZgD3bZZvjwCGxtMOD3wWNAu8cg=="
    },
    "aws-sign2": {
      "version": "0.6.0",
      "resolved": "https://registry.npmjs.org/aws-sign2/-/aws-sign2-0.6.0.tgz",
      "integrity": "sha1-FDQt0428yU0OW4fXY81jYSwOeU8="
    },
    "aws4": {
      "version": "1.9.1",
      "resolved": "https://registry.npmjs.org/aws4/-/aws4-1.9.1.tgz",
      "integrity": "sha512-wMHVg2EOHaMRxbzgFJ9gtjOOCrI80OHLG14rxi28XwOW8ux6IiEbRCGGGqCtdAIg4FQCbW20k9RsT4y3gJlFug=="
    },
    "axios": {
      "version": "0.19.2",
      "resolved": "https://registry.npmjs.org/axios/-/axios-0.19.2.tgz",
      "integrity": "sha512-fjgm5MvRHLhx+osE2xoekY70AhARk3a6hkN+3Io1jc00jtquGvxYlKlsFUhmUET0V5te6CcZI7lcv2Ym61mjHA==",
      "requires": {
        "follow-redirects": "1.5.10"
      }
    },
    "balanced-match": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/balanced-match/-/balanced-match-1.0.0.tgz",
      "integrity": "sha1-ibTRmasr7kneFk6gK4nORi1xt2c="
    },
    "base": {
      "version": "0.11.2",
      "resolved": "https://registry.npmjs.org/base/-/base-0.11.2.tgz",
      "integrity": "sha512-5T6P4xPgpp0YDFvSWwEZ4NoE3aM4QBQXDzmVbraCkFj8zHM+mba8SyqB5DbZWyR7mYHo6Y7BdQo3MoA4m0TeQg==",
      "requires": {
        "cache-base": "^1.0.1",
        "class-utils": "^0.3.5",
        "component-emitter": "^1.2.1",
        "define-property": "^1.0.0",
        "isobject": "^3.0.1",
        "mixin-deep": "^1.2.0",
        "pascalcase": "^0.1.1"
      },
      "dependencies": {
        "define-property": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-1.0.0.tgz",
          "integrity": "sha1-dp66rz9KY6rTr56NMEybvnm/sOY=",
          "requires": {
            "is-descriptor": "^1.0.0"
          }
        },
        "is-accessor-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-accessor-descriptor/-/is-accessor-descriptor-1.0.0.tgz",
          "integrity": "sha512-m5hnHTkcVsPfqx3AKlyttIPb7J+XykHvJP2B9bZDjlhLIoEq4XoK64Vg7boZlVWYK6LUY94dYPEE7Lh0ZkZKcQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-data-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-data-descriptor/-/is-data-descriptor-1.0.0.tgz",
          "integrity": "sha512-jbRXy1FmtAoCjQkVmIVYwuuqDFUbaOeDjmed1tOGPrsMhtJA4rD9tkgA0F1qJ3gRFRXcHYVkdeaP50Q5rE/jLQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-descriptor": {
          "version": "1.0.2",
          "resolved": "https://registry.npmjs.org/is-descriptor/-/is-descriptor-1.0.2.tgz",
          "integrity": "sha512-2eis5WqQGV7peooDyLmNEPUrps9+SXX5c9pL3xEB+4e9HnGuDa7mB7kHxHw4CbqS9k1T2hOH3miL8n8WtiYVtg==",
          "requires": {
            "is-accessor-descriptor": "^1.0.0",
            "is-data-descriptor": "^1.0.0",
            "kind-of": "^6.0.2"
          }
        }
      }
    },
    "base64-js": {
      "version": "1.3.1",
      "resolved": "https://registry.npmjs.org/base64-js/-/base64-js-1.3.1.tgz",
      "integrity": "sha512-mLQ4i2QO1ytvGWFWmcngKO//JXAQueZvwEKtjgQFM4jIK0kU+ytMfplL8j+n5mspOfjHwoAg+9yhb7BwAHm36g=="
    },
    "bcrypt-pbkdf": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/bcrypt-pbkdf/-/bcrypt-pbkdf-1.0.2.tgz",
      "integrity": "sha1-pDAdOJtqQ/m2f/PKEaP2Y342Dp4=",
      "requires": {
        "tweetnacl": "^0.14.3"
      }
    },
    "bignumber.js": {
      "version": "7.2.1",
      "resolved": "https://registry.npmjs.org/bignumber.js/-/bignumber.js-7.2.1.tgz",
      "integrity": "sha512-S4XzBk5sMB+Rcb/LNcpzXr57VRTxgAvaAEDAl1AwRx27j00hT84O6OkteE7u8UB3NuaaygCRrEpqox4uDOrbdQ=="
    },
    "body-parser": {
      "version": "1.19.0",
      "resolved": "https://registry.npmjs.org/body-parser/-/body-parser-1.19.0.tgz",
      "integrity": "sha512-dhEPs72UPbDnAQJ9ZKMNTP6ptJaionhP5cBb541nXPlW60Jepo9RV/a4fX4XWW9CuFNK22krhrj1+rgzifNCsw==",
      "requires": {
        "bytes": "3.1.0",
        "content-type": "~1.0.4",
        "debug": "2.6.9",
        "depd": "~1.1.2",
        "http-errors": "1.7.2",
        "iconv-lite": "0.4.24",
        "on-finished": "~2.3.0",
        "qs": "6.7.0",
        "raw-body": "2.4.0",
        "type-is": "~1.6.17"
      }
    },
    "boom": {
      "version": "2.10.1",
      "resolved": "https://registry.npmjs.org/boom/-/boom-2.10.1.tgz",
      "integrity": "sha1-OciRjO/1eZ+D+UkqhI9iWt0Mdm8=",
      "requires": {
        "hoek": "2.x.x"
      }
    },
    "brace-expansion": {
      "version": "1.1.11",
      "resolved": "https://registry.npmjs.org/brace-expansion/-/brace-expansion-1.1.11.tgz",
      "integrity": "sha512-iCuPHDFgrHX7H2vEI/5xpz07zSHB00TpugqhmYtVmMO6518mCuRMoOYFldEBl0g187ufozdaHgWKcYFb61qGiA==",
      "requires": {
        "balanced-match": "^1.0.0",
        "concat-map": "0.0.1"
      }
    },
    "braces": {
      "version": "2.3.2",
      "resolved": "https://registry.npmjs.org/braces/-/braces-2.3.2.tgz",
      "integrity": "sha512-aNdbnj9P8PjdXU4ybaWLK2IF3jc/EoDYbC7AazW6to3TRsfXxscC9UXOB5iDiEQrkyIbWp2SLQda4+QAa7nc3w==",
      "requires": {
        "arr-flatten": "^1.1.0",
        "array-unique": "^0.3.2",
        "extend-shallow": "^2.0.1",
        "fill-range": "^4.0.0",
        "isobject": "^3.0.1",
        "repeat-element": "^1.1.2",
        "snapdragon": "^0.8.1",
        "snapdragon-node": "^2.0.1",
        "split-string": "^3.0.2",
        "to-regex": "^3.0.1"
      },
      "dependencies": {
        "extend-shallow": {
          "version": "2.0.1",
          "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-2.0.1.tgz",
          "integrity": "sha1-Ua99YUrZqfYQ6huvu5idaxxWiQ8=",
          "requires": {
            "is-extendable": "^0.1.0"
          }
        }
      }
    },
    "buffer-equal-constant-time": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/buffer-equal-constant-time/-/buffer-equal-constant-time-1.0.1.tgz",
      "integrity": "sha1-+OcRMvf/5uAaXJaXpMbz5I1cyBk="
    },
    "buffer-from": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/buffer-from/-/buffer-from-1.1.1.tgz",
      "integrity": "sha512-MQcXEUbCKtEo7bhqEs6560Hyd4XaovZlO/k9V3hjVUF/zwW7KBVdSK4gIt/bzwS9MbR5qob+F5jusZsb0YQK2A=="
    },
    "bytebuffer": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/bytebuffer/-/bytebuffer-5.0.1.tgz",
      "integrity": "sha1-WC7qSxqHO20CCkjVjfhfC7ps/d0=",
      "requires": {
        "long": "~3"
      },
      "dependencies": {
        "long": {
          "version": "3.2.0",
          "resolved": "https://registry.npmjs.org/long/-/long-3.2.0.tgz",
          "integrity": "sha1-2CG3E4yhy1gcFymQ7xTbIAtcR0s="
        }
      }
    },
    "bytes": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/bytes/-/bytes-3.1.0.tgz",
      "integrity": "sha512-zauLjrfCG+xvoyaqLoV8bLVXXNGC4JqlxFCutSDWA6fJrTo2ZuvLYTqZ7aHBLZSMOopbzwv8f+wZcVzfVTI2Dg=="
    },
    "cache-base": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/cache-base/-/cache-base-1.0.1.tgz",
      "integrity": "sha512-AKcdTnFSWATd5/GCPRxr2ChwIJ85CeyrEyjRHlKxQ56d4XJMGym0uAiKn0xbLOGOl3+yRpOTi484dVCEc5AUzQ==",
      "requires": {
        "collection-visit": "^1.0.0",
        "component-emitter": "^1.2.1",
        "get-value": "^2.0.6",
        "has-value": "^1.0.0",
        "isobject": "^3.0.1",
        "set-value": "^2.0.0",
        "to-object-path": "^0.3.0",
        "union-value": "^1.0.0",
        "unset-value": "^1.0.0"
      }
    },
    "call-me-maybe": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/call-me-maybe/-/call-me-maybe-1.0.1.tgz",
      "integrity": "sha1-JtII6onje1y95gJQoV8DHBak1ms="
    },
    "call-signature": {
      "version": "0.0.2",
      "resolved": "https://registry.npmjs.org/call-signature/-/call-signature-0.0.2.tgz",
      "integrity": "sha1-qEq8glpV70yysCi9dOIFpluaSZY="
    },
    "camelcase": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/camelcase/-/camelcase-2.1.1.tgz",
      "integrity": "sha1-fB0W1nmhu+WcoCys7PsBHiAfWh8="
    },
    "capture-stack-trace": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/capture-stack-trace/-/capture-stack-trace-1.0.1.tgz",
      "integrity": "sha512-mYQLZnx5Qt1JgB1WEiMCf2647plpGeQ2NMR/5L0HNZzGQo4fuSPnK+wjfPnKZV0aiJDgzmWqqkV/g7JD+DW0qw=="
    },
    "caseless": {
      "version": "0.12.0",
      "resolved": "https://registry.npmjs.org/caseless/-/caseless-0.12.0.tgz",
      "integrity": "sha1-G2gcIf+EAzyCZUMJBolCDRhxUdw="
    },
    "class-utils": {
      "version": "0.3.6",
      "resolved": "https://registry.npmjs.org/class-utils/-/class-utils-0.3.6.tgz",
      "integrity": "sha512-qOhPa/Fj7s6TY8H8esGu5QNpMMQxz79h+urzrNYN6mn+9BnxlDGf5QZ+XeCDsxSjPqsSR56XOZOJmpeurnLMeg==",
      "requires": {
        "arr-union": "^3.1.0",
        "define-property": "^0.2.5",
        "isobject": "^3.0.0",
        "static-extend": "^0.1.1"
      },
      "dependencies": {
        "define-property": {
          "version": "0.2.5",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-0.2.5.tgz",
          "integrity": "sha1-w1se+RjsPJkPmlvFe+BKrOxcgRY=",
          "requires": {
            "is-descriptor": "^0.1.0"
          }
        }
      }
    },
    "cliui": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/cliui/-/cliui-3.2.0.tgz",
      "integrity": "sha1-EgYBU3qRbSmUD5NNo7SNWFo5IT0=",
      "requires": {
        "string-width": "^1.0.1",
        "strip-ansi": "^3.0.1",
        "wrap-ansi": "^2.0.0"
      }
    },
    "co": {
      "version": "4.6.0",
      "resolved": "https://registry.npmjs.org/co/-/co-4.6.0.tgz",
      "integrity": "sha1-bqa989hTrlTMuOR7+gvz+QMfsYQ="
    },
    "code-point-at": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/code-point-at/-/code-point-at-1.1.0.tgz",
      "integrity": "sha1-DQcLTQQ6W+ozovGkDi7bPZpMz3c="
    },
    "collection-visit": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/collection-visit/-/collection-visit-1.0.0.tgz",
      "integrity": "sha1-S8A3PBZLwykbTTaMgpzxqApZ3KA=",
      "requires": {
        "map-visit": "^1.0.0",
        "object-visit": "^1.0.0"
      }
    },
    "colour": {
      "version": "0.7.1",
      "resolved": "https://registry.npmjs.org/colour/-/colour-0.7.1.tgz",
      "integrity": "sha1-nLFpkX7F0SwHNtPoaFdG3xyt93g="
    },
    "combined-stream": {
      "version": "1.0.8",
      "resolved": "https://registry.npmjs.org/combined-stream/-/combined-stream-1.0.8.tgz",
      "integrity": "sha512-FQN4MRfuJeHf7cBbBMJFXhKSDq+2kAArBlmRBvcvFE5BB1HZKXtSFASDhdlz9zOYwxh8lDdnvmMOe/+5cdoEdg==",
      "requires": {
        "delayed-stream": "~1.0.0"
      }
    },
    "component-emitter": {
      "version": "1.3.0",
      "resolved": "https://registry.npmjs.org/component-emitter/-/component-emitter-1.3.0.tgz",
      "integrity": "sha512-Rd3se6QB+sO1TwqZjscQrurpEPIfO0/yYnSin6Q/rD3mOutHvUrCAhJub3r90uNb+SESBuE0QYoB90YdfatsRg=="
    },
    "compressible": {
      "version": "2.0.18",
      "resolved": "https://registry.npmjs.org/compressible/-/compressible-2.0.18.tgz",
      "integrity": "sha512-AF3r7P5dWxL8MxyITRMlORQNaOA2IkAFaTr4k7BUumjPtRpGDTZpl0Pb1XCO6JeDCBdp126Cgs9sMxqSjgYyRg==",
      "requires": {
        "mime-db": ">= 1.43.0 < 2"
      }
    },
    "concat-map": {
      "version": "0.0.1",
      "resolved": "https://registry.npmjs.org/concat-map/-/concat-map-0.0.1.tgz",
      "integrity": "sha1-2Klr13/Wjfd5OnMDajug1UBdR3s="
    },
    "concat-stream": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/concat-stream/-/concat-stream-2.0.0.tgz",
      "integrity": "sha512-MWufYdFw53ccGjCA+Ol7XJYpAlW6/prSMzuPOTRnJGcGzuhLn4Scrz7qf6o8bROZ514ltazcIFJZevcfbo0x7A==",
      "requires": {
        "buffer-from": "^1.0.0",
        "inherits": "^2.0.3",
        "readable-stream": "^3.0.2",
        "typedarray": "^0.0.6"
      }
    },
    "configstore": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/configstore/-/configstore-5.0.1.tgz",
      "integrity": "sha512-aMKprgk5YhBNyH25hj8wGt2+D52Sw1DRRIzqBwLp2Ya9mFmY8KPvvtvmna8SxVR9JMZ4kzMD68N22vlaRpkeFA==",
      "requires": {
        "dot-prop": "^5.2.0",
        "graceful-fs": "^4.1.2",
        "make-dir": "^3.0.0",
        "unique-string": "^2.0.0",
        "write-file-atomic": "^3.0.0",
        "xdg-basedir": "^4.0.0"
      }
    },
    "content-disposition": {
      "version": "0.5.3",
      "resolved": "https://registry.npmjs.org/content-disposition/-/content-disposition-0.5.3.tgz",
      "integrity": "sha512-ExO0774ikEObIAEV9kDo50o+79VCUdEB6n6lzKgGwupcVeRlhrj3qGAfwq8G6uBJjkqLrhT0qEYFcWng8z1z0g==",
      "requires": {
        "safe-buffer": "5.1.2"
      }
    },
    "content-type": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/content-type/-/content-type-1.0.4.tgz",
      "integrity": "sha512-hIP3EEPs8tB9AT1L+NUqtwOAps4mk2Zob89MWXMHjHWg9milF/j4osnnQLXBCBFBk/tvIG/tUc9mOUJiPBhPXA=="
    },
    "cookie": {
      "version": "0.4.0",
      "resolved": "https://registry.npmjs.org/cookie/-/cookie-0.4.0.tgz",
      "integrity": "sha512-+Hp8fLp57wnUSt0tY0tHEXh4voZRDnoIrZPqlo3DPiI4y9lwg/jqx+1Om94/W6ZaPDOUbnjOt/99w66zk+l1Xg=="
    },
    "cookie-signature": {
      "version": "1.0.6",
      "resolved": "https://registry.npmjs.org/cookie-signature/-/cookie-signature-1.0.6.tgz",
      "integrity": "sha1-4wOogrNCzD7oylE6eZmXNNqzriw="
    },
    "copy-descriptor": {
      "version": "0.1.1",
      "resolved": "https://registry.npmjs.org/copy-descriptor/-/copy-descriptor-0.1.1.tgz",
      "integrity": "sha1-Z29us8OZl8LuGsOpJP1hJHSPV40="
    },
    "core-js": {
      "version": "2.6.11",
      "resolved": "https://registry.npmjs.org/core-js/-/core-js-2.6.11.tgz",
      "integrity": "sha512-5wjnpaT/3dV+XB4borEsnAYQchn00XSgTAWKDkEqv+K8KevjbzmofK6hfJ9TZIlpj2N0xQpazy7PiRQiWHqzWg=="
    },
    "core-util-is": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/core-util-is/-/core-util-is-1.0.2.tgz",
      "integrity": "sha1-tf1UIgqivFq1eqtxQMlAdUUDwac="
    },
    "create-error-class": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/create-error-class/-/create-error-class-3.0.2.tgz",
      "integrity": "sha1-Br56vvlHo/FKMP1hBnHUAbyot7Y=",
      "requires": {
        "capture-stack-trace": "^1.0.0"
      }
    },
    "cryptiles": {
      "version": "2.0.5",
      "resolved": "https://registry.npmjs.org/cryptiles/-/cryptiles-2.0.5.tgz",
      "integrity": "sha1-O9/s3GCBR8HGcgL6KR59ylnqo7g=",
      "requires": {
        "boom": "2.x.x"
      }
    },
    "crypto-random-string": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/crypto-random-string/-/crypto-random-string-2.0.0.tgz",
      "integrity": "sha512-v1plID3y9r/lPhviJ1wrXpLeyUIGAZ2SHNYTEapm7/8A9nLPoyvVp3RK/EPFqn5kEznyWgYZNsRtYYIWbuG8KA=="
    },
    "dashdash": {
      "version": "1.14.1",
      "resolved": "https://registry.npmjs.org/dashdash/-/dashdash-1.14.1.tgz",
      "integrity": "sha1-hTz6D3y+L+1d4gMmuN1YEDX24vA=",
      "requires": {
        "assert-plus": "^1.0.0"
      },
      "dependencies": {
        "assert-plus": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/assert-plus/-/assert-plus-1.0.0.tgz",
          "integrity": "sha1-8S4PPF13sLHN2RRpQuTpbB5N1SU="
        }
      }
    },
    "date-and-time": {
      "version": "0.13.1",
      "resolved": "https://registry.npmjs.org/date-and-time/-/date-and-time-0.13.1.tgz",
      "integrity": "sha512-/Uge9DJAT+s+oAcDxtBhyR8+sKjUnZbYmyhbmWjTHNtX7B7oWD8YyYdeXcBRbwSj6hVvj+IQegJam7m7czhbFw=="
    },
    "debug": {
      "version": "2.6.9",
      "resolved": "https://registry.npmjs.org/debug/-/debug-2.6.9.tgz",
      "integrity": "sha512-bC7ElrdJaJnPbAP+1EotYvqZsb3ecl5wi6Bfi6BJTUcNowp6cvspg0jXznRTKDjm/E7AdgFBVeAPVMNcKGsHMA==",
      "requires": {
        "ms": "2.0.0"
      }
    },
    "decamelize": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/decamelize/-/decamelize-1.2.0.tgz",
      "integrity": "sha1-9lNNFRSCabIDUue+4m9QH5oZEpA="
    },
    "decode-uri-component": {
      "version": "0.2.0",
      "resolved": "https://registry.npmjs.org/decode-uri-component/-/decode-uri-component-0.2.0.tgz",
      "integrity": "sha1-6zkTMzRYd1y4TNGh+uBiEGu4dUU="
    },
    "define-properties": {
      "version": "1.1.3",
      "resolved": "https://registry.npmjs.org/define-properties/-/define-properties-1.1.3.tgz",
      "integrity": "sha512-3MqfYKj2lLzdMSf8ZIZE/V+Zuy+BgD6f164e8K2w7dgnpKArBDerGYpM46IYYcjnkdPNMjPk9A6VFB8+3SKlXQ==",
      "requires": {
        "object-keys": "^1.0.12"
      }
    },
    "define-property": {
      "version": "2.0.2",
      "resolved": "https://registry.npmjs.org/define-property/-/define-property-2.0.2.tgz",
      "integrity": "sha512-jwK2UV4cnPpbcG7+VRARKTZPUWowwXA8bzH5NP6ud0oeAxyYPuGZUAC7hMugpCdz4BeSZl2Dl9k66CHJ/46ZYQ==",
      "requires": {
        "is-descriptor": "^1.0.2",
        "isobject": "^3.0.1"
      },
      "dependencies": {
        "is-accessor-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-accessor-descriptor/-/is-accessor-descriptor-1.0.0.tgz",
          "integrity": "sha512-m5hnHTkcVsPfqx3AKlyttIPb7J+XykHvJP2B9bZDjlhLIoEq4XoK64Vg7boZlVWYK6LUY94dYPEE7Lh0ZkZKcQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-data-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-data-descriptor/-/is-data-descriptor-1.0.0.tgz",
          "integrity": "sha512-jbRXy1FmtAoCjQkVmIVYwuuqDFUbaOeDjmed1tOGPrsMhtJA4rD9tkgA0F1qJ3gRFRXcHYVkdeaP50Q5rE/jLQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-descriptor": {
          "version": "1.0.2",
          "resolved": "https://registry.npmjs.org/is-descriptor/-/is-descriptor-1.0.2.tgz",
          "integrity": "sha512-2eis5WqQGV7peooDyLmNEPUrps9+SXX5c9pL3xEB+4e9HnGuDa7mB7kHxHw4CbqS9k1T2hOH3miL8n8WtiYVtg==",
          "requires": {
            "is-accessor-descriptor": "^1.0.0",
            "is-data-descriptor": "^1.0.0",
            "kind-of": "^6.0.2"
          }
        }
      }
    },
    "delay": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/delay/-/delay-2.0.0.tgz",
      "integrity": "sha1-kRLq3APk7H4AKXM3iW8nO72R+uU=",
      "requires": {
        "p-defer": "^1.0.0"
      }
    },
    "delayed-stream": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/delayed-stream/-/delayed-stream-1.0.0.tgz",
      "integrity": "sha1-3zrhmayt+31ECqrgsp4icrJOxhk="
    },
    "depd": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/depd/-/depd-1.1.2.tgz",
      "integrity": "sha1-m81S4UwJd2PnSbJ0xDRu0uVgtak="
    },
    "destroy": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/destroy/-/destroy-1.0.4.tgz",
      "integrity": "sha1-l4hXRCxEdJ5CBmE+N5RiBYJqvYA="
    },
    "diff-match-patch": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/diff-match-patch/-/diff-match-patch-1.0.4.tgz",
      "integrity": "sha512-Uv3SW8bmH9nAtHKaKSanOQmj2DnlH65fUpcrMdfdaOxUG02QQ4YGZ8AE7kKOMisF7UqvOlGKVYWRvezdncW9lg=="
    },
    "dir-glob": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/dir-glob/-/dir-glob-2.0.0.tgz",
      "integrity": "sha512-37qirFDz8cA5fimp9feo43fSuRo2gHwaIn6dXL8Ber1dGwUosDrGZeCCXq57WnIqE4aQ+u3eQZzsk1yOzhdwag==",
      "requires": {
        "arrify": "^1.0.1",
        "path-type": "^3.0.0"
      },
      "dependencies": {
        "arrify": {
          "version": "1.0.1",
          "resolved": "https://registry.npmjs.org/arrify/-/arrify-1.0.1.tgz",
          "integrity": "sha1-iYUI2iIm84DfkEcoRWhJwVAaSw0="
        }
      }
    },
    "dot-prop": {
      "version": "5.2.0",
      "resolved": "https://registry.npmjs.org/dot-prop/-/dot-prop-5.2.0.tgz",
      "integrity": "sha512-uEUyaDKoSQ1M4Oq8l45hSE26SnTxL6snNnqvK/VWx5wJhmff5z0FUVJDKDanor/6w3kzE3i7XZOk+7wC0EXr1A==",
      "requires": {
        "is-obj": "^2.0.0"
      }
    },
    "duplexify": {
      "version": "3.7.1",
      "resolved": "https://registry.npmjs.org/duplexify/-/duplexify-3.7.1.tgz",
      "integrity": "sha512-07z8uv2wMyS51kKhD1KsdXJg5WQ6t93RneqRxUHnskXVtlYYkLqM0gqStQZ3pj073g687jPCHrqNfCzawLYh5g==",
      "requires": {
        "end-of-stream": "^1.0.0",
        "inherits": "^2.0.1",
        "readable-stream": "^2.0.0",
        "stream-shift": "^1.0.0"
      },
      "dependencies": {
        "readable-stream": {
          "version": "2.3.7",
          "resolved": "https://registry.npmjs.org/readable-stream/-/readable-stream-2.3.7.tgz",
          "integrity": "sha512-Ebho8K4jIbHAxnuxi7o42OrZgF/ZTNcsZj6nRKyUmkhLFq8CHItp/fy6hQZuZmP/n3yZ9VBUbp4zz/mX8hmYPw==",
          "requires": {
            "core-util-is": "~1.0.0",
            "inherits": "~2.0.3",
            "isarray": "~1.0.0",
            "process-nextick-args": "~2.0.0",
            "safe-buffer": "~5.1.1",
            "string_decoder": "~1.1.1",
            "util-deprecate": "~1.0.1"
          }
        }
      }
    },
    "eastasianwidth": {
      "version": "0.2.0",
      "resolved": "https://registry.npmjs.org/eastasianwidth/-/eastasianwidth-0.2.0.tgz",
      "integrity": "sha512-I88TYZWc9XiYHRQ4/3c5rjjfgkjhLyW2luGIheGERbNQ6OY7yTybanSpDXZa8y7VUP9YmDcYa+eyq4ca7iLqWA=="
    },
    "ecc-jsbn": {
      "version": "0.1.2",
      "resolved": "https://registry.npmjs.org/ecc-jsbn/-/ecc-jsbn-0.1.2.tgz",
      "integrity": "sha1-OoOpBOVDUyh4dMVkt1SThoSamMk=",
      "requires": {
        "jsbn": "~0.1.0",
        "safer-buffer": "^2.1.0"
      }
    },
    "ecdsa-sig-formatter": {
      "version": "1.0.11",
      "resolved": "https://registry.npmjs.org/ecdsa-sig-formatter/-/ecdsa-sig-formatter-1.0.11.tgz",
      "integrity": "sha512-nagl3RYrbNv6kQkeJIpt6NJZy8twLB/2vtz6yN9Z4vRKHN4/QZJIEbqohALSgwKdnksuY3k5Addp5lg8sVoVcQ==",
      "requires": {
        "safe-buffer": "^5.0.1"
      }
    },
    "ee-first": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/ee-first/-/ee-first-1.1.1.tgz",
      "integrity": "sha1-WQxhFWsK4vTwJVcyoViyZrxWsh0="
    },
    "empower": {
      "version": "1.3.1",
      "resolved": "https://registry.npmjs.org/empower/-/empower-1.3.1.tgz",
      "integrity": "sha512-uB6/ViBaawOO/uujFADTK3SqdYlxYNn+N4usK9MRKZ4Hbn/1QSy8k2PezxCA2/+JGbF8vd/eOfghZ90oOSDZCA==",
      "requires": {
        "core-js": "^2.0.0",
        "empower-core": "^1.2.0"
      }
    },
    "empower-core": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/empower-core/-/empower-core-1.2.0.tgz",
      "integrity": "sha512-g6+K6Geyc1o6FdXs9HwrXleCFan7d66G5xSCfSF7x1mJDCes6t0om9lFQG3zOrzh3Bkb/45N0cZ5Gqsf7YrzGQ==",
      "requires": {
        "call-signature": "0.0.2",
        "core-js": "^2.0.0"
      }
    },
    "encodeurl": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/encodeurl/-/encodeurl-1.0.2.tgz",
      "integrity": "sha1-rT/0yG7C0CkyL1oCw6mmBslbP1k="
    },
    "end-of-stream": {
      "version": "1.4.4",
      "resolved": "https://registry.npmjs.org/end-of-stream/-/end-of-stream-1.4.4.tgz",
      "integrity": "sha512-+uw1inIHVPQoaVuHzRyXd21icM+cnt4CzD5rW+NC1wjOUSTOs+Te7FOv7AhN7vS9x/oIyhLP5PR1H+phQAHu5Q==",
      "requires": {
        "once": "^1.4.0"
      }
    },
    "ent": {
      "version": "2.2.0",
      "resolved": "https://registry.npmjs.org/ent/-/ent-2.2.0.tgz",
      "integrity": "sha1-6WQhkyWiHQX0RGai9obtbOX13R0="
    },
    "es6-promise": {
      "version": "4.2.8",
      "resolved": "https://registry.npmjs.org/es6-promise/-/es6-promise-4.2.8.tgz",
      "integrity": "sha512-HJDGx5daxeIvxdBxvG2cb9g4tEvwIk3i8+nhX0yGrYmZUzbkdg8QbDevheDB8gd0//uPj4c1EQua8Q+MViT0/w=="
    },
    "es6-promisify": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/es6-promisify/-/es6-promisify-5.0.0.tgz",
      "integrity": "sha1-UQnWLz5W6pZ8S2NQWu8IKRyKUgM=",
      "requires": {
        "es6-promise": "^4.0.3"
      }
    },
    "escape-html": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/escape-html/-/escape-html-1.0.3.tgz",
      "integrity": "sha1-Aljq5NPQwJdN4cFpGI7wBR0dGYg="
    },
    "espurify": {
      "version": "1.8.1",
      "resolved": "https://registry.npmjs.org/espurify/-/espurify-1.8.1.tgz",
      "integrity": "sha512-ZDko6eY/o+D/gHCWyHTU85mKDgYcS4FJj7S+YD6WIInm7GQ6AnOjmcL4+buFV/JOztVLELi/7MmuGU5NHta0Mg==",
      "requires": {
        "core-js": "^2.0.0"
      }
    },
    "estraverse": {
      "version": "4.3.0",
      "resolved": "https://registry.npmjs.org/estraverse/-/estraverse-4.3.0.tgz",
      "integrity": "sha512-39nnKffWz8xN1BU/2c79n9nB9HDzo0niYUqx6xyqUnyoAnQyyWpOTdZEeiCch8BBu515t4wp9ZmgVfVhn9EBpw=="
    },
    "etag": {
      "version": "1.8.1",
      "resolved": "https://registry.npmjs.org/etag/-/etag-1.8.1.tgz",
      "integrity": "sha1-Qa4u62XvpiJorr/qg6x9eSmbCIc="
    },
    "event-target-shim": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/event-target-shim/-/event-target-shim-5.0.1.tgz",
      "integrity": "sha512-i/2XbnSz/uxRCU6+NdVJgKWDTM427+MqYbkQzD321DuCQJUqOuJKIA0IM2+W2xtYHdKOmZ4dR6fExsd4SXL+WQ=="
    },
    "expand-brackets": {
      "version": "2.1.4",
      "resolved": "https://registry.npmjs.org/expand-brackets/-/expand-brackets-2.1.4.tgz",
      "integrity": "sha1-t3c14xXOMPa27/D4OwQVGiJEliI=",
      "requires": {
        "debug": "^2.3.3",
        "define-property": "^0.2.5",
        "extend-shallow": "^2.0.1",
        "posix-character-classes": "^0.1.0",
        "regex-not": "^1.0.0",
        "snapdragon": "^0.8.1",
        "to-regex": "^3.0.1"
      },
      "dependencies": {
        "define-property": {
          "version": "0.2.5",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-0.2.5.tgz",
          "integrity": "sha1-w1se+RjsPJkPmlvFe+BKrOxcgRY=",
          "requires": {
            "is-descriptor": "^0.1.0"
          }
        },
        "extend-shallow": {
          "version": "2.0.1",
          "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-2.0.1.tgz",
          "integrity": "sha1-Ua99YUrZqfYQ6huvu5idaxxWiQ8=",
          "requires": {
            "is-extendable": "^0.1.0"
          }
        }
      }
    },
    "express": {
      "version": "4.17.1",
      "resolved": "https://registry.npmjs.org/express/-/express-4.17.1.tgz",
      "integrity": "sha512-mHJ9O79RqluphRrcw2X/GTh3k9tVv8YcoyY4Kkh4WDMUYKRZUq0h1o0w2rrrxBqM7VoeUVqgb27xlEMXTnYt4g==",
      "requires": {
        "accepts": "~1.3.7",
        "array-flatten": "1.1.1",
        "body-parser": "1.19.0",
        "content-disposition": "0.5.3",
        "content-type": "~1.0.4",
        "cookie": "0.4.0",
        "cookie-signature": "1.0.6",
        "debug": "2.6.9",
        "depd": "~1.1.2",
        "encodeurl": "~1.0.2",
        "escape-html": "~1.0.3",
        "etag": "~1.8.1",
        "finalhandler": "~1.1.2",
        "fresh": "0.5.2",
        "merge-descriptors": "1.0.1",
        "methods": "~1.1.2",
        "on-finished": "~2.3.0",
        "parseurl": "~1.3.3",
        "path-to-regexp": "0.1.7",
        "proxy-addr": "~2.0.5",
        "qs": "6.7.0",
        "range-parser": "~1.2.1",
        "safe-buffer": "5.1.2",
        "send": "0.17.1",
        "serve-static": "1.14.1",
        "setprototypeof": "1.1.1",
        "statuses": "~1.5.0",
        "type-is": "~1.6.18",
        "utils-merge": "1.0.1",
        "vary": "~1.1.2"
      }
    },
    "extend": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/extend/-/extend-3.0.2.tgz",
      "integrity": "sha512-fjquC59cD7CyW6urNXK0FBufkZcoiGG80wTuPujX590cB5Ttln20E2UB4S/WARVqhXffZl2LNgS+gQdPIIim/g=="
    },
    "extend-shallow": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-3.0.2.tgz",
      "integrity": "sha1-Jqcarwc7OfshJxcnRhMcJwQCjbg=",
      "requires": {
        "assign-symbols": "^1.0.0",
        "is-extendable": "^1.0.1"
      },
      "dependencies": {
        "is-extendable": {
          "version": "1.0.1",
          "resolved": "https://registry.npmjs.org/is-extendable/-/is-extendable-1.0.1.tgz",
          "integrity": "sha512-arnXMxT1hhoKo9k1LZdmlNyJdDDfy2v0fXjFlmok4+i8ul/6WlbVge9bhM74OpNPQPMGUToDtz+KXa1PneJxOA==",
          "requires": {
            "is-plain-object": "^2.0.4"
          }
        }
      }
    },
    "extglob": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/extglob/-/extglob-2.0.4.tgz",
      "integrity": "sha512-Nmb6QXkELsuBr24CJSkilo6UHHgbekK5UiZgfE6UHD3Eb27YC6oD+bhcT+tJ6cl8dmsgdQxnWlcry8ksBIBLpw==",
      "requires": {
        "array-unique": "^0.3.2",
        "define-property": "^1.0.0",
        "expand-brackets": "^2.1.4",
        "extend-shallow": "^2.0.1",
        "fragment-cache": "^0.2.1",
        "regex-not": "^1.0.0",
        "snapdragon": "^0.8.1",
        "to-regex": "^3.0.1"
      },
      "dependencies": {
        "define-property": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-1.0.0.tgz",
          "integrity": "sha1-dp66rz9KY6rTr56NMEybvnm/sOY=",
          "requires": {
            "is-descriptor": "^1.0.0"
          }
        },
        "extend-shallow": {
          "version": "2.0.1",
          "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-2.0.1.tgz",
          "integrity": "sha1-Ua99YUrZqfYQ6huvu5idaxxWiQ8=",
          "requires": {
            "is-extendable": "^0.1.0"
          }
        },
        "is-accessor-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-accessor-descriptor/-/is-accessor-descriptor-1.0.0.tgz",
          "integrity": "sha512-m5hnHTkcVsPfqx3AKlyttIPb7J+XykHvJP2B9bZDjlhLIoEq4XoK64Vg7boZlVWYK6LUY94dYPEE7Lh0ZkZKcQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-data-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-data-descriptor/-/is-data-descriptor-1.0.0.tgz",
          "integrity": "sha512-jbRXy1FmtAoCjQkVmIVYwuuqDFUbaOeDjmed1tOGPrsMhtJA4rD9tkgA0F1qJ3gRFRXcHYVkdeaP50Q5rE/jLQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-descriptor": {
          "version": "1.0.2",
          "resolved": "https://registry.npmjs.org/is-descriptor/-/is-descriptor-1.0.2.tgz",
          "integrity": "sha512-2eis5WqQGV7peooDyLmNEPUrps9+SXX5c9pL3xEB+4e9HnGuDa7mB7kHxHw4CbqS9k1T2hOH3miL8n8WtiYVtg==",
          "requires": {
            "is-accessor-descriptor": "^1.0.0",
            "is-data-descriptor": "^1.0.0",
            "kind-of": "^6.0.2"
          }
        }
      }
    },
    "extsprintf": {
      "version": "1.3.0",
      "resolved": "https://registry.npmjs.org/extsprintf/-/extsprintf-1.3.0.tgz",
      "integrity": "sha1-lpGEQOMEGnpBT4xS48V06zw+HgU="
    },
    "fast-glob": {
      "version": "2.2.7",
      "resolved": "https://registry.npmjs.org/fast-glob/-/fast-glob-2.2.7.tgz",
      "integrity": "sha512-g1KuQwHOZAmOZMuBtHdxDtju+T2RT8jgCC9aANsbpdiDDTSnjgfuVsIBNKbUeJI3oKMRExcfNDtJl4OhbffMsw==",
      "requires": {
        "@mrmlnc/readdir-enhanced": "^2.2.1",
        "@nodelib/fs.stat": "^1.1.2",
        "glob-parent": "^3.1.0",
        "is-glob": "^4.0.0",
        "merge2": "^1.2.3",
        "micromatch": "^3.1.10"
      }
    },
    "fast-text-encoding": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/fast-text-encoding/-/fast-text-encoding-1.0.1.tgz",
      "integrity": "sha512-x4FEgaz3zNRtJfLFqJmHWxkMDDvXVtaznj2V9jiP8ACUJrUgist4bP9FmDL2Vew2Y9mEQI/tG4GqabaitYp9CQ=="
    },
    "fill-range": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/fill-range/-/fill-range-4.0.0.tgz",
      "integrity": "sha1-1USBHUKPmOsGpj3EAtJAPDKMOPc=",
      "requires": {
        "extend-shallow": "^2.0.1",
        "is-number": "^3.0.0",
        "repeat-string": "^1.6.1",
        "to-regex-range": "^2.1.0"
      },
      "dependencies": {
        "extend-shallow": {
          "version": "2.0.1",
          "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-2.0.1.tgz",
          "integrity": "sha1-Ua99YUrZqfYQ6huvu5idaxxWiQ8=",
          "requires": {
            "is-extendable": "^0.1.0"
          }
        }
      }
    },
    "finalhandler": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/finalhandler/-/finalhandler-1.1.2.tgz",
      "integrity": "sha512-aAWcW57uxVNrQZqFXjITpW3sIUQmHGG3qSb9mUah9MgMC4NeWhNOlNjXEYq3HjRAvL6arUviZGGJsBg6z0zsWA==",
      "requires": {
        "debug": "2.6.9",
        "encodeurl": "~1.0.2",
        "escape-html": "~1.0.3",
        "on-finished": "~2.3.0",
        "parseurl": "~1.3.3",
        "statuses": "~1.5.0",
        "unpipe": "~1.0.0"
      }
    },
    "follow-redirects": {
      "version": "1.5.10",
      "resolved": "https://registry.npmjs.org/follow-redirects/-/follow-redirects-1.5.10.tgz",
      "integrity": "sha512-0V5l4Cizzvqt5D44aTXbFZz+FtyXV1vrDN6qrelxtfYQKW0KO0W2T/hkE8xvGa/540LkZlkaUjO4ailYTFtHVQ==",
      "requires": {
        "debug": "=3.1.0"
      },
      "dependencies": {
        "debug": {
          "version": "3.1.0",
          "resolved": "https://registry.npmjs.org/debug/-/debug-3.1.0.tgz",
          "integrity": "sha512-OX8XqP7/1a9cqkxYw2yXss15f26NKWBpDXQd0/uK/KPqdQhxbPa994hnzjcE2VqQpDslf55723cKPUOGSmMY3g==",
          "requires": {
            "ms": "2.0.0"
          }
        }
      }
    },
    "for-in": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/for-in/-/for-in-1.0.2.tgz",
      "integrity": "sha1-gQaNKVqBQuwKxybG4iAMMPttXoA="
    },
    "forever-agent": {
      "version": "0.6.1",
      "resolved": "https://registry.npmjs.org/forever-agent/-/forever-agent-0.6.1.tgz",
      "integrity": "sha1-+8cfDEGt6zf5bFd60e1C2P2sypE="
    },
    "form-data": {
      "version": "2.1.4",
      "resolved": "https://registry.npmjs.org/form-data/-/form-data-2.1.4.tgz",
      "integrity": "sha1-M8GDrPGTJ27KqYFDpp6Uv+4XUNE=",
      "requires": {
        "asynckit": "^0.4.0",
        "combined-stream": "^1.0.5",
        "mime-types": "^2.1.12"
      }
    },
    "forwarded": {
      "version": "0.1.2",
      "resolved": "https://registry.npmjs.org/forwarded/-/forwarded-0.1.2.tgz",
      "integrity": "sha1-mMI9qxF1ZXuMBXPozszZGw/xjIQ="
    },
    "fragment-cache": {
      "version": "0.2.1",
      "resolved": "https://registry.npmjs.org/fragment-cache/-/fragment-cache-0.2.1.tgz",
      "integrity": "sha1-QpD60n8T6Jvn8zeZxrxaCr//DRk=",
      "requires": {
        "map-cache": "^0.2.2"
      }
    },
    "fresh": {
      "version": "0.5.2",
      "resolved": "https://registry.npmjs.org/fresh/-/fresh-0.5.2.tgz",
      "integrity": "sha1-PYyt2Q2XZWn6g1qx+OSyOhBWBac="
    },
    "fs.realpath": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/fs.realpath/-/fs.realpath-1.0.0.tgz",
      "integrity": "sha1-FQStJSMVjKpA20onh8sBQRmU6k8="
    },
    "gaxios": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-3.0.2.tgz",
      "integrity": "sha512-cLOetrsKOBLPwjzVyFzirYaGjrhtYjbKUHp6fQpsio2HH8Mil35JTFQLgkV5D3CCXV7Gnd5V69/m4C9rMBi9bA==",
      "requires": {
        "abort-controller": "^3.0.0",
        "extend": "^3.0.2",
        "https-proxy-agent": "^5.0.0",
        "is-stream": "^2.0.0",
        "node-fetch": "^2.3.0"
      }
    },
    "gcp-metadata": {
      "version": "3.5.0",
      "resolved": "https://registry.npmjs.org/gcp-metadata/-/gcp-metadata-3.5.0.tgz",
      "integrity": "sha512-ZQf+DLZ5aKcRpLzYUyBS3yo3N0JSa82lNDO8rj3nMSlovLcz2riKFBsYgDzeXcv75oo5eqB2lx+B14UvPoCRnA==",
      "requires": {
        "gaxios": "^2.1.0",
        "json-bigint": "^0.3.0"
      },
      "dependencies": {
        "gaxios": {
          "version": "2.3.4",
          "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-2.3.4.tgz",
          "integrity": "sha512-US8UMj8C5pRnao3Zykc4AAVr+cffoNKRTg9Rsf2GiuZCW69vgJj38VK2PzlPuQU73FZ/nTk9/Av6/JGcE1N9vA==",
          "requires": {
            "abort-controller": "^3.0.0",
            "extend": "^3.0.2",
            "https-proxy-agent": "^5.0.0",
            "is-stream": "^2.0.0",
            "node-fetch": "^2.3.0"
          }
        }
      }
    },
    "gcs-resumable-upload": {
      "version": "2.3.3",
      "resolved": "https://registry.npmjs.org/gcs-resumable-upload/-/gcs-resumable-upload-2.3.3.tgz",
      "integrity": "sha512-sf896I5CC/1AxeaGfSFg3vKMjUq/r+A3bscmVzZm10CElyRanN0XwPu/MxeIO4LSP+9uF6yKzXvNsaTsMXUG6Q==",
      "requires": {
        "abort-controller": "^3.0.0",
        "configstore": "^5.0.0",
        "gaxios": "^2.0.0",
        "google-auth-library": "^5.0.0",
        "pumpify": "^2.0.0",
        "stream-events": "^1.0.4"
      },
      "dependencies": {
        "gaxios": {
          "version": "2.3.4",
          "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-2.3.4.tgz",
          "integrity": "sha512-US8UMj8C5pRnao3Zykc4AAVr+cffoNKRTg9Rsf2GiuZCW69vgJj38VK2PzlPuQU73FZ/nTk9/Av6/JGcE1N9vA==",
          "requires": {
            "abort-controller": "^3.0.0",
            "extend": "^3.0.2",
            "https-proxy-agent": "^5.0.0",
            "is-stream": "^2.0.0",
            "node-fetch": "^2.3.0"
          }
        }
      }
    },
    "get-value": {
      "version": "2.0.6",
      "resolved": "https://registry.npmjs.org/get-value/-/get-value-2.0.6.tgz",
      "integrity": "sha1-3BXKHGcjh8p2vTesCjlbogQqLCg="
    },
    "getpass": {
      "version": "0.1.7",
      "resolved": "https://registry.npmjs.org/getpass/-/getpass-0.1.7.tgz",
      "integrity": "sha1-Xv+OPmhNVprkyysSgmBOi6YhSfo=",
      "requires": {
        "assert-plus": "^1.0.0"
      },
      "dependencies": {
        "assert-plus": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/assert-plus/-/assert-plus-1.0.0.tgz",
          "integrity": "sha1-8S4PPF13sLHN2RRpQuTpbB5N1SU="
        }
      }
    },
    "glob": {
      "version": "7.1.6",
      "resolved": "https://registry.npmjs.org/glob/-/glob-7.1.6.tgz",
      "integrity": "sha512-LwaxwyZ72Lk7vZINtNNrywX0ZuLyStrdDtabefZKAY5ZGJhVtgdznluResxNmPitE0SAO+O26sWTHeKSI2wMBA==",
      "requires": {
        "fs.realpath": "^1.0.0",
        "inflight": "^1.0.4",
        "inherits": "2",
        "minimatch": "^3.0.4",
        "once": "^1.3.0",
        "path-is-absolute": "^1.0.0"
      }
    },
    "glob-parent": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/glob-parent/-/glob-parent-3.1.0.tgz",
      "integrity": "sha1-nmr2KZ2NO9K9QEMIMr0RPfkGxa4=",
      "requires": {
        "is-glob": "^3.1.0",
        "path-dirname": "^1.0.0"
      },
      "dependencies": {
        "is-glob": {
          "version": "3.1.0",
          "resolved": "https://registry.npmjs.org/is-glob/-/is-glob-3.1.0.tgz",
          "integrity": "sha1-e6WuJCF4BKxwcHuWkiVnSGzD6Eo=",
          "requires": {
            "is-extglob": "^2.1.0"
          }
        }
      }
    },
    "glob-to-regexp": {
      "version": "0.3.0",
      "resolved": "https://registry.npmjs.org/glob-to-regexp/-/glob-to-regexp-0.3.0.tgz",
      "integrity": "sha1-jFoUlNIGbFcMw7/kSWF1rMTVAqs="
    },
    "globby": {
      "version": "8.0.2",
      "resolved": "https://registry.npmjs.org/globby/-/globby-8.0.2.tgz",
      "integrity": "sha512-yTzMmKygLp8RUpG1Ymu2VXPSJQZjNAZPD4ywgYEaG7e4tBJeUQBO8OpXrf1RCNcEs5alsoJYPAMiIHP0cmeC7w==",
      "requires": {
        "array-union": "^1.0.1",
        "dir-glob": "2.0.0",
        "fast-glob": "^2.0.2",
        "glob": "^7.1.2",
        "ignore": "^3.3.5",
        "pify": "^3.0.0",
        "slash": "^1.0.0"
      },
      "dependencies": {
        "pify": {
          "version": "3.0.0",
          "resolved": "https://registry.npmjs.org/pify/-/pify-3.0.0.tgz",
          "integrity": "sha1-5aSs0sEB/fPZpNB/DbxNtJ3SgXY="
        }
      }
    },
    "google-auth-library": {
      "version": "5.10.1",
      "resolved": "https://registry.npmjs.org/google-auth-library/-/google-auth-library-5.10.1.tgz",
      "integrity": "sha512-rOlaok5vlpV9rSiUu5EpR0vVpc+PhN62oF4RyX/6++DG1VsaulAFEMlDYBLjJDDPI6OcNOCGAKy9UVB/3NIDXg==",
      "requires": {
        "arrify": "^2.0.0",
        "base64-js": "^1.3.0",
        "ecdsa-sig-formatter": "^1.0.11",
        "fast-text-encoding": "^1.0.0",
        "gaxios": "^2.1.0",
        "gcp-metadata": "^3.4.0",
        "gtoken": "^4.1.0",
        "jws": "^4.0.0",
        "lru-cache": "^5.0.0"
      },
      "dependencies": {
        "gaxios": {
          "version": "2.3.4",
          "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-2.3.4.tgz",
          "integrity": "sha512-US8UMj8C5pRnao3Zykc4AAVr+cffoNKRTg9Rsf2GiuZCW69vgJj38VK2PzlPuQU73FZ/nTk9/Av6/JGcE1N9vA==",
          "requires": {
            "abort-controller": "^3.0.0",
            "extend": "^3.0.2",
            "https-proxy-agent": "^5.0.0",
            "is-stream": "^2.0.0",
            "node-fetch": "^2.3.0"
          }
        }
      }
    },
    "google-auto-auth": {
      "version": "0.9.7",
      "resolved": "https://registry.npmjs.org/google-auto-auth/-/google-auto-auth-0.9.7.tgz",
      "integrity": "sha512-Nro7aIFrL2NP0G7PoGrJqXGMZj8AjdBOcbZXRRm/8T3w08NUHIiNN3dxpuUYzDsZizslH+c8e+7HXL8vh3JXTQ==",
      "requires": {
        "async": "^2.3.0",
        "gcp-metadata": "^0.6.1",
        "google-auth-library": "^1.3.1",
        "request": "^2.79.0"
      },
      "dependencies": {
        "agent-base": {
          "version": "4.3.0",
          "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-4.3.0.tgz",
          "integrity": "sha512-salcGninV0nPrwpGNn4VTXBb1SOuXQBiqbrNXoeizJsHrsL6ERFM2Ne3JUSBWRE6aeNJI2ROP/WEEIDUiDe3cg==",
          "requires": {
            "es6-promisify": "^5.0.0"
          }
        },
        "axios": {
          "version": "0.18.1",
          "resolved": "https://registry.npmjs.org/axios/-/axios-0.18.1.tgz",
          "integrity": "sha512-0BfJq4NSfQXd+SkFdrvFbG7addhYSBA2mQwISr46pD6E5iqkWg02RAs8vyTT/j0RTnoYmeXauBuSv1qKwR179g==",
          "requires": {
            "follow-redirects": "1.5.10",
            "is-buffer": "^2.0.2"
          }
        },
        "debug": {
          "version": "3.2.6",
          "resolved": "https://registry.npmjs.org/debug/-/debug-3.2.6.tgz",
          "integrity": "sha512-mel+jf7nrtEl5Pn1Qx46zARXKDpBbvzezse7p7LqINmdoIk8PYP5SySaxEmYv6TZ0JyEKA1hsCId6DIhgITtWQ==",
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "gaxios": {
          "version": "1.8.4",
          "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-1.8.4.tgz",
          "integrity": "sha512-BoENMnu1Gav18HcpV9IleMPZ9exM+AvUjrAOV4Mzs/vfz2Lu/ABv451iEXByKiMPn2M140uul1txXCg83sAENw==",
          "requires": {
            "abort-controller": "^3.0.0",
            "extend": "^3.0.2",
            "https-proxy-agent": "^2.2.1",
            "node-fetch": "^2.3.0"
          }
        },
        "gcp-metadata": {
          "version": "0.6.3",
          "resolved": "https://registry.npmjs.org/gcp-metadata/-/gcp-metadata-0.6.3.tgz",
          "integrity": "sha512-MSmczZctbz91AxCvqp9GHBoZOSbJKAICV7Ow/AIWSJZRrRchUd5NL1b2P4OfP+4m490BEUPhhARfpHdqCxuCvg==",
          "requires": {
            "axios": "^0.18.0",
            "extend": "^3.0.1",
            "retry-axios": "0.3.2"
          }
        },
        "google-auth-library": {
          "version": "1.6.1",
          "resolved": "https://registry.npmjs.org/google-auth-library/-/google-auth-library-1.6.1.tgz",
          "integrity": "sha512-jYiWC8NA9n9OtQM7ANn0Tk464do9yhKEtaJ72pKcaBiEwn4LwcGYIYOfwtfsSm3aur/ed3tlSxbmg24IAT6gAg==",
          "requires": {
            "axios": "^0.18.0",
            "gcp-metadata": "^0.6.3",
            "gtoken": "^2.3.0",
            "jws": "^3.1.5",
            "lodash.isstring": "^4.0.1",
            "lru-cache": "^4.1.3",
            "retry-axios": "^0.3.2"
          }
        },
        "google-p12-pem": {
          "version": "1.0.4",
          "resolved": "https://registry.npmjs.org/google-p12-pem/-/google-p12-pem-1.0.4.tgz",
          "integrity": "sha512-SwLAUJqUfTB2iS+wFfSS/G9p7bt4eWcc2LyfvmUXe7cWp6p3mpxDo6LLI29MXdU6wvPcQ/up298X7GMC5ylAlA==",
          "requires": {
            "node-forge": "^0.8.0",
            "pify": "^4.0.0"
          }
        },
        "gtoken": {
          "version": "2.3.3",
          "resolved": "https://registry.npmjs.org/gtoken/-/gtoken-2.3.3.tgz",
          "integrity": "sha512-EaB49bu/TCoNeQjhCYKI/CurooBKkGxIqFHsWABW0b25fobBYVTMe84A8EBVVZhl8emiUdNypil9huMOTmyAnw==",
          "requires": {
            "gaxios": "^1.0.4",
            "google-p12-pem": "^1.0.0",
            "jws": "^3.1.5",
            "mime": "^2.2.0",
            "pify": "^4.0.0"
          }
        },
        "https-proxy-agent": {
          "version": "2.2.4",
          "resolved": "https://registry.npmjs.org/https-proxy-agent/-/https-proxy-agent-2.2.4.tgz",
          "integrity": "sha512-OmvfoQ53WLjtA9HeYP9RNrWMJzzAz1JGaSFr1nijg0PVR1JaD/xbJq1mdEIIlxGpXp9eSe/O2LgU9DJmTPd0Eg==",
          "requires": {
            "agent-base": "^4.3.0",
            "debug": "^3.1.0"
          }
        },
        "jwa": {
          "version": "1.4.1",
          "resolved": "https://registry.npmjs.org/jwa/-/jwa-1.4.1.tgz",
          "integrity": "sha512-qiLX/xhEEFKUAJ6FiBMbes3w9ATzyk5W7Hvzpa/SLYdxNtng+gcurvrI7TbACjIXlsJyr05/S1oUhZrc63evQA==",
          "requires": {
            "buffer-equal-constant-time": "1.0.1",
            "ecdsa-sig-formatter": "1.0.11",
            "safe-buffer": "^5.0.1"
          }
        },
        "jws": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/jws/-/jws-3.2.2.tgz",
          "integrity": "sha512-YHlZCB6lMTllWDtSPHz/ZXTsi8S00usEV6v1tjq8tOUZzw7DpSDWVXjXDre6ed1w/pd495ODpHZYSdkRTsa0HA==",
          "requires": {
            "jwa": "^1.4.1",
            "safe-buffer": "^5.0.1"
          }
        },
        "lru-cache": {
          "version": "4.1.5",
          "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-4.1.5.tgz",
          "integrity": "sha512-sWZlbEP2OsHNkXrMl5GYk/jKk70MBng6UU4YI/qGDYbgf6YbP4EvmqISbXCoJiRKs+1bSpFHVgQxvJ17F2li5g==",
          "requires": {
            "pseudomap": "^1.0.2",
            "yallist": "^2.1.2"
          }
        },
        "mime": {
          "version": "2.4.4",
          "resolved": "https://registry.npmjs.org/mime/-/mime-2.4.4.tgz",
          "integrity": "sha512-LRxmNwziLPT828z+4YkNzloCFC2YM4wrB99k+AV5ZbEyfGNWfG8SO1FUXLmLDBSo89NrJZ4DIWeLjy1CHGhMGA=="
        },
        "ms": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
          "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
        },
        "node-forge": {
          "version": "0.8.5",
          "resolved": "https://registry.npmjs.org/node-forge/-/node-forge-0.8.5.tgz",
          "integrity": "sha512-vFMQIWt+J/7FLNyKouZ9TazT74PRV3wgv9UT4cRjC8BffxFbKXkgIWR42URCPSnHm/QDz6BOlb2Q0U4+VQT67Q=="
        },
        "yallist": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/yallist/-/yallist-2.1.2.tgz",
          "integrity": "sha1-HBH5IY8HYImkfdUS+TxmmaaoHVI="
        }
      }
    },
    "google-gax": {
      "version": "0.16.1",
      "resolved": "https://registry.npmjs.org/google-gax/-/google-gax-0.16.1.tgz",
      "integrity": "sha512-eP7UUkKvaHmmvCrr+rxzkIOeEKOnXmoib7/AkENDAuqlC9T2+lWlzwpthDRnitQcV8SblDMzsk73YPMPCDwPyQ==",
      "requires": {
        "duplexify": "^3.5.4",
        "extend": "^3.0.0",
        "globby": "^8.0.0",
        "google-auto-auth": "^0.10.0",
        "google-proto-files": "^0.15.0",
        "grpc": "^1.10.0",
        "is-stream-ended": "^0.1.0",
        "lodash": "^4.17.2",
        "protobufjs": "^6.8.0",
        "through2": "^2.0.3"
      },
      "dependencies": {
        "agent-base": {
          "version": "4.3.0",
          "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-4.3.0.tgz",
          "integrity": "sha512-salcGninV0nPrwpGNn4VTXBb1SOuXQBiqbrNXoeizJsHrsL6ERFM2Ne3JUSBWRE6aeNJI2ROP/WEEIDUiDe3cg==",
          "requires": {
            "es6-promisify": "^5.0.0"
          }
        },
        "axios": {
          "version": "0.18.1",
          "resolved": "https://registry.npmjs.org/axios/-/axios-0.18.1.tgz",
          "integrity": "sha512-0BfJq4NSfQXd+SkFdrvFbG7addhYSBA2mQwISr46pD6E5iqkWg02RAs8vyTT/j0RTnoYmeXauBuSv1qKwR179g==",
          "requires": {
            "follow-redirects": "1.5.10",
            "is-buffer": "^2.0.2"
          }
        },
        "debug": {
          "version": "3.2.6",
          "resolved": "https://registry.npmjs.org/debug/-/debug-3.2.6.tgz",
          "integrity": "sha512-mel+jf7nrtEl5Pn1Qx46zARXKDpBbvzezse7p7LqINmdoIk8PYP5SySaxEmYv6TZ0JyEKA1hsCId6DIhgITtWQ==",
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "gaxios": {
          "version": "1.8.4",
          "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-1.8.4.tgz",
          "integrity": "sha512-BoENMnu1Gav18HcpV9IleMPZ9exM+AvUjrAOV4Mzs/vfz2Lu/ABv451iEXByKiMPn2M140uul1txXCg83sAENw==",
          "requires": {
            "abort-controller": "^3.0.0",
            "extend": "^3.0.2",
            "https-proxy-agent": "^2.2.1",
            "node-fetch": "^2.3.0"
          }
        },
        "gcp-metadata": {
          "version": "0.6.3",
          "resolved": "https://registry.npmjs.org/gcp-metadata/-/gcp-metadata-0.6.3.tgz",
          "integrity": "sha512-MSmczZctbz91AxCvqp9GHBoZOSbJKAICV7Ow/AIWSJZRrRchUd5NL1b2P4OfP+4m490BEUPhhARfpHdqCxuCvg==",
          "requires": {
            "axios": "^0.18.0",
            "extend": "^3.0.1",
            "retry-axios": "0.3.2"
          }
        },
        "google-auth-library": {
          "version": "1.6.1",
          "resolved": "https://registry.npmjs.org/google-auth-library/-/google-auth-library-1.6.1.tgz",
          "integrity": "sha512-jYiWC8NA9n9OtQM7ANn0Tk464do9yhKEtaJ72pKcaBiEwn4LwcGYIYOfwtfsSm3aur/ed3tlSxbmg24IAT6gAg==",
          "requires": {
            "axios": "^0.18.0",
            "gcp-metadata": "^0.6.3",
            "gtoken": "^2.3.0",
            "jws": "^3.1.5",
            "lodash.isstring": "^4.0.1",
            "lru-cache": "^4.1.3",
            "retry-axios": "^0.3.2"
          }
        },
        "google-auto-auth": {
          "version": "0.10.1",
          "resolved": "https://registry.npmjs.org/google-auto-auth/-/google-auto-auth-0.10.1.tgz",
          "integrity": "sha512-iIqSbY7Ypd32mnHGbYctp80vZzXoDlvI9gEfvtl3kmyy5HzOcrZCIGCBdSlIzRsg7nHpQiHE3Zl6Ycur6TSodQ==",
          "requires": {
            "async": "^2.3.0",
            "gcp-metadata": "^0.6.1",
            "google-auth-library": "^1.3.1",
            "request": "^2.79.0"
          }
        },
        "google-p12-pem": {
          "version": "1.0.4",
          "resolved": "https://registry.npmjs.org/google-p12-pem/-/google-p12-pem-1.0.4.tgz",
          "integrity": "sha512-SwLAUJqUfTB2iS+wFfSS/G9p7bt4eWcc2LyfvmUXe7cWp6p3mpxDo6LLI29MXdU6wvPcQ/up298X7GMC5ylAlA==",
          "requires": {
            "node-forge": "^0.8.0",
            "pify": "^4.0.0"
          }
        },
        "gtoken": {
          "version": "2.3.3",
          "resolved": "https://registry.npmjs.org/gtoken/-/gtoken-2.3.3.tgz",
          "integrity": "sha512-EaB49bu/TCoNeQjhCYKI/CurooBKkGxIqFHsWABW0b25fobBYVTMe84A8EBVVZhl8emiUdNypil9huMOTmyAnw==",
          "requires": {
            "gaxios": "^1.0.4",
            "google-p12-pem": "^1.0.0",
            "jws": "^3.1.5",
            "mime": "^2.2.0",
            "pify": "^4.0.0"
          }
        },
        "https-proxy-agent": {
          "version": "2.2.4",
          "resolved": "https://registry.npmjs.org/https-proxy-agent/-/https-proxy-agent-2.2.4.tgz",
          "integrity": "sha512-OmvfoQ53WLjtA9HeYP9RNrWMJzzAz1JGaSFr1nijg0PVR1JaD/xbJq1mdEIIlxGpXp9eSe/O2LgU9DJmTPd0Eg==",
          "requires": {
            "agent-base": "^4.3.0",
            "debug": "^3.1.0"
          }
        },
        "jwa": {
          "version": "1.4.1",
          "resolved": "https://registry.npmjs.org/jwa/-/jwa-1.4.1.tgz",
          "integrity": "sha512-qiLX/xhEEFKUAJ6FiBMbes3w9ATzyk5W7Hvzpa/SLYdxNtng+gcurvrI7TbACjIXlsJyr05/S1oUhZrc63evQA==",
          "requires": {
            "buffer-equal-constant-time": "1.0.1",
            "ecdsa-sig-formatter": "1.0.11",
            "safe-buffer": "^5.0.1"
          }
        },
        "jws": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/jws/-/jws-3.2.2.tgz",
          "integrity": "sha512-YHlZCB6lMTllWDtSPHz/ZXTsi8S00usEV6v1tjq8tOUZzw7DpSDWVXjXDre6ed1w/pd495ODpHZYSdkRTsa0HA==",
          "requires": {
            "jwa": "^1.4.1",
            "safe-buffer": "^5.0.1"
          }
        },
        "lru-cache": {
          "version": "4.1.5",
          "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-4.1.5.tgz",
          "integrity": "sha512-sWZlbEP2OsHNkXrMl5GYk/jKk70MBng6UU4YI/qGDYbgf6YbP4EvmqISbXCoJiRKs+1bSpFHVgQxvJ17F2li5g==",
          "requires": {
            "pseudomap": "^1.0.2",
            "yallist": "^2.1.2"
          }
        },
        "mime": {
          "version": "2.4.4",
          "resolved": "https://registry.npmjs.org/mime/-/mime-2.4.4.tgz",
          "integrity": "sha512-LRxmNwziLPT828z+4YkNzloCFC2YM4wrB99k+AV5ZbEyfGNWfG8SO1FUXLmLDBSo89NrJZ4DIWeLjy1CHGhMGA=="
        },
        "ms": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
          "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
        },
        "node-forge": {
          "version": "0.8.5",
          "resolved": "https://registry.npmjs.org/node-forge/-/node-forge-0.8.5.tgz",
          "integrity": "sha512-vFMQIWt+J/7FLNyKouZ9TazT74PRV3wgv9UT4cRjC8BffxFbKXkgIWR42URCPSnHm/QDz6BOlb2Q0U4+VQT67Q=="
        },
        "readable-stream": {
          "version": "2.3.7",
          "resolved": "https://registry.npmjs.org/readable-stream/-/readable-stream-2.3.7.tgz",
          "integrity": "sha512-Ebho8K4jIbHAxnuxi7o42OrZgF/ZTNcsZj6nRKyUmkhLFq8CHItp/fy6hQZuZmP/n3yZ9VBUbp4zz/mX8hmYPw==",
          "requires": {
            "core-util-is": "~1.0.0",
            "inherits": "~2.0.3",
            "isarray": "~1.0.0",
            "process-nextick-args": "~2.0.0",
            "safe-buffer": "~5.1.1",
            "string_decoder": "~1.1.1",
            "util-deprecate": "~1.0.1"
          }
        },
        "through2": {
          "version": "2.0.5",
          "resolved": "https://registry.npmjs.org/through2/-/through2-2.0.5.tgz",
          "integrity": "sha512-/mrRod8xqpA+IHSLyGCQ2s8SPHiCDEeQJSep1jqLYeEUClOFG2Qsh+4FU6G9VeqpZnGW/Su8LQGc4YKni5rYSQ==",
          "requires": {
            "readable-stream": "~2.3.6",
            "xtend": "~4.0.1"
          }
        },
        "yallist": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/yallist/-/yallist-2.1.2.tgz",
          "integrity": "sha1-HBH5IY8HYImkfdUS+TxmmaaoHVI="
        }
      }
    },
    "google-p12-pem": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/google-p12-pem/-/google-p12-pem-2.0.4.tgz",
      "integrity": "sha512-S4blHBQWZRnEW44OcR7TL9WR+QCqByRvhNDZ/uuQfpxywfupikf/miba8js1jZi6ZOGv5slgSuoshCWh6EMDzg==",
      "requires": {
        "node-forge": "^0.9.0"
      }
    },
    "google-proto-files": {
      "version": "0.15.1",
      "resolved": "https://registry.npmjs.org/google-proto-files/-/google-proto-files-0.15.1.tgz",
      "integrity": "sha512-ebtmWgi/ooR5Nl63qRVZZ6VLM6JOb5zTNxTT/ZAU8yfMOdcauoOZNNMOVg0pCmTjqWXeuuVbgPP0CwO5UHHzBQ==",
      "requires": {
        "globby": "^7.1.1",
        "power-assert": "^1.4.4",
        "protobufjs": "^6.8.0"
      },
      "dependencies": {
        "globby": {
          "version": "7.1.1",
          "resolved": "https://registry.npmjs.org/globby/-/globby-7.1.1.tgz",
          "integrity": "sha1-+yzP+UAfhgCUXfral0QMypcrhoA=",
          "requires": {
            "array-union": "^1.0.1",
            "dir-glob": "^2.0.0",
            "glob": "^7.1.2",
            "ignore": "^3.3.5",
            "pify": "^3.0.0",
            "slash": "^1.0.0"
          }
        },
        "pify": {
          "version": "3.0.0",
          "resolved": "https://registry.npmjs.org/pify/-/pify-3.0.0.tgz",
          "integrity": "sha1-5aSs0sEB/fPZpNB/DbxNtJ3SgXY="
        }
      }
    },
    "graceful-fs": {
      "version": "4.2.3",
      "resolved": "https://registry.npmjs.org/graceful-fs/-/graceful-fs-4.2.3.tgz",
      "integrity": "sha512-a30VEBm4PEdx1dRB7MFK7BejejvCvBronbLjht+sHuGYj8PHs7M/5Z+rt5lw551vZ7yfTCj4Vuyy3mSJytDWRQ=="
    },
    "grpc": {
      "version": "1.24.2",
      "resolved": "https://registry.npmjs.org/grpc/-/grpc-1.24.2.tgz",
      "integrity": "sha512-EG3WH6AWMVvAiV15d+lr+K77HJ/KV/3FvMpjKjulXHbTwgDZkhkcWbwhxFAoTdxTkQvy0WFcO3Nog50QBbHZWw==",
      "requires": {
        "@types/bytebuffer": "^5.0.40",
        "lodash.camelcase": "^4.3.0",
        "lodash.clone": "^4.5.0",
        "nan": "^2.13.2",
        "node-pre-gyp": "^0.14.0",
        "protobufjs": "^5.0.3"
      },
      "dependencies": {
        "abbrev": {
          "version": "1.1.1",
          "bundled": true
        },
        "ansi-regex": {
          "version": "2.1.1",
          "bundled": true
        },
        "aproba": {
          "version": "1.2.0",
          "bundled": true
        },
        "are-we-there-yet": {
          "version": "1.1.5",
          "bundled": true,
          "requires": {
            "delegates": "^1.0.0",
            "readable-stream": "^2.0.6"
          }
        },
        "balanced-match": {
          "version": "1.0.0",
          "bundled": true
        },
        "brace-expansion": {
          "version": "1.1.11",
          "bundled": true,
          "requires": {
            "balanced-match": "^1.0.0",
            "concat-map": "0.0.1"
          }
        },
        "chownr": {
          "version": "1.1.3",
          "bundled": true
        },
        "code-point-at": {
          "version": "1.1.0",
          "bundled": true
        },
        "concat-map": {
          "version": "0.0.1",
          "bundled": true
        },
        "console-control-strings": {
          "version": "1.1.0",
          "bundled": true
        },
        "core-util-is": {
          "version": "1.0.2",
          "bundled": true
        },
        "debug": {
          "version": "3.2.6",
          "bundled": true,
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "deep-extend": {
          "version": "0.6.0",
          "bundled": true
        },
        "delegates": {
          "version": "1.0.0",
          "bundled": true
        },
        "detect-libc": {
          "version": "1.0.3",
          "bundled": true
        },
        "fs-minipass": {
          "version": "1.2.7",
          "bundled": true,
          "requires": {
            "minipass": "^2.6.0"
          }
        },
        "fs.realpath": {
          "version": "1.0.0",
          "bundled": true
        },
        "gauge": {
          "version": "2.7.4",
          "bundled": true,
          "requires": {
            "aproba": "^1.0.3",
            "console-control-strings": "^1.0.0",
            "has-unicode": "^2.0.0",
            "object-assign": "^4.1.0",
            "signal-exit": "^3.0.0",
            "string-width": "^1.0.1",
            "strip-ansi": "^3.0.1",
            "wide-align": "^1.1.0"
          }
        },
        "glob": {
          "version": "7.1.4",
          "bundled": true,
          "requires": {
            "fs.realpath": "^1.0.0",
            "inflight": "^1.0.4",
            "inherits": "2",
            "minimatch": "^3.0.4",
            "once": "^1.3.0",
            "path-is-absolute": "^1.0.0"
          }
        },
        "has-unicode": {
          "version": "2.0.1",
          "bundled": true
        },
        "iconv-lite": {
          "version": "0.4.24",
          "bundled": true,
          "requires": {
            "safer-buffer": ">= 2.1.2 < 3"
          }
        },
        "ignore-walk": {
          "version": "3.0.3",
          "bundled": true,
          "requires": {
            "minimatch": "^3.0.4"
          }
        },
        "inflight": {
          "version": "1.0.6",
          "bundled": true,
          "requires": {
            "once": "^1.3.0",
            "wrappy": "1"
          }
        },
        "inherits": {
          "version": "2.0.4",
          "bundled": true
        },
        "ini": {
          "version": "1.3.5",
          "bundled": true
        },
        "is-fullwidth-code-point": {
          "version": "1.0.0",
          "bundled": true,
          "requires": {
            "number-is-nan": "^1.0.0"
          }
        },
        "isarray": {
          "version": "1.0.0",
          "bundled": true
        },
        "minimatch": {
          "version": "3.0.4",
          "bundled": true,
          "requires": {
            "brace-expansion": "^1.1.7"
          }
        },
        "minimist": {
          "version": "1.2.0",
          "bundled": true
        },
        "minipass": {
          "version": "2.9.0",
          "bundled": true,
          "requires": {
            "safe-buffer": "^5.1.2",
            "yallist": "^3.0.0"
          }
        },
        "minizlib": {
          "version": "1.3.3",
          "bundled": true,
          "requires": {
            "minipass": "^2.9.0"
          }
        },
        "mkdirp": {
          "version": "0.5.1",
          "bundled": true,
          "requires": {
            "minimist": "0.0.8"
          },
          "dependencies": {
            "minimist": {
              "version": "0.0.8",
              "bundled": true
            }
          }
        },
        "ms": {
          "version": "2.1.2",
          "bundled": true
        },
        "needle": {
          "version": "2.4.0",
          "bundled": true,
          "requires": {
            "debug": "^3.2.6",
            "iconv-lite": "^0.4.4",
            "sax": "^1.2.4"
          }
        },
        "node-pre-gyp": {
          "version": "0.14.0",
          "bundled": true,
          "requires": {
            "detect-libc": "^1.0.2",
            "mkdirp": "^0.5.1",
            "needle": "^2.2.1",
            "nopt": "^4.0.1",
            "npm-packlist": "^1.1.6",
            "npmlog": "^4.0.2",
            "rc": "^1.2.7",
            "rimraf": "^2.6.1",
            "semver": "^5.3.0",
            "tar": "^4.4.2"
          }
        },
        "nopt": {
          "version": "4.0.1",
          "bundled": true,
          "requires": {
            "abbrev": "1",
            "osenv": "^0.1.4"
          }
        },
        "npm-bundled": {
          "version": "1.0.6",
          "bundled": true
        },
        "npm-packlist": {
          "version": "1.4.6",
          "bundled": true,
          "requires": {
            "ignore-walk": "^3.0.1",
            "npm-bundled": "^1.0.1"
          }
        },
        "npmlog": {
          "version": "4.1.2",
          "bundled": true,
          "requires": {
            "are-we-there-yet": "~1.1.2",
            "console-control-strings": "~1.1.0",
            "gauge": "~2.7.3",
            "set-blocking": "~2.0.0"
          }
        },
        "number-is-nan": {
          "version": "1.0.1",
          "bundled": true
        },
        "object-assign": {
          "version": "4.1.1",
          "bundled": true
        },
        "once": {
          "version": "1.4.0",
          "bundled": true,
          "requires": {
            "wrappy": "1"
          }
        },
        "os-homedir": {
          "version": "1.0.2",
          "bundled": true
        },
        "os-tmpdir": {
          "version": "1.0.2",
          "bundled": true
        },
        "osenv": {
          "version": "0.1.5",
          "bundled": true,
          "requires": {
            "os-homedir": "^1.0.0",
            "os-tmpdir": "^1.0.0"
          }
        },
        "path-is-absolute": {
          "version": "1.0.1",
          "bundled": true
        },
        "process-nextick-args": {
          "version": "2.0.1",
          "bundled": true
        },
        "protobufjs": {
          "version": "5.0.3",
          "resolved": "https://registry.npmjs.org/protobufjs/-/protobufjs-5.0.3.tgz",
          "integrity": "sha512-55Kcx1MhPZX0zTbVosMQEO5R6/rikNXd9b6RQK4KSPcrSIIwoXTtebIczUrXlwaSrbz4x8XUVThGPob1n8I4QA==",
          "requires": {
            "ascli": "~1",
            "bytebuffer": "~5",
            "glob": "^7.0.5",
            "yargs": "^3.10.0"
          }
        },
        "rc": {
          "version": "1.2.8",
          "bundled": true,
          "requires": {
            "deep-extend": "^0.6.0",
            "ini": "~1.3.0",
            "minimist": "^1.2.0",
            "strip-json-comments": "~2.0.1"
          }
        },
        "readable-stream": {
          "version": "2.3.6",
          "bundled": true,
          "requires": {
            "core-util-is": "~1.0.0",
            "inherits": "~2.0.3",
            "isarray": "~1.0.0",
            "process-nextick-args": "~2.0.0",
            "safe-buffer": "~5.1.1",
            "string_decoder": "~1.1.1",
            "util-deprecate": "~1.0.1"
          }
        },
        "rimraf": {
          "version": "2.7.1",
          "bundled": true,
          "requires": {
            "glob": "^7.1.3"
          }
        },
        "safe-buffer": {
          "version": "5.1.2",
          "bundled": true
        },
        "safer-buffer": {
          "version": "2.1.2",
          "bundled": true
        },
        "sax": {
          "version": "1.2.4",
          "bundled": true
        },
        "semver": {
          "version": "5.7.1",
          "bundled": true
        },
        "set-blocking": {
          "version": "2.0.0",
          "bundled": true
        },
        "signal-exit": {
          "version": "3.0.2",
          "bundled": true
        },
        "string-width": {
          "version": "1.0.2",
          "bundled": true,
          "requires": {
            "code-point-at": "^1.0.0",
            "is-fullwidth-code-point": "^1.0.0",
            "strip-ansi": "^3.0.0"
          }
        },
        "string_decoder": {
          "version": "1.1.1",
          "bundled": true,
          "requires": {
            "safe-buffer": "~5.1.0"
          }
        },
        "strip-ansi": {
          "version": "3.0.1",
          "bundled": true,
          "requires": {
            "ansi-regex": "^2.0.0"
          }
        },
        "strip-json-comments": {
          "version": "2.0.1",
          "bundled": true
        },
        "tar": {
          "version": "4.4.13",
          "bundled": true,
          "requires": {
            "chownr": "^1.1.1",
            "fs-minipass": "^1.2.5",
            "minipass": "^2.8.6",
            "minizlib": "^1.2.1",
            "mkdirp": "^0.5.0",
            "safe-buffer": "^5.1.2",
            "yallist": "^3.0.3"
          }
        },
        "util-deprecate": {
          "version": "1.0.2",
          "bundled": true
        },
        "wide-align": {
          "version": "1.1.3",
          "bundled": true,
          "requires": {
            "string-width": "^1.0.2 || 2"
          }
        },
        "wrappy": {
          "version": "1.0.2",
          "bundled": true
        },
        "yallist": {
          "version": "3.1.1",
          "bundled": true
        }
      }
    },
    "gtoken": {
      "version": "4.1.4",
      "resolved": "https://registry.npmjs.org/gtoken/-/gtoken-4.1.4.tgz",
      "integrity": "sha512-VxirzD0SWoFUo5p8RDP8Jt2AGyOmyYcT/pOUgDKJCK+iSw0TMqwrVfY37RXTNmoKwrzmDHSk0GMT9FsgVmnVSA==",
      "requires": {
        "gaxios": "^2.1.0",
        "google-p12-pem": "^2.0.0",
        "jws": "^4.0.0",
        "mime": "^2.2.0"
      },
      "dependencies": {
        "gaxios": {
          "version": "2.3.4",
          "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-2.3.4.tgz",
          "integrity": "sha512-US8UMj8C5pRnao3Zykc4AAVr+cffoNKRTg9Rsf2GiuZCW69vgJj38VK2PzlPuQU73FZ/nTk9/Av6/JGcE1N9vA==",
          "requires": {
            "abort-controller": "^3.0.0",
            "extend": "^3.0.2",
            "https-proxy-agent": "^5.0.0",
            "is-stream": "^2.0.0",
            "node-fetch": "^2.3.0"
          }
        },
        "mime": {
          "version": "2.4.4",
          "resolved": "https://registry.npmjs.org/mime/-/mime-2.4.4.tgz",
          "integrity": "sha512-LRxmNwziLPT828z+4YkNzloCFC2YM4wrB99k+AV5ZbEyfGNWfG8SO1FUXLmLDBSo89NrJZ4DIWeLjy1CHGhMGA=="
        }
      }
    },
    "har-schema": {
      "version": "1.0.5",
      "resolved": "https://registry.npmjs.org/har-schema/-/har-schema-1.0.5.tgz",
      "integrity": "sha1-0mMTX0MwfALGAq/I/pWXDAFRNp4="
    },
    "har-validator": {
      "version": "4.2.1",
      "resolved": "https://registry.npmjs.org/har-validator/-/har-validator-4.2.1.tgz",
      "integrity": "sha1-M0gdDxu/9gDdID11gSpqX7oALio=",
      "requires": {
        "ajv": "^4.9.1",
        "har-schema": "^1.0.5"
      }
    },
    "has-value": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/has-value/-/has-value-1.0.0.tgz",
      "integrity": "sha1-GLKB2lhbHFxR3vJMkw7SmgvmsXc=",
      "requires": {
        "get-value": "^2.0.6",
        "has-values": "^1.0.0",
        "isobject": "^3.0.0"
      }
    },
    "has-values": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/has-values/-/has-values-1.0.0.tgz",
      "integrity": "sha1-lbC2P+whRmGab+V/51Yo1aOe/k8=",
      "requires": {
        "is-number": "^3.0.0",
        "kind-of": "^4.0.0"
      },
      "dependencies": {
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "4.0.0",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-4.0.0.tgz",
          "integrity": "sha1-IIE989cSkosgc3hpGkUGb65y3Vc=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "hash-stream-validation": {
      "version": "0.2.2",
      "resolved": "https://registry.npmjs.org/hash-stream-validation/-/hash-stream-validation-0.2.2.tgz",
      "integrity": "sha512-cMlva5CxWZOrlS/cY0C+9qAzesn5srhFA8IT1VPiHc9bWWBLkJfEUIZr7MWoi89oOOGmpg8ymchaOjiArsGu5A==",
      "requires": {
        "through2": "^2.0.0"
      },
      "dependencies": {
        "readable-stream": {
          "version": "2.3.7",
          "resolved": "https://registry.npmjs.org/readable-stream/-/readable-stream-2.3.7.tgz",
          "integrity": "sha512-Ebho8K4jIbHAxnuxi7o42OrZgF/ZTNcsZj6nRKyUmkhLFq8CHItp/fy6hQZuZmP/n3yZ9VBUbp4zz/mX8hmYPw==",
          "requires": {
            "core-util-is": "~1.0.0",
            "inherits": "~2.0.3",
            "isarray": "~1.0.0",
            "process-nextick-args": "~2.0.0",
            "safe-buffer": "~5.1.1",
            "string_decoder": "~1.1.1",
            "util-deprecate": "~1.0.1"
          }
        },
        "through2": {
          "version": "2.0.5",
          "resolved": "https://registry.npmjs.org/through2/-/through2-2.0.5.tgz",
          "integrity": "sha512-/mrRod8xqpA+IHSLyGCQ2s8SPHiCDEeQJSep1jqLYeEUClOFG2Qsh+4FU6G9VeqpZnGW/Su8LQGc4YKni5rYSQ==",
          "requires": {
            "readable-stream": "~2.3.6",
            "xtend": "~4.0.1"
          }
        }
      }
    },
    "hawk": {
      "version": "3.1.3",
      "resolved": "https://registry.npmjs.org/hawk/-/hawk-3.1.3.tgz",
      "integrity": "sha1-B4REvXwWQLD+VA0sm3PVlnjo4cQ=",
      "requires": {
        "boom": "2.x.x",
        "cryptiles": "2.x.x",
        "hoek": "2.x.x",
        "sntp": "1.x.x"
      }
    },
    "hoek": {
      "version": "2.16.3",
      "resolved": "https://registry.npmjs.org/hoek/-/hoek-2.16.3.tgz",
      "integrity": "sha1-ILt0A9POo5jpHcRxCo/xuCdKJe0="
    },
    "http-errors": {
      "version": "1.7.2",
      "resolved": "https://registry.npmjs.org/http-errors/-/http-errors-1.7.2.tgz",
      "integrity": "sha512-uUQBt3H/cSIVfch6i1EuPNy/YsRSOUBXTVfZ+yR7Zjez3qjBz6i9+i4zjNaoqcoFVI4lQJ5plg63TvGfRSDCRg==",
      "requires": {
        "depd": "~1.1.2",
        "inherits": "2.0.3",
        "setprototypeof": "1.1.1",
        "statuses": ">= 1.5.0 < 2",
        "toidentifier": "1.0.0"
      }
    },
    "http-proxy-agent": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/http-proxy-agent/-/http-proxy-agent-4.0.1.tgz",
      "integrity": "sha512-k0zdNgqWTGA6aeIRVpvfVob4fL52dTfaehylg0Y4UvSySvOq/Y+BOyPrgpUrA7HylqvU8vIZGsRuXmspskV0Tg==",
      "requires": {
        "@tootallnate/once": "1",
        "agent-base": "6",
        "debug": "4"
      },
      "dependencies": {
        "debug": {
          "version": "4.1.1",
          "resolved": "https://registry.npmjs.org/debug/-/debug-4.1.1.tgz",
          "integrity": "sha512-pYAIzeRo8J6KPEaJ0VWOh5Pzkbw/RetuzehGM7QRRX5he4fPHx2rdKMB256ehJCkX+XRQm16eZLqLNS8RSZXZw==",
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "ms": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
          "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
        }
      }
    },
    "http-signature": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/http-signature/-/http-signature-1.1.1.tgz",
      "integrity": "sha1-33LiZwZs0Kxn+3at+OE0qPvPkb8=",
      "requires": {
        "assert-plus": "^0.2.0",
        "jsprim": "^1.2.2",
        "sshpk": "^1.7.0"
      }
    },
    "https-proxy-agent": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/https-proxy-agent/-/https-proxy-agent-5.0.0.tgz",
      "integrity": "sha512-EkYm5BcKUGiduxzSt3Eppko+PiNWNEpa4ySk9vTC6wDsQJW9rHSa+UhGNJoRYp7bz6Ht1eaRIa6QaJqO5rCFbA==",
      "requires": {
        "agent-base": "6",
        "debug": "4"
      },
      "dependencies": {
        "debug": {
          "version": "4.1.1",
          "resolved": "https://registry.npmjs.org/debug/-/debug-4.1.1.tgz",
          "integrity": "sha512-pYAIzeRo8J6KPEaJ0VWOh5Pzkbw/RetuzehGM7QRRX5he4fPHx2rdKMB256ehJCkX+XRQm16eZLqLNS8RSZXZw==",
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "ms": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
          "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
        }
      }
    },
    "iconv-lite": {
      "version": "0.4.24",
      "resolved": "https://registry.npmjs.org/iconv-lite/-/iconv-lite-0.4.24.tgz",
      "integrity": "sha512-v3MXnZAcvnywkTUEZomIActle7RXXeedOR31wwl7VlyoXO4Qi9arvSenNQWne1TcRwhCL1HwLI21bEqdpj8/rA==",
      "requires": {
        "safer-buffer": ">= 2.1.2 < 3"
      }
    },
    "ignore": {
      "version": "3.3.10",
      "resolved": "https://registry.npmjs.org/ignore/-/ignore-3.3.10.tgz",
      "integrity": "sha512-Pgs951kaMm5GXP7MOvxERINe3gsaVjUWFm+UZPSq9xYriQAksyhg0csnS0KXSNRD5NmNdapXEpjxG49+AKh/ug=="
    },
    "imurmurhash": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/imurmurhash/-/imurmurhash-0.1.4.tgz",
      "integrity": "sha1-khi5srkoojixPcT7a21XbyMUU+o="
    },
    "indexof": {
      "version": "0.0.1",
      "resolved": "https://registry.npmjs.org/indexof/-/indexof-0.0.1.tgz",
      "integrity": "sha1-gtwzbSMrkGIXnQWrMpOmYFn9Q10="
    },
    "inflight": {
      "version": "1.0.6",
      "resolved": "https://registry.npmjs.org/inflight/-/inflight-1.0.6.tgz",
      "integrity": "sha1-Sb1jMdfQLQwJvJEKEHW6gWW1bfk=",
      "requires": {
        "once": "^1.3.0",
        "wrappy": "1"
      }
    },
    "inherits": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/inherits/-/inherits-2.0.3.tgz",
      "integrity": "sha1-Yzwsg+PaQqUC9SRmAiSA9CCCYd4="
    },
    "invert-kv": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/invert-kv/-/invert-kv-1.0.0.tgz",
      "integrity": "sha1-EEqOSqym09jNFXqO+L+rLXo//bY="
    },
    "ipaddr.js": {
      "version": "1.9.1",
      "resolved": "https://registry.npmjs.org/ipaddr.js/-/ipaddr.js-1.9.1.tgz",
      "integrity": "sha512-0KI/607xoxSToH7GjN1FfSbLoU0+btTicjsQSWQlh/hZykN8KpmMf7uYwPW3R+akZ6R/w18ZlXSHBYXiYUPO3g=="
    },
    "is": {
      "version": "3.3.0",
      "resolved": "https://registry.npmjs.org/is/-/is-3.3.0.tgz",
      "integrity": "sha512-nW24QBoPcFGGHJGUwnfpI7Yc5CdqWNdsyHQszVE/z2pKHXzh7FZ5GWhJqSyaQ9wMkQnsTx+kAI8bHlCX4tKdbg=="
    },
    "is-accessor-descriptor": {
      "version": "0.1.6",
      "resolved": "https://registry.npmjs.org/is-accessor-descriptor/-/is-accessor-descriptor-0.1.6.tgz",
      "integrity": "sha1-qeEss66Nh2cn7u84Q/igiXtcmNY=",
      "requires": {
        "kind-of": "^3.0.2"
      },
      "dependencies": {
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-3.2.2.tgz",
          "integrity": "sha1-MeohpzS6ubuw8yRm2JOupR5KPGQ=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "is-buffer": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-2.0.4.tgz",
      "integrity": "sha512-Kq1rokWXOPXWuaMAqZiJW4XxsmD9zGx9q4aePabbn3qCRGedtH7Cm+zV8WETitMfu1wdh+Rvd6w5egwSngUX2A=="
    },
    "is-data-descriptor": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/is-data-descriptor/-/is-data-descriptor-0.1.4.tgz",
      "integrity": "sha1-C17mSDiOLIYCgueT8YVv7D8wG1Y=",
      "requires": {
        "kind-of": "^3.0.2"
      },
      "dependencies": {
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-3.2.2.tgz",
          "integrity": "sha1-MeohpzS6ubuw8yRm2JOupR5KPGQ=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "is-descriptor": {
      "version": "0.1.6",
      "resolved": "https://registry.npmjs.org/is-descriptor/-/is-descriptor-0.1.6.tgz",
      "integrity": "sha512-avDYr0SB3DwO9zsMov0gKCESFYqCnE4hq/4z3TdUlukEy5t9C0YRq7HLrsN52NAcqXKaepeCD0n+B0arnVG3Hg==",
      "requires": {
        "is-accessor-descriptor": "^0.1.6",
        "is-data-descriptor": "^0.1.4",
        "kind-of": "^5.0.0"
      },
      "dependencies": {
        "kind-of": {
          "version": "5.1.0",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-5.1.0.tgz",
          "integrity": "sha512-NGEErnH6F2vUuXDh+OlbcKW7/wOcfdRHaZ7VWtqCztfHri/++YKmP51OdWeGPuqCOba6kk2OTe5d02VmTB80Pw=="
        }
      }
    },
    "is-extendable": {
      "version": "0.1.1",
      "resolved": "https://registry.npmjs.org/is-extendable/-/is-extendable-0.1.1.tgz",
      "integrity": "sha1-YrEQ4omkcUGOPsNqYX1HLjAd/Ik="
    },
    "is-extglob": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/is-extglob/-/is-extglob-2.1.1.tgz",
      "integrity": "sha1-qIwCU1eR8C7TfHahueqXc8gz+MI="
    },
    "is-fullwidth-code-point": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/is-fullwidth-code-point/-/is-fullwidth-code-point-1.0.0.tgz",
      "integrity": "sha1-754xOG8DGn8NZDr4L95QxFfvAMs=",
      "requires": {
        "number-is-nan": "^1.0.0"
      }
    },
    "is-glob": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/is-glob/-/is-glob-4.0.1.tgz",
      "integrity": "sha512-5G0tKtBTFImOqDnLB2hG6Bp2qcKEFduo4tZu9MT/H6NQv/ghhy30o55ufafxJ/LdH79LLs2Kfrn85TLKyA7BUg==",
      "requires": {
        "is-extglob": "^2.1.1"
      }
    },
    "is-number": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/is-number/-/is-number-3.0.0.tgz",
      "integrity": "sha1-JP1iAaR4LPUFYcgQJ2r8fRLXEZU=",
      "requires": {
        "kind-of": "^3.0.2"
      },
      "dependencies": {
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-3.2.2.tgz",
          "integrity": "sha1-MeohpzS6ubuw8yRm2JOupR5KPGQ=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "is-obj": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/is-obj/-/is-obj-2.0.0.tgz",
      "integrity": "sha512-drqDG3cbczxxEJRoOXcOjtdp1J/lyp1mNn0xaznRs8+muBhgQcrnbspox5X5fOw0HnMnbfDzvnEMEtqDEJEo8w=="
    },
    "is-plain-object": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/is-plain-object/-/is-plain-object-2.0.4.tgz",
      "integrity": "sha512-h5PpgXkWitc38BBMYawTYMWJHFZJVnBquFE57xFpjB8pJFiF6gZ+bU+WyI/yqXiFR5mdLsgYNaPe8uao6Uv9Og==",
      "requires": {
        "isobject": "^3.0.1"
      }
    },
    "is-stream": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/is-stream/-/is-stream-2.0.0.tgz",
      "integrity": "sha512-XCoy+WlUr7d1+Z8GgSuXmpuUFC9fOhRXglJMx+dwLKTkL44Cjd4W1Z5P+BQZpr+cR93aGP4S/s7Ftw6Nd/kiEw=="
    },
    "is-stream-ended": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/is-stream-ended/-/is-stream-ended-0.1.4.tgz",
      "integrity": "sha512-xj0XPvmr7bQFTvirqnFr50o0hQIh6ZItDqloxt5aJrR4NQsYeSsyFQERYGCAzfindAcnKjINnwEEgLx4IqVzQw=="
    },
    "is-typedarray": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/is-typedarray/-/is-typedarray-1.0.0.tgz",
      "integrity": "sha1-5HnICFjfDBsR3dppQPlgEfzaSpo="
    },
    "is-windows": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/is-windows/-/is-windows-1.0.2.tgz",
      "integrity": "sha512-eXK1UInq2bPmjyX6e3VHIzMLobc4J94i4AWn+Hpq3OU5KkrRC96OAcR3PRJ/pGu6m8TRnBHP9dkXQVsT/COVIA=="
    },
    "isarray": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/isarray/-/isarray-1.0.0.tgz",
      "integrity": "sha1-u5NdSFgsuhaMBoNJV6VKPgcSTxE="
    },
    "isobject": {
      "version": "3.0.1",
      "resolved": "https://registry.npmjs.org/isobject/-/isobject-3.0.1.tgz",
      "integrity": "sha1-TkMekrEalzFjaqH5yNHMvP2reN8="
    },
    "isstream": {
      "version": "0.1.2",
      "resolved": "https://registry.npmjs.org/isstream/-/isstream-0.1.2.tgz",
      "integrity": "sha1-R+Y/evVa+m+S4VAOaQ64uFKcCZo="
    },
    "jsbn": {
      "version": "0.1.1",
      "resolved": "https://registry.npmjs.org/jsbn/-/jsbn-0.1.1.tgz",
      "integrity": "sha1-peZUwuWi3rXyAdls77yoDA7y9RM="
    },
    "json-bigint": {
      "version": "0.3.0",
      "resolved": "https://registry.npmjs.org/json-bigint/-/json-bigint-0.3.0.tgz",
      "integrity": "sha1-DM2RLEuCcNBfBW+9E4FLU9OCWx4=",
      "requires": {
        "bignumber.js": "^7.0.0"
      }
    },
    "json-schema": {
      "version": "0.2.3",
      "resolved": "https://registry.npmjs.org/json-schema/-/json-schema-0.2.3.tgz",
      "integrity": "sha1-tIDIkuWaLwWVTOcnvT8qTogvnhM="
    },
    "json-stable-stringify": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/json-stable-stringify/-/json-stable-stringify-1.0.1.tgz",
      "integrity": "sha1-mnWdOcXy/1A/1TAGRu1EX4jE+a8=",
      "requires": {
        "jsonify": "~0.0.0"
      }
    },
    "json-stringify-safe": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/json-stringify-safe/-/json-stringify-safe-5.0.1.tgz",
      "integrity": "sha1-Epai1Y/UXxmg9s4B1lcB4sc1tus="
    },
    "jsonify": {
      "version": "0.0.0",
      "resolved": "https://registry.npmjs.org/jsonify/-/jsonify-0.0.0.tgz",
      "integrity": "sha1-LHS27kHZPKUbe1qu6PUDYx0lKnM="
    },
    "jsprim": {
      "version": "1.4.1",
      "resolved": "https://registry.npmjs.org/jsprim/-/jsprim-1.4.1.tgz",
      "integrity": "sha1-MT5mvB5cwG5Di8G3SZwuXFastqI=",
      "requires": {
        "assert-plus": "1.0.0",
        "extsprintf": "1.3.0",
        "json-schema": "0.2.3",
        "verror": "1.10.0"
      },
      "dependencies": {
        "assert-plus": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/assert-plus/-/assert-plus-1.0.0.tgz",
          "integrity": "sha1-8S4PPF13sLHN2RRpQuTpbB5N1SU="
        }
      }
    },
    "jwa": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/jwa/-/jwa-2.0.0.tgz",
      "integrity": "sha512-jrZ2Qx916EA+fq9cEAeCROWPTfCwi1IVHqT2tapuqLEVVDKFDENFw1oL+MwrTvH6msKxsd1YTDVw6uKEcsrLEA==",
      "requires": {
        "buffer-equal-constant-time": "1.0.1",
        "ecdsa-sig-formatter": "1.0.11",
        "safe-buffer": "^5.0.1"
      }
    },
    "jws": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/jws/-/jws-4.0.0.tgz",
      "integrity": "sha512-KDncfTmOZoOMTFG4mBlG0qUIOlc03fmzH+ru6RgYVZhPkyiy/92Owlt/8UEN+a4TXR1FQetfIpJE8ApdvdVxTg==",
      "requires": {
        "jwa": "^2.0.0",
        "safe-buffer": "^5.0.1"
      }
    },
    "kind-of": {
      "version": "6.0.3",
      "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-6.0.3.tgz",
      "integrity": "sha512-dcS1ul+9tmeD95T+x28/ehLgd9mENa3LsvDTtzm3vyBEO7RPptvAD+t44WVXaUjTBRcrpFeFlC8WCruUR456hw=="
    },
    "lcid": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/lcid/-/lcid-1.0.0.tgz",
      "integrity": "sha1-MIrMr6C8SDo4Z7S28rlQYlHRuDU=",
      "requires": {
        "invert-kv": "^1.0.0"
      }
    },
    "lodash": {
      "version": "4.17.15",
      "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.15.tgz",
      "integrity": "sha512-8xOcRHvCjnocdS5cpwXQXVzmmh5e5+saE2QGoeQmbKmRS6J3VQppPOIt0MnmE+4xlZoumy0GPG0D0MVIQbNA1A=="
    },
    "lodash.camelcase": {
      "version": "4.3.0",
      "resolved": "https://registry.npmjs.org/lodash.camelcase/-/lodash.camelcase-4.3.0.tgz",
      "integrity": "sha1-soqmKIorn8ZRA1x3EfZathkDMaY="
    },
    "lodash.chunk": {
      "version": "4.2.0",
      "resolved": "https://registry.npmjs.org/lodash.chunk/-/lodash.chunk-4.2.0.tgz",
      "integrity": "sha1-ZuXOH3btJ7QwPYxlEujRIW6BBrw="
    },
    "lodash.clone": {
      "version": "4.5.0",
      "resolved": "https://registry.npmjs.org/lodash.clone/-/lodash.clone-4.5.0.tgz",
      "integrity": "sha1-GVhwRQ9aExkkeN9Lw9I9LeoZB7Y="
    },
    "lodash.isstring": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/lodash.isstring/-/lodash.isstring-4.0.1.tgz",
      "integrity": "sha1-1SfftUVuynzJu5XV2ur4i6VKVFE="
    },
    "lodash.merge": {
      "version": "4.6.2",
      "resolved": "https://registry.npmjs.org/lodash.merge/-/lodash.merge-4.6.2.tgz",
      "integrity": "sha512-0KpjqXRVvrYyCsX1swR/XTK0va6VQkQM6MNo7PqW77ByjAhoARA8EfrP1N4+KlKj8YS0ZUCtRT/YUuhyYDujIQ=="
    },
    "lodash.snakecase": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/lodash.snakecase/-/lodash.snakecase-4.1.1.tgz",
      "integrity": "sha1-OdcUo1NXFHg3rv1ktdy7Fr7Nj40="
    },
    "log-driver": {
      "version": "1.2.7",
      "resolved": "https://registry.npmjs.org/log-driver/-/log-driver-1.2.7.tgz",
      "integrity": "sha512-U7KCmLdqsGHBLeWqYlFA0V0Sl6P08EE1ZrmA9cxjUE0WVqT9qnyVDPz1kzpFEP0jdJuFnasWIfSd7fsaNXkpbg=="
    },
    "long": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/long/-/long-4.0.0.tgz",
      "integrity": "sha512-XsP+KhQif4bjX1kbuSiySJFNAehNxgLb6hPRGJ9QsUr8ajHkuXGdrHmFUTUUXhDwVX2R5bY4JNZEwbUiMhV+MA=="
    },
    "lru-cache": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-5.1.1.tgz",
      "integrity": "sha512-KpNARQA3Iwv+jTA0utUVVbrh+Jlrr1Fv0e56GGzAFOXN7dk/FviaDW8LHmK52DlcH4WP2n6gI8vN1aesBFgo9w==",
      "requires": {
        "yallist": "^3.0.2"
      }
    },
    "make-dir": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/make-dir/-/make-dir-3.0.2.tgz",
      "integrity": "sha512-rYKABKutXa6vXTXhoV18cBE7PaewPXHe/Bdq4v+ZLMhxbWApkFFplT0LcbMW+6BbjnQXzZ/sAvSE/JdguApG5w==",
      "requires": {
        "semver": "^6.0.0"
      }
    },
    "map-cache": {
      "version": "0.2.2",
      "resolved": "https://registry.npmjs.org/map-cache/-/map-cache-0.2.2.tgz",
      "integrity": "sha1-wyq9C9ZSXZsFFkW7TyasXcmKDb8="
    },
    "map-visit": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/map-visit/-/map-visit-1.0.0.tgz",
      "integrity": "sha1-7Nyo8TFE5mDxtb1B8S80edmN+48=",
      "requires": {
        "object-visit": "^1.0.0"
      }
    },
    "media-typer": {
      "version": "0.3.0",
      "resolved": "https://registry.npmjs.org/media-typer/-/media-typer-0.3.0.tgz",
      "integrity": "sha1-hxDXrwqmJvj/+hzgAWhUUmMlV0g="
    },
    "merge-descriptors": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/merge-descriptors/-/merge-descriptors-1.0.1.tgz",
      "integrity": "sha1-sAqqVW3YtEVoFQ7J0blT8/kMu2E="
    },
    "merge2": {
      "version": "1.3.0",
      "resolved": "https://registry.npmjs.org/merge2/-/merge2-1.3.0.tgz",
      "integrity": "sha512-2j4DAdlBOkiSZIsaXk4mTE3sRS02yBHAtfy127xRV3bQUFqXkjHCHLW6Scv7DwNRbIWNHH8zpnz9zMaKXIdvYw=="
    },
    "methmeth": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/methmeth/-/methmeth-1.1.0.tgz",
      "integrity": "sha1-6AomYY5S9cQiKGG7dIUQvRDikIk="
    },
    "methods": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/methods/-/methods-1.1.2.tgz",
      "integrity": "sha1-VSmk1nZUE07cxSZmVoNbD4Ua/O4="
    },
    "micromatch": {
      "version": "3.1.10",
      "resolved": "https://registry.npmjs.org/micromatch/-/micromatch-3.1.10.tgz",
      "integrity": "sha512-MWikgl9n9M3w+bpsY3He8L+w9eF9338xRl8IAO5viDizwSzziFEyUzo2xrrloB64ADbTf8uA8vRqqttDTOmccg==",
      "requires": {
        "arr-diff": "^4.0.0",
        "array-unique": "^0.3.2",
        "braces": "^2.3.1",
        "define-property": "^2.0.2",
        "extend-shallow": "^3.0.2",
        "extglob": "^2.0.4",
        "fragment-cache": "^0.2.1",
        "kind-of": "^6.0.2",
        "nanomatch": "^1.2.9",
        "object.pick": "^1.3.0",
        "regex-not": "^1.0.0",
        "snapdragon": "^0.8.1",
        "to-regex": "^3.0.2"
      }
    },
    "mime": {
      "version": "1.6.0",
      "resolved": "https://registry.npmjs.org/mime/-/mime-1.6.0.tgz",
      "integrity": "sha512-x0Vn8spI+wuJ1O6S7gnbaQg8Pxh4NNHb7KSINmEWKiPE4RKOplvijn+NkmYmmRgP68mc70j2EbeTFRsrswaQeg=="
    },
    "mime-db": {
      "version": "1.43.0",
      "resolved": "https://registry.npmjs.org/mime-db/-/mime-db-1.43.0.tgz",
      "integrity": "sha512-+5dsGEEovYbT8UY9yD7eE4XTc4UwJ1jBYlgaQQF38ENsKR3wj/8q8RFZrF9WIZpB2V1ArTVFUva8sAul1NzRzQ=="
    },
    "mime-types": {
      "version": "2.1.26",
      "resolved": "https://registry.npmjs.org/mime-types/-/mime-types-2.1.26.tgz",
      "integrity": "sha512-01paPWYgLrkqAyrlDorC1uDwl2p3qZT7yl806vW7DvDoxwXi46jsjFbg+WdwotBIk6/MbEhO/dh5aZ5sNj/dWQ==",
      "requires": {
        "mime-db": "1.43.0"
      }
    },
    "mimic-fn": {
      "version": "2.1.0",
      "resolved": "https://registry.npmjs.org/mimic-fn/-/mimic-fn-2.1.0.tgz",
      "integrity": "sha512-OqbOk5oEQeAZ8WXWydlu9HJjz9WVdEIvamMCcXmuqUYjTknH/sqsWvhQ3vgwKFRR1HpjvNBKQ37nbJgYzGqGcg=="
    },
    "minimatch": {
      "version": "3.0.4",
      "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-3.0.4.tgz",
      "integrity": "sha512-yJHVQEhyqPLUTgt9B83PXu6W3rx4MvvHvSUvToogpwoGDOUQ+yDrR0HRot+yOCdCO7u4hX3pWft6kWBBcqh0UA==",
      "requires": {
        "brace-expansion": "^1.1.7"
      }
    },
    "minimist": {
      "version": "1.2.5",
      "resolved": "https://registry.npmjs.org/minimist/-/minimist-1.2.5.tgz",
      "integrity": "sha512-FM9nNUYrRBAELZQT3xeZQ7fmMOBg6nWNmJKTcgsJeaLstP/UODVpGsr5OhXhhXg6f+qtJ8uiZ+PUxkDWcgIXLw=="
    },
    "mixin-deep": {
      "version": "1.3.2",
      "resolved": "https://registry.npmjs.org/mixin-deep/-/mixin-deep-1.3.2.tgz",
      "integrity": "sha512-WRoDn//mXBiJ1H40rqa3vH0toePwSsGb45iInWlTySa+Uu4k3tYUSxa2v1KqAiLtvlrSzaExqS1gtk96A9zvEA==",
      "requires": {
        "for-in": "^1.0.2",
        "is-extendable": "^1.0.1"
      },
      "dependencies": {
        "is-extendable": {
          "version": "1.0.1",
          "resolved": "https://registry.npmjs.org/is-extendable/-/is-extendable-1.0.1.tgz",
          "integrity": "sha512-arnXMxT1hhoKo9k1LZdmlNyJdDDfy2v0fXjFlmok4+i8ul/6WlbVge9bhM74OpNPQPMGUToDtz+KXa1PneJxOA==",
          "requires": {
            "is-plain-object": "^2.0.4"
          }
        }
      }
    },
    "modelo": {
      "version": "4.2.3",
      "resolved": "https://registry.npmjs.org/modelo/-/modelo-4.2.3.tgz",
      "integrity": "sha512-9DITV2YEMcw7XojdfvGl3gDD8J9QjZTJ7ZOUuSAkP+F3T6rDbzMJuPktxptsdHYEvZcmXrCD3LMOhdSAEq6zKA=="
    },
    "ms": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.0.0.tgz",
      "integrity": "sha1-VgiurfwAvmwpAd9fmGF4jeDVl8g="
    },
    "nan": {
      "version": "2.14.0",
      "resolved": "https://registry.npmjs.org/nan/-/nan-2.14.0.tgz",
      "integrity": "sha512-INOFj37C7k3AfaNTtX8RhsTw7qRy7eLET14cROi9+5HAVbbHuIWUHEauBv5qT4Av2tWasiTY1Jw6puUNqRJXQg=="
    },
    "nanomatch": {
      "version": "1.2.13",
      "resolved": "https://registry.npmjs.org/nanomatch/-/nanomatch-1.2.13.tgz",
      "integrity": "sha512-fpoe2T0RbHwBTBUOftAfBPaDEi06ufaUai0mE6Yn1kacc3SnTErfb/h+X94VXzI64rKFHYImXSvdwGGCmwOqCA==",
      "requires": {
        "arr-diff": "^4.0.0",
        "array-unique": "^0.3.2",
        "define-property": "^2.0.2",
        "extend-shallow": "^3.0.2",
        "fragment-cache": "^0.2.1",
        "is-windows": "^1.0.2",
        "kind-of": "^6.0.2",
        "object.pick": "^1.3.0",
        "regex-not": "^1.0.0",
        "snapdragon": "^0.8.1",
        "to-regex": "^3.0.1"
      }
    },
    "negotiator": {
      "version": "0.6.2",
      "resolved": "https://registry.npmjs.org/negotiator/-/negotiator-0.6.2.tgz",
      "integrity": "sha512-hZXc7K2e+PgeI1eDBe/10Ard4ekbfrrqG8Ep+8Jmf4JID2bNg7NvCPOZN+kfF574pFQI7mum2AUqDidoKqcTOw=="
    },
    "node-fetch": {
      "version": "2.6.0",
      "resolved": "https://registry.npmjs.org/node-fetch/-/node-fetch-2.6.0.tgz",
      "integrity": "sha512-8dG4H5ujfvFiqDmVu9fQ5bOHUC15JMjMY/Zumv26oOvvVJjM67KF8koCWIabKQ1GJIa9r2mMZscBq/TbdOcmNA=="
    },
    "node-forge": {
      "version": "0.9.1",
      "resolved": "https://registry.npmjs.org/node-forge/-/node-forge-0.9.1.tgz",
      "integrity": "sha512-G6RlQt5Sb4GMBzXvhfkeFmbqR6MzhtnT7VTHuLadjkii3rdYHNdw0m8zA4BTxVIh68FicCQ2NSUANpsqkr9jvQ=="
    },
    "number-is-nan": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/number-is-nan/-/number-is-nan-1.0.1.tgz",
      "integrity": "sha1-CXtgK1NCKlIsGvuHkDGDNpQaAR0="
    },
    "oauth-sign": {
      "version": "0.8.2",
      "resolved": "https://registry.npmjs.org/oauth-sign/-/oauth-sign-0.8.2.tgz",
      "integrity": "sha1-Rqarfwrq2N6unsBWV4C31O/rnUM="
    },
    "object-copy": {
      "version": "0.1.0",
      "resolved": "https://registry.npmjs.org/object-copy/-/object-copy-0.1.0.tgz",
      "integrity": "sha1-fn2Fi3gb18mRpBupde04EnVOmYw=",
      "requires": {
        "copy-descriptor": "^0.1.0",
        "define-property": "^0.2.5",
        "kind-of": "^3.0.3"
      },
      "dependencies": {
        "define-property": {
          "version": "0.2.5",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-0.2.5.tgz",
          "integrity": "sha1-w1se+RjsPJkPmlvFe+BKrOxcgRY=",
          "requires": {
            "is-descriptor": "^0.1.0"
          }
        },
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-3.2.2.tgz",
          "integrity": "sha1-MeohpzS6ubuw8yRm2JOupR5KPGQ=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "object-keys": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/object-keys/-/object-keys-1.1.1.tgz",
      "integrity": "sha512-NuAESUOUMrlIXOfHKzD6bpPu3tYt3xvjNdRIQ+FeT0lNb4K8WR70CaDxhuNguS2XG+GjkyMwOzsN5ZktImfhLA=="
    },
    "object-visit": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/object-visit/-/object-visit-1.0.1.tgz",
      "integrity": "sha1-95xEk68MU3e1n+OdOV5BBC3QRbs=",
      "requires": {
        "isobject": "^3.0.0"
      }
    },
    "object.pick": {
      "version": "1.3.0",
      "resolved": "https://registry.npmjs.org/object.pick/-/object.pick-1.3.0.tgz",
      "integrity": "sha1-h6EKxMFpS9Lhy/U1kaZhQftd10c=",
      "requires": {
        "isobject": "^3.0.1"
      }
    },
    "on-finished": {
      "version": "2.3.0",
      "resolved": "https://registry.npmjs.org/on-finished/-/on-finished-2.3.0.tgz",
      "integrity": "sha1-IPEzZIGwg811M3mSoWlxqi2QaUc=",
      "requires": {
        "ee-first": "1.1.1"
      }
    },
    "once": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/once/-/once-1.4.0.tgz",
      "integrity": "sha1-WDsap3WWHUsROsF9nFC6753Xa9E=",
      "requires": {
        "wrappy": "1"
      }
    },
    "onetime": {
      "version": "5.1.0",
      "resolved": "https://registry.npmjs.org/onetime/-/onetime-5.1.0.tgz",
      "integrity": "sha512-5NcSkPHhwTVFIQN+TUqXoS5+dlElHXdpAWu9I0HP20YOtIi+aZ0Ct82jdlILDxjLEAWwvm+qj1m6aEtsDVmm6Q==",
      "requires": {
        "mimic-fn": "^2.1.0"
      }
    },
    "optjs": {
      "version": "3.2.2",
      "resolved": "https://registry.npmjs.org/optjs/-/optjs-3.2.2.tgz",
      "integrity": "sha1-aabOicRCpEQDFBrS+bNwvVu29O4="
    },
    "os-locale": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/os-locale/-/os-locale-1.4.0.tgz",
      "integrity": "sha1-IPnxeuKe00XoveWDsT0gCYA8FNk=",
      "requires": {
        "lcid": "^1.0.0"
      }
    },
    "p-defer": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/p-defer/-/p-defer-1.0.0.tgz",
      "integrity": "sha1-n26xgvbJqozXQwBKfU+WsZaw+ww="
    },
    "p-limit": {
      "version": "2.2.2",
      "resolved": "https://registry.npmjs.org/p-limit/-/p-limit-2.2.2.tgz",
      "integrity": "sha512-WGR+xHecKTr7EbUEhyLSh5Dube9JtdiG78ufaeLxTgpudf/20KqyMioIUZJAezlTIi6evxuoUs9YXc11cU+yzQ==",
      "requires": {
        "p-try": "^2.0.0"
      }
    },
    "p-try": {
      "version": "2.2.0",
      "resolved": "https://registry.npmjs.org/p-try/-/p-try-2.2.0.tgz",
      "integrity": "sha512-R4nPAVTAU0B9D35/Gk3uJf/7XYbQcyohSKdvAxIRSNghFl4e71hVoGnBNQz9cWaXxO2I10KTC+3jMdvvoKw6dQ=="
    },
    "parseurl": {
      "version": "1.3.3",
      "resolved": "https://registry.npmjs.org/parseurl/-/parseurl-1.3.3.tgz",
      "integrity": "sha512-CiyeOxFT/JZyN5m0z9PfXw4SCBJ6Sygz1Dpl0wqjlhDEGGBP1GnsUVEL0p63hoG1fcj3fHynXi9NYO4nWOL+qQ=="
    },
    "pascalcase": {
      "version": "0.1.1",
      "resolved": "https://registry.npmjs.org/pascalcase/-/pascalcase-0.1.1.tgz",
      "integrity": "sha1-s2PlXoAGym/iF4TS2yK9FdeRfxQ="
    },
    "path-dirname": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/path-dirname/-/path-dirname-1.0.2.tgz",
      "integrity": "sha1-zDPSTVJeCZpTiMAzbG4yuRYGCeA="
    },
    "path-is-absolute": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/path-is-absolute/-/path-is-absolute-1.0.1.tgz",
      "integrity": "sha1-F0uSaHNVNP+8es5r9TpanhtcX18="
    },
    "path-to-regexp": {
      "version": "0.1.7",
      "resolved": "https://registry.npmjs.org/path-to-regexp/-/path-to-regexp-0.1.7.tgz",
      "integrity": "sha1-32BBeABfUi8V60SQ5yR6G/qmf4w="
    },
    "path-type": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/path-type/-/path-type-3.0.0.tgz",
      "integrity": "sha512-T2ZUsdZFHgA3u4e5PfPbjd7HDDpxPnQb5jN0SrDsjNSuVXHJqtwTnWqG0B1jZrgmJ/7lj1EmVIByWt1gxGkWvg==",
      "requires": {
        "pify": "^3.0.0"
      },
      "dependencies": {
        "pify": {
          "version": "3.0.0",
          "resolved": "https://registry.npmjs.org/pify/-/pify-3.0.0.tgz",
          "integrity": "sha1-5aSs0sEB/fPZpNB/DbxNtJ3SgXY="
        }
      }
    },
    "performance-now": {
      "version": "0.2.0",
      "resolved": "https://registry.npmjs.org/performance-now/-/performance-now-0.2.0.tgz",
      "integrity": "sha1-M+8wxcd9TqIcWlOGnZG1bY8lVeU="
    },
    "pify": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/pify/-/pify-4.0.1.tgz",
      "integrity": "sha512-uB80kBFb/tfd68bVleG9T5GGsGPjJrLAUpR5PZIrhBnIaRTQRjqdJSsIKkOP6OAIFbj7GOrcudc5pNjZ+geV2g=="
    },
    "posix-character-classes": {
      "version": "0.1.1",
      "resolved": "https://registry.npmjs.org/posix-character-classes/-/posix-character-classes-0.1.1.tgz",
      "integrity": "sha1-AerA/jta9xoqbAL+q7jB/vfgDqs="
    },
    "power-assert": {
      "version": "1.6.1",
      "resolved": "https://registry.npmjs.org/power-assert/-/power-assert-1.6.1.tgz",
      "integrity": "sha512-VWkkZV6Y+W8qLX/PtJu2Ur2jDPIs0a5vbP0TpKeybNcIXmT4vcKoVkyTp5lnQvTpY/DxacAZ4RZisHRHLJcAZQ==",
      "requires": {
        "define-properties": "^1.1.2",
        "empower": "^1.3.1",
        "power-assert-formatter": "^1.4.1",
        "universal-deep-strict-equal": "^1.2.1",
        "xtend": "^4.0.0"
      }
    },
    "power-assert-context-formatter": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-context-formatter/-/power-assert-context-formatter-1.2.0.tgz",
      "integrity": "sha512-HLNEW8Bin+BFCpk/zbyKwkEu9W8/zThIStxGo7weYcFkKgMuGCHUJhvJeBGXDZf0Qm2xis4pbnnciGZiX0EpSg==",
      "requires": {
        "core-js": "^2.0.0",
        "power-assert-context-traversal": "^1.2.0"
      }
    },
    "power-assert-context-reducer-ast": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-context-reducer-ast/-/power-assert-context-reducer-ast-1.2.0.tgz",
      "integrity": "sha512-EgOxmZ/Lb7tw4EwSKX7ZnfC0P/qRZFEG28dx/690qvhmOJ6hgThYFm5TUWANDLK5NiNKlPBi5WekVGd2+5wPrw==",
      "requires": {
        "acorn": "^5.0.0",
        "acorn-es7-plugin": "^1.0.12",
        "core-js": "^2.0.0",
        "espurify": "^1.6.0",
        "estraverse": "^4.2.0"
      }
    },
    "power-assert-context-traversal": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-context-traversal/-/power-assert-context-traversal-1.2.0.tgz",
      "integrity": "sha512-NFoHU6g2umNajiP2l4qb0BRWD773Aw9uWdWYH9EQsVwIZnog5bd2YYLFCVvaxWpwNzWeEfZIon2xtyc63026pQ==",
      "requires": {
        "core-js": "^2.0.0",
        "estraverse": "^4.1.0"
      }
    },
    "power-assert-formatter": {
      "version": "1.4.1",
      "resolved": "https://registry.npmjs.org/power-assert-formatter/-/power-assert-formatter-1.4.1.tgz",
      "integrity": "sha1-XcEl7VCj37HdomwZNH879Y7CiEo=",
      "requires": {
        "core-js": "^2.0.0",
        "power-assert-context-formatter": "^1.0.7",
        "power-assert-context-reducer-ast": "^1.0.7",
        "power-assert-renderer-assertion": "^1.0.7",
        "power-assert-renderer-comparison": "^1.0.7",
        "power-assert-renderer-diagram": "^1.0.7",
        "power-assert-renderer-file": "^1.0.7"
      }
    },
    "power-assert-renderer-assertion": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-renderer-assertion/-/power-assert-renderer-assertion-1.2.0.tgz",
      "integrity": "sha512-3F7Q1ZLmV2ZCQv7aV7NJLNK9G7QsostrhOU7U0RhEQS/0vhEqrRg2jEJl1jtUL4ZyL2dXUlaaqrmPv5r9kRvIg==",
      "requires": {
        "power-assert-renderer-base": "^1.1.1",
        "power-assert-util-string-width": "^1.2.0"
      }
    },
    "power-assert-renderer-base": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/power-assert-renderer-base/-/power-assert-renderer-base-1.1.1.tgz",
      "integrity": "sha1-lqZQxv0F7hvB9mtUrWFELIs/Y+s="
    },
    "power-assert-renderer-comparison": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-renderer-comparison/-/power-assert-renderer-comparison-1.2.0.tgz",
      "integrity": "sha512-7c3RKPDBKK4E3JqdPtYRE9cM8AyX4LC4yfTvvTYyx8zSqmT5kJnXwzR0yWQLOavACllZfwrAGQzFiXPc5sWa+g==",
      "requires": {
        "core-js": "^2.0.0",
        "diff-match-patch": "^1.0.0",
        "power-assert-renderer-base": "^1.1.1",
        "stringifier": "^1.3.0",
        "type-name": "^2.0.1"
      }
    },
    "power-assert-renderer-diagram": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-renderer-diagram/-/power-assert-renderer-diagram-1.2.0.tgz",
      "integrity": "sha512-JZ6PC+DJPQqfU6dwSmpcoD7gNnb/5U77bU5KgNwPPa+i1Pxiz6UuDeM3EUBlhZ1HvH9tMjI60anqVyi5l2oNdg==",
      "requires": {
        "core-js": "^2.0.0",
        "power-assert-renderer-base": "^1.1.1",
        "power-assert-util-string-width": "^1.2.0",
        "stringifier": "^1.3.0"
      }
    },
    "power-assert-renderer-file": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-renderer-file/-/power-assert-renderer-file-1.2.0.tgz",
      "integrity": "sha512-/oaVrRbeOtGoyyd7e4IdLP/jIIUFJdqJtsYzP9/88R39CMnfF/S/rUc8ZQalENfUfQ/wQHu+XZYRMaCEZmEesg==",
      "requires": {
        "power-assert-renderer-base": "^1.1.1"
      }
    },
    "power-assert-util-string-width": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/power-assert-util-string-width/-/power-assert-util-string-width-1.2.0.tgz",
      "integrity": "sha512-lX90G0igAW0iyORTILZ/QjZWsa1MZ6VVY3L0K86e2eKun3S4LKPH4xZIl8fdeMYLfOjkaszbNSzf1uugLeAm2A==",
      "requires": {
        "eastasianwidth": "^0.2.0"
      }
    },
    "process-nextick-args": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/process-nextick-args/-/process-nextick-args-2.0.1.tgz",
      "integrity": "sha512-3ouUOpQhtgrbOa17J7+uxOTpITYWaGP7/AhoR3+A+/1e9skrzelGi/dXzEYyvbxubEF6Wn2ypscTKiKJFFn1ag=="
    },
    "protobufjs": {
      "version": "6.8.9",
      "resolved": "https://registry.npmjs.org/protobufjs/-/protobufjs-6.8.9.tgz",
      "integrity": "sha512-j2JlRdUeL/f4Z6x4aU4gj9I2LECglC+5qR2TrWb193Tla1qfdaNQTZ8I27Pt7K0Ajmvjjpft7O3KWTGciz4gpw==",
      "requires": {
        "@protobufjs/aspromise": "^1.1.2",
        "@protobufjs/base64": "^1.1.2",
        "@protobufjs/codegen": "^2.0.4",
        "@protobufjs/eventemitter": "^1.1.0",
        "@protobufjs/fetch": "^1.1.0",
        "@protobufjs/float": "^1.0.2",
        "@protobufjs/inquire": "^1.1.0",
        "@protobufjs/path": "^1.1.2",
        "@protobufjs/pool": "^1.1.0",
        "@protobufjs/utf8": "^1.1.0",
        "@types/long": "^4.0.0",
        "@types/node": "^10.1.0",
        "long": "^4.0.0"
      }
    },
    "proxy-addr": {
      "version": "2.0.6",
      "resolved": "https://registry.npmjs.org/proxy-addr/-/proxy-addr-2.0.6.tgz",
      "integrity": "sha512-dh/frvCBVmSsDYzw6n926jv974gddhkFPfiN8hPOi30Wax25QZyZEGveluCgliBnqmuM+UJmBErbAUFIoDbjOw==",
      "requires": {
        "forwarded": "~0.1.2",
        "ipaddr.js": "1.9.1"
      }
    },
    "pseudomap": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/pseudomap/-/pseudomap-1.0.2.tgz",
      "integrity": "sha1-8FKijacOYYkX7wqKw0wa5aaChrM="
    },
    "pump": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/pump/-/pump-3.0.0.tgz",
      "integrity": "sha512-LwZy+p3SFs1Pytd/jYct4wpv49HiYCqd9Rlc5ZVdk0V+8Yzv6jR5Blk3TRmPL1ft69TxP0IMZGJ+WPFU2BFhww==",
      "requires": {
        "end-of-stream": "^1.1.0",
        "once": "^1.3.1"
      }
    },
    "pumpify": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/pumpify/-/pumpify-2.0.1.tgz",
      "integrity": "sha512-m7KOje7jZxrmutanlkS1daj1dS6z6BgslzOXmcSEpIlCxM3VJH7lG5QLeck/6hgF6F4crFf01UtQmNsJfweTAw==",
      "requires": {
        "duplexify": "^4.1.1",
        "inherits": "^2.0.3",
        "pump": "^3.0.0"
      },
      "dependencies": {
        "duplexify": {
          "version": "4.1.1",
          "resolved": "https://registry.npmjs.org/duplexify/-/duplexify-4.1.1.tgz",
          "integrity": "sha512-DY3xVEmVHTv1wSzKNbwoU6nVjzI369Y6sPoqfYr0/xlx3IdX2n94xIszTcjPO8W8ZIv0Wb0PXNcjuZyT4wiICA==",
          "requires": {
            "end-of-stream": "^1.4.1",
            "inherits": "^2.0.3",
            "readable-stream": "^3.1.1",
            "stream-shift": "^1.0.0"
          }
        }
      }
    },
    "punycode": {
      "version": "1.4.1",
      "resolved": "https://registry.npmjs.org/punycode/-/punycode-1.4.1.tgz",
      "integrity": "sha1-wNWmOycYgArY4esPpSachN1BhF4="
    },
    "qs": {
      "version": "6.7.0",
      "resolved": "https://registry.npmjs.org/qs/-/qs-6.7.0.tgz",
      "integrity": "sha512-VCdBRNFTX1fyE7Nb6FYoURo/SPe62QCaAyzJvUjwRaIsc+NePBEniHlvxFmmX56+HZphIGtV0XeCirBtpDrTyQ=="
    },
    "range-parser": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/range-parser/-/range-parser-1.2.1.tgz",
      "integrity": "sha512-Hrgsx+orqoygnmhFbKaHE6c296J+HTAQXoxEF6gNupROmmGJRoyzfG3ccAveqCBrwr/2yxQ5BVd/GTl5agOwSg=="
    },
    "raw-body": {
      "version": "2.4.0",
      "resolved": "https://registry.npmjs.org/raw-body/-/raw-body-2.4.0.tgz",
      "integrity": "sha512-4Oz8DUIwdvoa5qMJelxipzi/iJIi40O5cGV1wNYp5hvZP8ZN0T+jiNkL0QepXs+EsQ9XJ8ipEDoiH70ySUJP3Q==",
      "requires": {
        "bytes": "3.1.0",
        "http-errors": "1.7.2",
        "iconv-lite": "0.4.24",
        "unpipe": "1.0.0"
      }
    },
    "readable-stream": {
      "version": "3.6.0",
      "resolved": "https://registry.npmjs.org/readable-stream/-/readable-stream-3.6.0.tgz",
      "integrity": "sha512-BViHy7LKeTz4oNnkcLJ+lVSL6vpiFeX6/d3oSH8zCW7UxP2onchk+vTGB143xuFjHS3deTgkKoXXymXqymiIdA==",
      "requires": {
        "inherits": "^2.0.3",
        "string_decoder": "^1.1.1",
        "util-deprecate": "^1.0.1"
      }
    },
    "regex-not": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/regex-not/-/regex-not-1.0.2.tgz",
      "integrity": "sha512-J6SDjUgDxQj5NusnOtdFxDwN/+HWykR8GELwctJ7mdqhcyy1xEc4SRFHUXvxTp661YaVKAjfRLZ9cCqS6tn32A==",
      "requires": {
        "extend-shallow": "^3.0.2",
        "safe-regex": "^1.1.0"
      }
    },
    "repeat-element": {
      "version": "1.1.3",
      "resolved": "https://registry.npmjs.org/repeat-element/-/repeat-element-1.1.3.tgz",
      "integrity": "sha512-ahGq0ZnV5m5XtZLMb+vP76kcAM5nkLqk0lpqAuojSKGgQtn4eRi4ZZGm2olo2zKFH+sMsWaqOCW1dqAnOru72g=="
    },
    "repeat-string": {
      "version": "1.6.1",
      "resolved": "https://registry.npmjs.org/repeat-string/-/repeat-string-1.6.1.tgz",
      "integrity": "sha1-jcrkcOHIirwtYA//Sndihtp15jc="
    },
    "request": {
      "version": "2.81.0",
      "resolved": "https://registry.npmjs.org/request/-/request-2.81.0.tgz",
      "integrity": "sha1-xpKJRqDgbF+Nb4qTM0af/aRimKA=",
      "requires": {
        "aws-sign2": "~0.6.0",
        "aws4": "^1.2.1",
        "caseless": "~0.12.0",
        "combined-stream": "~1.0.5",
        "extend": "~3.0.0",
        "forever-agent": "~0.6.1",
        "form-data": "~2.1.1",
        "har-validator": "~4.2.1",
        "hawk": "~3.1.3",
        "http-signature": "~1.1.0",
        "is-typedarray": "~1.0.0",
        "isstream": "~0.1.2",
        "json-stringify-safe": "~5.0.1",
        "mime-types": "~2.1.7",
        "oauth-sign": "~0.8.1",
        "performance-now": "^0.2.0",
        "qs": "~6.4.0",
        "safe-buffer": "^5.0.1",
        "stringstream": "~0.0.4",
        "tough-cookie": "~2.3.0",
        "tunnel-agent": "^0.6.0",
        "uuid": "^3.0.0"
      },
      "dependencies": {
        "qs": {
          "version": "6.4.0",
          "resolved": "https://registry.npmjs.org/qs/-/qs-6.4.0.tgz",
          "integrity": "sha1-E+JtKK1rD/qpExLNO/cI7TUecjM="
        }
      }
    },
    "resolve-url": {
      "version": "0.2.1",
      "resolved": "https://registry.npmjs.org/resolve-url/-/resolve-url-0.2.1.tgz",
      "integrity": "sha1-LGN/53yJOv0qZj/iGqkIAGjiBSo="
    },
    "ret": {
      "version": "0.1.15",
      "resolved": "https://registry.npmjs.org/ret/-/ret-0.1.15.tgz",
      "integrity": "sha512-TTlYpa+OL+vMMNG24xSlQGEJ3B/RzEfUlLct7b5G/ytav+wPrplCpVMFuwzXbkecJrb6IYo1iFb0S9v37754mg=="
    },
    "retry-axios": {
      "version": "0.3.2",
      "resolved": "https://registry.npmjs.org/retry-axios/-/retry-axios-0.3.2.tgz",
      "integrity": "sha512-jp4YlI0qyDFfXiXGhkCOliBN1G7fRH03Nqy8YdShzGqbY5/9S2x/IR6C88ls2DFkbWuL3ASkP7QD3pVrNpPgwQ=="
    },
    "retry-request": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/retry-request/-/retry-request-4.1.1.tgz",
      "integrity": "sha512-BINDzVtLI2BDukjWmjAIRZ0oglnCAkpP2vQjM3jdLhmT62h0xnQgciPwBRDAvHqpkPT2Wo1XuUyLyn6nbGrZQQ==",
      "requires": {
        "debug": "^4.1.1",
        "through2": "^3.0.1"
      },
      "dependencies": {
        "debug": {
          "version": "4.1.1",
          "resolved": "https://registry.npmjs.org/debug/-/debug-4.1.1.tgz",
          "integrity": "sha512-pYAIzeRo8J6KPEaJ0VWOh5Pzkbw/RetuzehGM7QRRX5he4fPHx2rdKMB256ehJCkX+XRQm16eZLqLNS8RSZXZw==",
          "requires": {
            "ms": "^2.1.1"
          }
        },
        "ms": {
          "version": "2.1.2",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
          "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
        }
      }
    },
    "safe-buffer": {
      "version": "5.1.2",
      "resolved": "https://registry.npmjs.org/safe-buffer/-/safe-buffer-5.1.2.tgz",
      "integrity": "sha512-Gd2UZBJDkXlY7GbJxfsE8/nvKkUEU1G38c1siN6QP6a9PT9MmHB8GnpscSmMJSoF8LOIrt8ud/wPtojys4G6+g=="
    },
    "safe-regex": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/safe-regex/-/safe-regex-1.1.0.tgz",
      "integrity": "sha1-QKNmnzsHfR6UPURinhV91IAjvy4=",
      "requires": {
        "ret": "~0.1.10"
      }
    },
    "safer-buffer": {
      "version": "2.1.2",
      "resolved": "https://registry.npmjs.org/safer-buffer/-/safer-buffer-2.1.2.tgz",
      "integrity": "sha512-YZo3K82SD7Riyi0E1EQPojLz7kpepnSQI9IyPbHHg1XXXevb5dJI7tpyN2ADxGcQbHG7vcyRHk0cbwqcQriUtg=="
    },
    "semver": {
      "version": "6.3.0",
      "resolved": "https://registry.npmjs.org/semver/-/semver-6.3.0.tgz",
      "integrity": "sha512-b39TBaTSfV6yBrapU89p5fKekE2m/NwnDocOVruQFS1/veMgdzuPcnOM34M6CwxW8jH/lxEa5rBoDeUwu5HHTw=="
    },
    "send": {
      "version": "0.17.1",
      "resolved": "https://registry.npmjs.org/send/-/send-0.17.1.tgz",
      "integrity": "sha512-BsVKsiGcQMFwT8UxypobUKyv7irCNRHk1T0G680vk88yf6LBByGcZJOTJCrTP2xVN6yI+XjPJcNuE3V4fT9sAg==",
      "requires": {
        "debug": "2.6.9",
        "depd": "~1.1.2",
        "destroy": "~1.0.4",
        "encodeurl": "~1.0.2",
        "escape-html": "~1.0.3",
        "etag": "~1.8.1",
        "fresh": "0.5.2",
        "http-errors": "~1.7.2",
        "mime": "1.6.0",
        "ms": "2.1.1",
        "on-finished": "~2.3.0",
        "range-parser": "~1.2.1",
        "statuses": "~1.5.0"
      },
      "dependencies": {
        "ms": {
          "version": "2.1.1",
          "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.1.tgz",
          "integrity": "sha512-tgp+dl5cGk28utYktBsrFqA7HKgrhgPsg6Z/EfhWI4gl1Hwq8B/GmY/0oXZ6nF8hDVesS/FpnYaD/kOWhYQvyg=="
        }
      }
    },
    "serve-static": {
      "version": "1.14.1",
      "resolved": "https://registry.npmjs.org/serve-static/-/serve-static-1.14.1.tgz",
      "integrity": "sha512-JMrvUwE54emCYWlTI+hGrGv5I8dEwmco/00EvkzIIsR7MqrHonbD9pO2MOfFnpFntl7ecpZs+3mW+XbQZu9QCg==",
      "requires": {
        "encodeurl": "~1.0.2",
        "escape-html": "~1.0.3",
        "parseurl": "~1.3.3",
        "send": "0.17.1"
      }
    },
    "set-value": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/set-value/-/set-value-2.0.1.tgz",
      "integrity": "sha512-JxHc1weCN68wRY0fhCoXpyK55m/XPHafOmK4UWD7m2CI14GMcFypt4w/0+NV5f/ZMby2F6S2wwA7fgynh9gWSw==",
      "requires": {
        "extend-shallow": "^2.0.1",
        "is-extendable": "^0.1.1",
        "is-plain-object": "^2.0.3",
        "split-string": "^3.0.1"
      },
      "dependencies": {
        "extend-shallow": {
          "version": "2.0.1",
          "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-2.0.1.tgz",
          "integrity": "sha1-Ua99YUrZqfYQ6huvu5idaxxWiQ8=",
          "requires": {
            "is-extendable": "^0.1.0"
          }
        }
      }
    },
    "setprototypeof": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/setprototypeof/-/setprototypeof-1.1.1.tgz",
      "integrity": "sha512-JvdAWfbXeIGaZ9cILp38HntZSFSo3mWg6xGcJJsd+d4aRMOqauag1C63dJfDw7OaMYwEbHMOxEZ1lqVRYP2OAw=="
    },
    "signal-exit": {
      "version": "3.0.3",
      "resolved": "https://registry.npmjs.org/signal-exit/-/signal-exit-3.0.3.tgz",
      "integrity": "sha512-VUJ49FC8U1OxwZLxIbTTrDvLnf/6TDgxZcK8wxR8zs13xpx7xbG60ndBlhNrFi2EMuFRoeDoJO7wthSLq42EjA=="
    },
    "slash": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/slash/-/slash-1.0.0.tgz",
      "integrity": "sha1-xB8vbDn8FtHNF61LXYlhFK5HDVU="
    },
    "snakeize": {
      "version": "0.1.0",
      "resolved": "https://registry.npmjs.org/snakeize/-/snakeize-0.1.0.tgz",
      "integrity": "sha1-EMCI2LWOsHazIpu1oE4jLOEmQi0="
    },
    "snapdragon": {
      "version": "0.8.2",
      "resolved": "https://registry.npmjs.org/snapdragon/-/snapdragon-0.8.2.tgz",
      "integrity": "sha512-FtyOnWN/wCHTVXOMwvSv26d+ko5vWlIDD6zoUJ7LW8vh+ZBC8QdljveRP+crNrtBwioEUWy/4dMtbBjA4ioNlg==",
      "requires": {
        "base": "^0.11.1",
        "debug": "^2.2.0",
        "define-property": "^0.2.5",
        "extend-shallow": "^2.0.1",
        "map-cache": "^0.2.2",
        "source-map": "^0.5.6",
        "source-map-resolve": "^0.5.0",
        "use": "^3.1.0"
      },
      "dependencies": {
        "define-property": {
          "version": "0.2.5",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-0.2.5.tgz",
          "integrity": "sha1-w1se+RjsPJkPmlvFe+BKrOxcgRY=",
          "requires": {
            "is-descriptor": "^0.1.0"
          }
        },
        "extend-shallow": {
          "version": "2.0.1",
          "resolved": "https://registry.npmjs.org/extend-shallow/-/extend-shallow-2.0.1.tgz",
          "integrity": "sha1-Ua99YUrZqfYQ6huvu5idaxxWiQ8=",
          "requires": {
            "is-extendable": "^0.1.0"
          }
        }
      }
    },
    "snapdragon-node": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/snapdragon-node/-/snapdragon-node-2.1.1.tgz",
      "integrity": "sha512-O27l4xaMYt/RSQ5TR3vpWCAB5Kb/czIcqUFOM/C4fYcLnbZUc1PkjTAMjof2pBWaSTwOUd6qUHcFGVGj7aIwnw==",
      "requires": {
        "define-property": "^1.0.0",
        "isobject": "^3.0.0",
        "snapdragon-util": "^3.0.1"
      },
      "dependencies": {
        "define-property": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-1.0.0.tgz",
          "integrity": "sha1-dp66rz9KY6rTr56NMEybvnm/sOY=",
          "requires": {
            "is-descriptor": "^1.0.0"
          }
        },
        "is-accessor-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-accessor-descriptor/-/is-accessor-descriptor-1.0.0.tgz",
          "integrity": "sha512-m5hnHTkcVsPfqx3AKlyttIPb7J+XykHvJP2B9bZDjlhLIoEq4XoK64Vg7boZlVWYK6LUY94dYPEE7Lh0ZkZKcQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-data-descriptor": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/is-data-descriptor/-/is-data-descriptor-1.0.0.tgz",
          "integrity": "sha512-jbRXy1FmtAoCjQkVmIVYwuuqDFUbaOeDjmed1tOGPrsMhtJA4rD9tkgA0F1qJ3gRFRXcHYVkdeaP50Q5rE/jLQ==",
          "requires": {
            "kind-of": "^6.0.0"
          }
        },
        "is-descriptor": {
          "version": "1.0.2",
          "resolved": "https://registry.npmjs.org/is-descriptor/-/is-descriptor-1.0.2.tgz",
          "integrity": "sha512-2eis5WqQGV7peooDyLmNEPUrps9+SXX5c9pL3xEB+4e9HnGuDa7mB7kHxHw4CbqS9k1T2hOH3miL8n8WtiYVtg==",
          "requires": {
            "is-accessor-descriptor": "^1.0.0",
            "is-data-descriptor": "^1.0.0",
            "kind-of": "^6.0.2"
          }
        }
      }
    },
    "snapdragon-util": {
      "version": "3.0.1",
      "resolved": "https://registry.npmjs.org/snapdragon-util/-/snapdragon-util-3.0.1.tgz",
      "integrity": "sha512-mbKkMdQKsjX4BAL4bRYTj21edOf8cN7XHdYUJEe+Zn99hVEYcMvKPct1IqNe7+AZPirn8BCDOQBHQZknqmKlZQ==",
      "requires": {
        "kind-of": "^3.2.0"
      },
      "dependencies": {
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-3.2.2.tgz",
          "integrity": "sha1-MeohpzS6ubuw8yRm2JOupR5KPGQ=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "sntp": {
      "version": "1.0.9",
      "resolved": "https://registry.npmjs.org/sntp/-/sntp-1.0.9.tgz",
      "integrity": "sha1-ZUEYTMkK7qbG57NeJlkIJEPGYZg=",
      "requires": {
        "hoek": "2.x.x"
      }
    },
    "source-map": {
      "version": "0.5.7",
      "resolved": "https://registry.npmjs.org/source-map/-/source-map-0.5.7.tgz",
      "integrity": "sha1-igOdLRAh0i0eoUyA2OpGi6LvP8w="
    },
    "source-map-resolve": {
      "version": "0.5.3",
      "resolved": "https://registry.npmjs.org/source-map-resolve/-/source-map-resolve-0.5.3.tgz",
      "integrity": "sha512-Htz+RnsXWk5+P2slx5Jh3Q66vhQj1Cllm0zvnaY98+NFx+Dv2CF/f5O/t8x+KaNdrdIAsruNzoh/KpialbqAnw==",
      "requires": {
        "atob": "^2.1.2",
        "decode-uri-component": "^0.2.0",
        "resolve-url": "^0.2.1",
        "source-map-url": "^0.4.0",
        "urix": "^0.1.0"
      }
    },
    "source-map-url": {
      "version": "0.4.0",
      "resolved": "https://registry.npmjs.org/source-map-url/-/source-map-url-0.4.0.tgz",
      "integrity": "sha1-PpNdfd1zYxuXZZlW1VEo6HtQhKM="
    },
    "split-array-stream": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/split-array-stream/-/split-array-stream-1.0.3.tgz",
      "integrity": "sha1-0rdajl4Ngk1S/eyLgiWDncLjXfo=",
      "requires": {
        "async": "^2.4.0",
        "is-stream-ended": "^0.1.0"
      }
    },
    "split-string": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/split-string/-/split-string-3.1.0.tgz",
      "integrity": "sha512-NzNVhJDYpwceVVii8/Hu6DKfD2G+NrQHlS/V/qgv763EYudVwEcMQNxd2lh+0VrUByXN/oJkl5grOhYWvQUYiw==",
      "requires": {
        "extend-shallow": "^3.0.0"
      }
    },
    "sshpk": {
      "version": "1.16.1",
      "resolved": "https://registry.npmjs.org/sshpk/-/sshpk-1.16.1.tgz",
      "integrity": "sha512-HXXqVUq7+pcKeLqqZj6mHFUMvXtOJt1uoUx09pFW6011inTMxqI8BA8PM95myrIyyKwdnzjdFjLiE6KBPVtJIg==",
      "requires": {
        "asn1": "~0.2.3",
        "assert-plus": "^1.0.0",
        "bcrypt-pbkdf": "^1.0.0",
        "dashdash": "^1.12.0",
        "ecc-jsbn": "~0.1.1",
        "getpass": "^0.1.1",
        "jsbn": "~0.1.0",
        "safer-buffer": "^2.0.2",
        "tweetnacl": "~0.14.0"
      },
      "dependencies": {
        "assert-plus": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/assert-plus/-/assert-plus-1.0.0.tgz",
          "integrity": "sha1-8S4PPF13sLHN2RRpQuTpbB5N1SU="
        }
      }
    },
    "static-extend": {
      "version": "0.1.2",
      "resolved": "https://registry.npmjs.org/static-extend/-/static-extend-0.1.2.tgz",
      "integrity": "sha1-YICcOcv/VTNyJv1eC1IPNB8ftcY=",
      "requires": {
        "define-property": "^0.2.5",
        "object-copy": "^0.1.0"
      },
      "dependencies": {
        "define-property": {
          "version": "0.2.5",
          "resolved": "https://registry.npmjs.org/define-property/-/define-property-0.2.5.tgz",
          "integrity": "sha1-w1se+RjsPJkPmlvFe+BKrOxcgRY=",
          "requires": {
            "is-descriptor": "^0.1.0"
          }
        }
      }
    },
    "statuses": {
      "version": "1.5.0",
      "resolved": "https://registry.npmjs.org/statuses/-/statuses-1.5.0.tgz",
      "integrity": "sha1-Fhx9rBd2Wf2YEfQ3cfqZOBR4Yow="
    },
    "stream-events": {
      "version": "1.0.5",
      "resolved": "https://registry.npmjs.org/stream-events/-/stream-events-1.0.5.tgz",
      "integrity": "sha512-E1GUzBSgvct8Jsb3v2X15pjzN1tYebtbLaMg+eBOUOAxgbLoSbT2NS91ckc5lJD1KfLjId+jXJRgo0qnV5Nerg==",
      "requires": {
        "stubs": "^3.0.0"
      }
    },
    "stream-shift": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/stream-shift/-/stream-shift-1.0.1.tgz",
      "integrity": "sha512-AiisoFqQ0vbGcZgQPY1cdP2I76glaVA/RauYR4G4thNFgkTqr90yXTo4LYX60Jl+sIlPNHHdGSwo01AvbKUSVQ=="
    },
    "string-format-obj": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/string-format-obj/-/string-format-obj-1.1.1.tgz",
      "integrity": "sha512-Mm+sROy+pHJmx0P/0Bs1uxIX6UhGJGj6xDGQZ5zh9v/SZRmLGevp+p0VJxV7lirrkAmQ2mvva/gHKpnF/pTb+Q=="
    },
    "string-width": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/string-width/-/string-width-1.0.2.tgz",
      "integrity": "sha1-EYvfW4zcUaKn5w0hHgfisLmxB9M=",
      "requires": {
        "code-point-at": "^1.0.0",
        "is-fullwidth-code-point": "^1.0.0",
        "strip-ansi": "^3.0.0"
      }
    },
    "string_decoder": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/string_decoder/-/string_decoder-1.1.1.tgz",
      "integrity": "sha512-n/ShnvDi6FHbbVfviro+WojiFzv+s8MPMHBczVePfUpDJLwoLT0ht1l4YwBCbi8pJAveEEdnkHyPyTP/mzRfwg==",
      "requires": {
        "safe-buffer": "~5.1.0"
      }
    },
    "stringifier": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/stringifier/-/stringifier-1.4.0.tgz",
      "integrity": "sha512-cNsMOqqrcbLcHTXEVmkw9y0fwDwkdgtZwlfyolzpQDoAE1xdNGhQhxBUfiDvvZIKl1hnUEgMv66nHwtMz3OjPw==",
      "requires": {
        "core-js": "^2.0.0",
        "traverse": "^0.6.6",
        "type-name": "^2.0.1"
      }
    },
    "stringstream": {
      "version": "0.0.6",
      "resolved": "https://registry.npmjs.org/stringstream/-/stringstream-0.0.6.tgz",
      "integrity": "sha512-87GEBAkegbBcweToUrdzf3eLhWNg06FJTebl4BVJz/JgWy8CvEr9dRtX5qWphiynMSQlxxi+QqN0z5T32SLlhA=="
    },
    "strip-ansi": {
      "version": "3.0.1",
      "resolved": "https://registry.npmjs.org/strip-ansi/-/strip-ansi-3.0.1.tgz",
      "integrity": "sha1-ajhfuIU9lS1f8F0Oiq+UJ43GPc8=",
      "requires": {
        "ansi-regex": "^2.0.0"
      }
    },
    "stubs": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/stubs/-/stubs-3.0.0.tgz",
      "integrity": "sha1-6NK6H6nJBXAwPAMLaQD31fiavls="
    },
    "teeny-request": {
      "version": "6.0.3",
      "resolved": "https://registry.npmjs.org/teeny-request/-/teeny-request-6.0.3.tgz",
      "integrity": "sha512-TZG/dfd2r6yeji19es1cUIwAlVD8y+/svB1kAC2Y0bjEyysrfbO8EZvJBRwIE6WkwmUoB7uvWLwTIhJbMXZ1Dw==",
      "requires": {
        "http-proxy-agent": "^4.0.0",
        "https-proxy-agent": "^5.0.0",
        "node-fetch": "^2.2.0",
        "stream-events": "^1.0.5",
        "uuid": "^7.0.0"
      },
      "dependencies": {
        "uuid": {
          "version": "7.0.3",
          "resolved": "https://registry.npmjs.org/uuid/-/uuid-7.0.3.tgz",
          "integrity": "sha512-DPSke0pXhTZgoF/d+WSt2QaKMCFSfx7QegxEWT+JOuHF5aWrKEn0G+ztjuJg/gG8/ItK+rbPCD/yNv8yyih6Cg=="
        }
      }
    },
    "through2": {
      "version": "3.0.1",
      "resolved": "https://registry.npmjs.org/through2/-/through2-3.0.1.tgz",
      "integrity": "sha512-M96dvTalPT3YbYLaKaCuwu+j06D/8Jfib0o/PxbVt6Amhv3dUAtW6rTV1jPgJSBG83I/e04Y6xkVdVhSRhi0ww==",
      "requires": {
        "readable-stream": "2 || 3"
      }
    },
    "to-object-path": {
      "version": "0.3.0",
      "resolved": "https://registry.npmjs.org/to-object-path/-/to-object-path-0.3.0.tgz",
      "integrity": "sha1-KXWIt7Dn4KwI4E5nL4XB9JmeF68=",
      "requires": {
        "kind-of": "^3.0.2"
      },
      "dependencies": {
        "is-buffer": {
          "version": "1.1.6",
          "resolved": "https://registry.npmjs.org/is-buffer/-/is-buffer-1.1.6.tgz",
          "integrity": "sha512-NcdALwpXkTm5Zvvbk7owOUSvVvBKDgKP5/ewfXEznmQFfs4ZRmanOeKBTjRVjka3QFoN6XJ+9F3USqfHqTaU5w=="
        },
        "kind-of": {
          "version": "3.2.2",
          "resolved": "https://registry.npmjs.org/kind-of/-/kind-of-3.2.2.tgz",
          "integrity": "sha1-MeohpzS6ubuw8yRm2JOupR5KPGQ=",
          "requires": {
            "is-buffer": "^1.1.5"
          }
        }
      }
    },
    "to-regex": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/to-regex/-/to-regex-3.0.2.tgz",
      "integrity": "sha512-FWtleNAtZ/Ki2qtqej2CXTOayOH9bHDQF+Q48VpWyDXjbYxA4Yz8iDB31zXOBUlOHHKidDbqGVrTUvQMPmBGBw==",
      "requires": {
        "define-property": "^2.0.2",
        "extend-shallow": "^3.0.2",
        "regex-not": "^1.0.2",
        "safe-regex": "^1.1.0"
      }
    },
    "to-regex-range": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/to-regex-range/-/to-regex-range-2.1.1.tgz",
      "integrity": "sha1-fIDBe53+vlmeJzZ+DU3VWQFB2zg=",
      "requires": {
        "is-number": "^3.0.0",
        "repeat-string": "^1.6.1"
      }
    },
    "toidentifier": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/toidentifier/-/toidentifier-1.0.0.tgz",
      "integrity": "sha512-yaOH/Pk/VEhBWWTlhI+qXxDFXlejDGcQipMlyxda9nthulaxLZUNcUqFxokp0vcYnvteJln5FNQDRrxj3YcbVw=="
    },
    "tough-cookie": {
      "version": "2.3.4",
      "resolved": "https://registry.npmjs.org/tough-cookie/-/tough-cookie-2.3.4.tgz",
      "integrity": "sha512-TZ6TTfI5NtZnuyy/Kecv+CnoROnyXn2DN97LontgQpCwsX2XyLYCC0ENhYkehSOwAp8rTQKc/NUIF7BkQ5rKLA==",
      "requires": {
        "punycode": "^1.4.1"
      }
    },
    "traverse": {
      "version": "0.6.6",
      "resolved": "https://registry.npmjs.org/traverse/-/traverse-0.6.6.tgz",
      "integrity": "sha1-y99WD9e5r2MlAv7UD5GMFX6pcTc="
    },
    "tunnel-agent": {
      "version": "0.6.0",
      "resolved": "https://registry.npmjs.org/tunnel-agent/-/tunnel-agent-0.6.0.tgz",
      "integrity": "sha1-J6XeoGs2sEoKmWZ3SykIaPD8QP0=",
      "requires": {
        "safe-buffer": "^5.0.1"
      }
    },
    "tweetnacl": {
      "version": "0.14.5",
      "resolved": "https://registry.npmjs.org/tweetnacl/-/tweetnacl-0.14.5.tgz",
      "integrity": "sha1-WuaBd/GS1EViadEIr6k/+HQ/T2Q="
    },
    "type-is": {
      "version": "1.6.18",
      "resolved": "https://registry.npmjs.org/type-is/-/type-is-1.6.18.tgz",
      "integrity": "sha512-TkRKr9sUTxEH8MdfuCSP7VizJyzRNMjj2J2do2Jr3Kym598JVdEksuzPQCnlFPW4ky9Q+iA+ma9BGm06XQBy8g==",
      "requires": {
        "media-typer": "0.3.0",
        "mime-types": "~2.1.24"
      }
    },
    "type-name": {
      "version": "2.0.2",
      "resolved": "https://registry.npmjs.org/type-name/-/type-name-2.0.2.tgz",
      "integrity": "sha1-7+fUEj2KxSr/9/QMfk3sUmYAj7Q="
    },
    "typedarray": {
      "version": "0.0.6",
      "resolved": "https://registry.npmjs.org/typedarray/-/typedarray-0.0.6.tgz",
      "integrity": "sha1-hnrHTjhkGHsdPUfZlqeOxciDB3c="
    },
    "typedarray-to-buffer": {
      "version": "3.1.5",
      "resolved": "https://registry.npmjs.org/typedarray-to-buffer/-/typedarray-to-buffer-3.1.5.tgz",
      "integrity": "sha512-zdu8XMNEDepKKR+XYOXAVPtWui0ly0NtohUscw+UmaHiAWT8hrV1rr//H6V+0DvJ3OQ19S979M0laLfX8rm82Q==",
      "requires": {
        "is-typedarray": "^1.0.0"
      }
    },
    "union-value": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/union-value/-/union-value-1.0.1.tgz",
      "integrity": "sha512-tJfXmxMeWYnczCVs7XAEvIV7ieppALdyepWMkHkwciRpZraG/xwT+s2JN8+pr1+8jCRf80FFzvr+MpQeeoF4Xg==",
      "requires": {
        "arr-union": "^3.1.0",
        "get-value": "^2.0.6",
        "is-extendable": "^0.1.1",
        "set-value": "^2.0.1"
      }
    },
    "unique-string": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/unique-string/-/unique-string-2.0.0.tgz",
      "integrity": "sha512-uNaeirEPvpZWSgzwsPGtU2zVSTrn/8L5q/IexZmH0eH6SA73CmAA5U4GwORTxQAZs95TAXLNqeLoPPNO5gZfWg==",
      "requires": {
        "crypto-random-string": "^2.0.0"
      }
    },
    "universal-deep-strict-equal": {
      "version": "1.2.2",
      "resolved": "https://registry.npmjs.org/universal-deep-strict-equal/-/universal-deep-strict-equal-1.2.2.tgz",
      "integrity": "sha1-DaSsL3PP95JMgfpN4BjKViyisKc=",
      "requires": {
        "array-filter": "^1.0.0",
        "indexof": "0.0.1",
        "object-keys": "^1.0.0"
      }
    },
    "unpipe": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/unpipe/-/unpipe-1.0.0.tgz",
      "integrity": "sha1-sr9O6FFKrmFltIF4KdIbLvSZBOw="
    },
    "unset-value": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/unset-value/-/unset-value-1.0.0.tgz",
      "integrity": "sha1-g3aHP30jNRef+x5vw6jtDfyKtVk=",
      "requires": {
        "has-value": "^0.3.1",
        "isobject": "^3.0.0"
      },
      "dependencies": {
        "has-value": {
          "version": "0.3.1",
          "resolved": "https://registry.npmjs.org/has-value/-/has-value-0.3.1.tgz",
          "integrity": "sha1-ex9YutpiyoJ+wKIHgCVlSEWZXh8=",
          "requires": {
            "get-value": "^2.0.3",
            "has-values": "^0.1.4",
            "isobject": "^2.0.0"
          },
          "dependencies": {
            "isobject": {
              "version": "2.1.0",
              "resolved": "https://registry.npmjs.org/isobject/-/isobject-2.1.0.tgz",
              "integrity": "sha1-8GVWEJaj8dou9GJy+BXIQNh+DIk=",
              "requires": {
                "isarray": "1.0.0"
              }
            }
          }
        },
        "has-values": {
          "version": "0.1.4",
          "resolved": "https://registry.npmjs.org/has-values/-/has-values-0.1.4.tgz",
          "integrity": "sha1-bWHeldkd/Km5oCCJrThL/49it3E="
        }
      }
    },
    "urix": {
      "version": "0.1.0",
      "resolved": "https://registry.npmjs.org/urix/-/urix-0.1.0.tgz",
      "integrity": "sha1-2pN/emLiH+wf0Y1Js1wpNQZ6bHI="
    },
    "use": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/use/-/use-3.1.1.tgz",
      "integrity": "sha512-cwESVXlO3url9YWlFW/TA9cshCEhtu7IKJ/p5soJ/gGpj7vbvFrAY/eIioQ6Dw23KjZhYgiIo8HOs1nQ2vr/oQ=="
    },
    "util-deprecate": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/util-deprecate/-/util-deprecate-1.0.2.tgz",
      "integrity": "sha1-RQ1Nyfpw3nMnYvvS1KKJgUGaDM8="
    },
    "utils-merge": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/utils-merge/-/utils-merge-1.0.1.tgz",
      "integrity": "sha1-n5VxD1CiZ5R7LMwSR0HBAoQn5xM="
    },
    "uuid": {
      "version": "3.4.0",
      "resolved": "https://registry.npmjs.org/uuid/-/uuid-3.4.0.tgz",
      "integrity": "sha512-HjSDRw6gZE5JMggctHBcjVak08+KEVhSIiDzFnT9S9aegmp85S/bReBVTb4QTFaRNptJ9kuYaNhnbNEOkbKb/A=="
    },
    "vary": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/vary/-/vary-1.1.2.tgz",
      "integrity": "sha1-IpnwLG3tMNSllhsLn3RSShj2NPw="
    },
    "verror": {
      "version": "1.10.0",
      "resolved": "https://registry.npmjs.org/verror/-/verror-1.10.0.tgz",
      "integrity": "sha1-OhBcoXBTr1XW4nDB+CiGguGNpAA=",
      "requires": {
        "assert-plus": "^1.0.0",
        "core-util-is": "1.0.2",
        "extsprintf": "^1.2.0"
      },
      "dependencies": {
        "assert-plus": {
          "version": "1.0.0",
          "resolved": "https://registry.npmjs.org/assert-plus/-/assert-plus-1.0.0.tgz",
          "integrity": "sha1-8S4PPF13sLHN2RRpQuTpbB5N1SU="
        }
      }
    },
    "window-size": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/window-size/-/window-size-0.1.4.tgz",
      "integrity": "sha1-+OGqHuWlPsW/FR/6CXQqatdpeHY="
    },
    "wrap-ansi": {
      "version": "2.1.0",
      "resolved": "https://registry.npmjs.org/wrap-ansi/-/wrap-ansi-2.1.0.tgz",
      "integrity": "sha1-2Pw9KE3QV5T+hJc8rs3Rz4JP3YU=",
      "requires": {
        "string-width": "^1.0.1",
        "strip-ansi": "^3.0.1"
      }
    },
    "wrappy": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/wrappy/-/wrappy-1.0.2.tgz",
      "integrity": "sha1-tSQ9jz7BqjXxNkYFvA0QNuMKtp8="
    },
    "write-file-atomic": {
      "version": "3.0.3",
      "resolved": "https://registry.npmjs.org/write-file-atomic/-/write-file-atomic-3.0.3.tgz",
      "integrity": "sha512-AvHcyZ5JnSfq3ioSyjrBkH9yW4m7Ayk8/9My/DD9onKeu/94fwrMocemO2QAJFAlnnDN+ZDS+ZjAR5ua1/PV/Q==",
      "requires": {
        "imurmurhash": "^0.1.4",
        "is-typedarray": "^1.0.0",
        "signal-exit": "^3.0.2",
        "typedarray-to-buffer": "^3.1.5"
      }
    },
    "xdg-basedir": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/xdg-basedir/-/xdg-basedir-4.0.0.tgz",
      "integrity": "sha512-PSNhEJDejZYV7h50BohL09Er9VaIefr2LMAf3OEmpCkjOi34eYyQYAXUTjEQtZJTKcF0E2UKTh+osDLsgNim9Q=="
    },
    "xtend": {
      "version": "4.0.2",
      "resolved": "https://registry.npmjs.org/xtend/-/xtend-4.0.2.tgz",
      "integrity": "sha512-LKYU1iAXJXUgAXn9URjiu+MWhyUXHsvfp7mcuYm9dSUKK0/CjtrUwFAxD82/mCWbtLsGjFIad0wIsod4zrTAEQ=="
    },
    "y18n": {
      "version": "3.2.1",
      "resolved": "https://registry.npmjs.org/y18n/-/y18n-3.2.1.tgz",
      "integrity": "sha1-bRX7qITAhnnA136I53WegR4H+kE="
    },
    "yallist": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/yallist/-/yallist-3.1.1.tgz",
      "integrity": "sha512-a4UGQaWPH59mOXUYnAG2ewncQS4i4F43Tv3JoAM+s2VDAmS9NsK8GpDMLrCHPksFT7h3K6TOoUNn2pb7RoXx4g=="
    },
    "yargs": {
      "version": "3.32.0",
      "resolved": "https://registry.npmjs.org/yargs/-/yargs-3.32.0.tgz",
      "integrity": "sha1-AwiOnr+edWtpdRYR0qXvWRSCyZU=",
      "requires": {
        "camelcase": "^2.0.1",
        "cliui": "^3.0.3",
        "decamelize": "^1.1.1",
        "os-locale": "^1.4.0",
        "string-width": "^1.0.1",
        "window-size": "^0.1.4",
        "y18n": "^3.2.0"
      }
    }
  }
}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           insta-puller/config.py                                                                              0000644 0001750 0001750 00000001126 13670726436 016706  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            import os
import sqlalchemy

db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

db = sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
        drivername="mysql+pymysql",
        username=db_user,
        password=db_pass,
        database=db_name,
        query={
            "unix_socket": "/cloudsql/{}".format(cloud_sql_connection_name)},
    ),
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,  # 30 seconds
    pool_recycle=1800,  # 30 minutes
)
                                                                                                                                                                                                                                                                                                                                                                                                                                          insta-puller/Dockerfile                                                                             0000644 0001750 0001750 00000001110 13670726436 017052  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            # Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.7-slim

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app                                                                                                                                                                                                                                                                                                                                                                                                                                                        insta-puller/misc/                                                                                  0000755 0001750 0001750 00000000000 13670726436 016022  5                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            insta-puller/misc/test.json                                                                         0000644 0001750 0001750 00000002445 13670726436 017701  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "username": "danaherjohn",
  "post_id": "2277964939800838508",
  "shortcode": "B-c9Qsnn4Fs",
  "direct_link": "https://www.instagram.com/p/B-c9Qsnn4Fs",
  "caption": "Worried about forward stacking pressure when you\\u2019re going for your favorite submissions from bottom? Angle is your friend. Learn to RE-DIRECT forward stacking pressure by turning beyond perpendicular so that the forces of your submission hold COMPLIMENT your opponents stacking pressure rather than fight it. This will off balance your opponent and force him to either back off the pressure or get swept into an even worse situation. Make ANGLE a big part of your triangle and arm bar attacks from underneath and you will experience a lot more success from guard with your submission game!",
  "display_url": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/e35/s1080x1080/91346581_2750066925091902_1868730095985319597_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=106&_nc_ohc=cRNwWxouZQYAX-kpm3x&oh=0570d552b981a0d2229498bcad8f70ab&oe=5EB81E53",
  "thumbnail_src": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/sh0.08/e35/s640x640/91346581_2750066925091902_1868730095985319597_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=106&_nc_ohc=cRNwWxouZQYAX-kpm3x&oh=eaf7238632e04e247ab8b03437d2c5db&oe=5EB7DA97"
}
                                                                                                                                                                                                                           insta-puller/misc/sql_queries.sql                                                                   0000644 0001750 0001750 00000000542 13670726436 021100  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            select * from posts;
select count(distinct username) from posts;
select distinct username from posts;
select count(*) from posts;

select username, count(username) from posts 
	group by username 
    order by count(username) desc;

select username from posts 
	group by username
    order by username;

    
select * from posts
	order by updated_at desc;                                                                                                                                                              insta-puller/package-lock.json                                                                      0000644 0001750 0001750 00000055607 13670726436 020320  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "requires": true,
  "lockfileVersion": 1,
  "dependencies": {
    "@google-cloud/paginator": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/@google-cloud/paginator/-/paginator-2.0.3.tgz",
      "integrity": "sha512-kp/pkb2p/p0d8/SKUu4mOq8+HGwF8NPzHWkj+VKrIPQPyMRw8deZtrO/OcSiy9C/7bpfU5Txah5ltUNfPkgEXg==",
      "requires": {
        "arrify": "^2.0.0",
        "extend": "^3.0.2"
      }
    },
    "@google-cloud/precise-date": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/@google-cloud/precise-date/-/precise-date-1.0.3.tgz",
      "integrity": "sha512-wWnDGh9y3cJHLuVEY8t6un78vizzMWsS7oIWKeFtPj+Ndy+dXvHW0HTx29ZUhen+tswSlQYlwFubvuRP5kKdzQ=="
    },
    "@google-cloud/projectify": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/@google-cloud/projectify/-/projectify-1.0.4.tgz",
      "integrity": "sha512-ZdzQUN02eRsmTKfBj9FDL0KNDIFNjBn/d6tHQmA/+FImH5DO6ZV8E7FzxMgAUiVAUq41RFAkb25p1oHOZ8psfg=="
    },
    "@google-cloud/promisify": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/@google-cloud/promisify/-/promisify-1.0.4.tgz",
      "integrity": "sha512-VccZDcOql77obTnFh0TbNED/6ZbbmHDf8UMNnzO1d5g9V0Htfm4k5cllY8P1tJsRKC3zWYGRLaViiupcgVjBoQ=="
    },
    "@google-cloud/pubsub": {
      "version": "1.6.0",
      "resolved": "https://registry.npmjs.org/@google-cloud/pubsub/-/pubsub-1.6.0.tgz",
      "integrity": "sha512-RL7GJFOQaJpUcNjMDXAQ6dv+cxIIzzDc5DFwbak8KlIvK9znw/YrEybki8e8JTMdvU5Kg7FKGi5RmI6EQkWkVw==",
      "requires": {
        "@google-cloud/paginator": "^2.0.0",
        "@google-cloud/precise-date": "^1.0.0",
        "@google-cloud/projectify": "^1.0.0",
        "@google-cloud/promisify": "^1.0.0",
        "@types/duplexify": "^3.6.0",
        "@types/long": "^4.0.0",
        "arrify": "^2.0.0",
        "async-each": "^1.0.1",
        "extend": "^3.0.2",
        "google-auth-library": "^5.5.0",
        "google-gax": "^1.14.2",
        "is-stream-ended": "^0.1.4",
        "lodash.snakecase": "^4.1.1",
        "p-defer": "^3.0.0",
        "protobufjs": "^6.8.1"
      }
    },
    "@grpc/grpc-js": {
      "version": "0.6.18",
      "resolved": "https://registry.npmjs.org/@grpc/grpc-js/-/grpc-js-0.6.18.tgz",
      "integrity": "sha512-uAzv/tM8qpbf1vpx1xPMfcUMzbfdqJtdCYAqY/LsLeQQlnTb4vApylojr+wlCyr7bZeg3AFfHvtihnNOQQt/nA==",
      "requires": {
        "semver": "^6.2.0"
      }
    },
    "@grpc/proto-loader": {
      "version": "0.5.3",
      "resolved": "https://registry.npmjs.org/@grpc/proto-loader/-/proto-loader-0.5.3.tgz",
      "integrity": "sha512-8qvUtGg77G2ZT2HqdqYoM/OY97gQd/0crSG34xNmZ4ZOsv3aQT/FQV9QfZPazTGna6MIoyUd+u6AxsoZjJ/VMQ==",
      "requires": {
        "lodash.camelcase": "^4.3.0",
        "protobufjs": "^6.8.6"
      }
    },
    "@protobufjs/aspromise": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/aspromise/-/aspromise-1.1.2.tgz",
      "integrity": "sha1-m4sMxmPWaafY9vXQiToU00jzD78="
    },
    "@protobufjs/base64": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/base64/-/base64-1.1.2.tgz",
      "integrity": "sha512-AZkcAA5vnN/v4PDqKyMR5lx7hZttPDgClv83E//FMNhR2TMcLUhfRUBHCmSl0oi9zMgDDqRUJkSxO3wm85+XLg=="
    },
    "@protobufjs/codegen": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/@protobufjs/codegen/-/codegen-2.0.4.tgz",
      "integrity": "sha512-YyFaikqM5sH0ziFZCN3xDC7zeGaB/d0IUb9CATugHWbd1FRFwWwt4ld4OYMPWu5a3Xe01mGAULCdqhMlPl29Jg=="
    },
    "@protobufjs/eventemitter": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/eventemitter/-/eventemitter-1.1.0.tgz",
      "integrity": "sha1-NVy8mLr61ZePntCV85diHx0Ga3A="
    },
    "@protobufjs/fetch": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/fetch/-/fetch-1.1.0.tgz",
      "integrity": "sha1-upn7WYYUr2VwDBYZ/wbUVLDYTEU=",
      "requires": {
        "@protobufjs/aspromise": "^1.1.1",
        "@protobufjs/inquire": "^1.1.0"
      }
    },
    "@protobufjs/float": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/float/-/float-1.0.2.tgz",
      "integrity": "sha1-Xp4avctz/Ap8uLKR33jIy9l7h9E="
    },
    "@protobufjs/inquire": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/inquire/-/inquire-1.1.0.tgz",
      "integrity": "sha1-/yAOPnzyQp4tyvwRQIKOjMY48Ik="
    },
    "@protobufjs/path": {
      "version": "1.1.2",
      "resolved": "https://registry.npmjs.org/@protobufjs/path/-/path-1.1.2.tgz",
      "integrity": "sha1-bMKyDFya1q0NzP0hynZz2Nf79o0="
    },
    "@protobufjs/pool": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/pool/-/pool-1.1.0.tgz",
      "integrity": "sha1-Cf0V8tbTq/qbZbw2ZQbWrXhG/1Q="
    },
    "@protobufjs/utf8": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@protobufjs/utf8/-/utf8-1.1.0.tgz",
      "integrity": "sha1-p3c2C1s5oaLlEG+OhY8v0tBgxXA="
    },
    "@types/duplexify": {
      "version": "3.6.0",
      "resolved": "https://registry.npmjs.org/@types/duplexify/-/duplexify-3.6.0.tgz",
      "integrity": "sha512-5zOA53RUlzN74bvrSGwjudssD9F3a797sDZQkiYpUOxW+WHaXTCPz4/d5Dgi6FKnOqZ2CpaTo0DhgIfsXAOE/A==",
      "requires": {
        "@types/node": "*"
      }
    },
    "@types/fs-extra": {
      "version": "8.1.0",
      "resolved": "https://registry.npmjs.org/@types/fs-extra/-/fs-extra-8.1.0.tgz",
      "integrity": "sha512-UoOfVEzAUpeSPmjm7h1uk5MH6KZma2z2O7a75onTGjnNvAvMVrPzPL/vBbT65iIGHWj6rokwfmYcmxmlSf2uwg==",
      "requires": {
        "@types/node": "*"
      }
    },
    "@types/long": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/@types/long/-/long-4.0.1.tgz",
      "integrity": "sha512-5tXH6Bx/kNGd3MgffdmP4dy2Z+G4eaXw0SE81Tq3BNadtnMR5/ySMzX4SLEzHJzSmPNn4HIdpQsBvXMUykr58w=="
    },
    "@types/node": {
      "version": "12.12.31",
      "resolved": "https://registry.npmjs.org/@types/node/-/node-12.12.31.tgz",
      "integrity": "sha512-T+wnJno8uh27G9c+1T+a1/WYCHzLeDqtsGJkoEdSp2X8RTh3oOCZQcUnjAx90CS8cmmADX51O0FI/tu9s0yssg=="
    },
    "abort-controller": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/abort-controller/-/abort-controller-3.0.0.tgz",
      "integrity": "sha512-h8lQ8tacZYnR3vNQTgibj+tODHI5/+l06Au2Pcriv/Gmet0eaj4TwWH41sO9wnHDiQsEj19q0drzdWdeAHtweg==",
      "requires": {
        "event-target-shim": "^5.0.0"
      }
    },
    "agent-base": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-6.0.0.tgz",
      "integrity": "sha512-j1Q7cSCqN+AwrmDd+pzgqc0/NpC655x2bUf5ZjRIO77DcNBFmh+OgRNzF6OKdCC9RSCb19fGd99+bhXFdkRNqw==",
      "requires": {
        "debug": "4"
      }
    },
    "arrify": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/arrify/-/arrify-2.0.1.tgz",
      "integrity": "sha512-3duEwti880xqi4eAMN8AyR4a0ByT90zoYdLlevfrvU43vb0YZwZVfxOgxWrLXXXpyugL0hNZc9G6BiB5B3nUug=="
    },
    "async-each": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/async-each/-/async-each-1.0.3.tgz",
      "integrity": "sha512-z/WhQ5FPySLdvREByI2vZiTWwCnF0moMJ1hK9YQwDTHKh6I7/uSckMetoRGb5UBZPC1z0jlw+n/XCgjeH7y1AQ=="
    },
    "base64-js": {
      "version": "1.3.1",
      "resolved": "https://registry.npmjs.org/base64-js/-/base64-js-1.3.1.tgz",
      "integrity": "sha512-mLQ4i2QO1ytvGWFWmcngKO//JXAQueZvwEKtjgQFM4jIK0kU+ytMfplL8j+n5mspOfjHwoAg+9yhb7BwAHm36g=="
    },
    "bignumber.js": {
      "version": "7.2.1",
      "resolved": "https://registry.npmjs.org/bignumber.js/-/bignumber.js-7.2.1.tgz",
      "integrity": "sha512-S4XzBk5sMB+Rcb/LNcpzXr57VRTxgAvaAEDAl1AwRx27j00hT84O6OkteE7u8UB3NuaaygCRrEpqox4uDOrbdQ=="
    },
    "buffer-equal-constant-time": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/buffer-equal-constant-time/-/buffer-equal-constant-time-1.0.1.tgz",
      "integrity": "sha1-+OcRMvf/5uAaXJaXpMbz5I1cyBk="
    },
    "core-util-is": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/core-util-is/-/core-util-is-1.0.2.tgz",
      "integrity": "sha1-tf1UIgqivFq1eqtxQMlAdUUDwac="
    },
    "debug": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/debug/-/debug-4.1.1.tgz",
      "integrity": "sha512-pYAIzeRo8J6KPEaJ0VWOh5Pzkbw/RetuzehGM7QRRX5he4fPHx2rdKMB256ehJCkX+XRQm16eZLqLNS8RSZXZw==",
      "requires": {
        "ms": "^2.1.1"
      }
    },
    "duplexify": {
      "version": "3.7.1",
      "resolved": "https://registry.npmjs.org/duplexify/-/duplexify-3.7.1.tgz",
      "integrity": "sha512-07z8uv2wMyS51kKhD1KsdXJg5WQ6t93RneqRxUHnskXVtlYYkLqM0gqStQZ3pj073g687jPCHrqNfCzawLYh5g==",
      "requires": {
        "end-of-stream": "^1.0.0",
        "inherits": "^2.0.1",
        "readable-stream": "^2.0.0",
        "stream-shift": "^1.0.0"
      }
    },
    "ecdsa-sig-formatter": {
      "version": "1.0.11",
      "resolved": "https://registry.npmjs.org/ecdsa-sig-formatter/-/ecdsa-sig-formatter-1.0.11.tgz",
      "integrity": "sha512-nagl3RYrbNv6kQkeJIpt6NJZy8twLB/2vtz6yN9Z4vRKHN4/QZJIEbqohALSgwKdnksuY3k5Addp5lg8sVoVcQ==",
      "requires": {
        "safe-buffer": "^5.0.1"
      }
    },
    "end-of-stream": {
      "version": "1.4.4",
      "resolved": "https://registry.npmjs.org/end-of-stream/-/end-of-stream-1.4.4.tgz",
      "integrity": "sha512-+uw1inIHVPQoaVuHzRyXd21icM+cnt4CzD5rW+NC1wjOUSTOs+Te7FOv7AhN7vS9x/oIyhLP5PR1H+phQAHu5Q==",
      "requires": {
        "once": "^1.4.0"
      }
    },
    "event-target-shim": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/event-target-shim/-/event-target-shim-5.0.1.tgz",
      "integrity": "sha512-i/2XbnSz/uxRCU6+NdVJgKWDTM427+MqYbkQzD321DuCQJUqOuJKIA0IM2+W2xtYHdKOmZ4dR6fExsd4SXL+WQ=="
    },
    "extend": {
      "version": "3.0.2",
      "resolved": "https://registry.npmjs.org/extend/-/extend-3.0.2.tgz",
      "integrity": "sha512-fjquC59cD7CyW6urNXK0FBufkZcoiGG80wTuPujX590cB5Ttln20E2UB4S/WARVqhXffZl2LNgS+gQdPIIim/g=="
    },
    "fast-text-encoding": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/fast-text-encoding/-/fast-text-encoding-1.0.1.tgz",
      "integrity": "sha512-x4FEgaz3zNRtJfLFqJmHWxkMDDvXVtaznj2V9jiP8ACUJrUgist4bP9FmDL2Vew2Y9mEQI/tG4GqabaitYp9CQ=="
    },
    "gaxios": {
      "version": "2.3.4",
      "resolved": "https://registry.npmjs.org/gaxios/-/gaxios-2.3.4.tgz",
      "integrity": "sha512-US8UMj8C5pRnao3Zykc4AAVr+cffoNKRTg9Rsf2GiuZCW69vgJj38VK2PzlPuQU73FZ/nTk9/Av6/JGcE1N9vA==",
      "requires": {
        "abort-controller": "^3.0.0",
        "extend": "^3.0.2",
        "https-proxy-agent": "^5.0.0",
        "is-stream": "^2.0.0",
        "node-fetch": "^2.3.0"
      }
    },
    "gcp-metadata": {
      "version": "3.5.0",
      "resolved": "https://registry.npmjs.org/gcp-metadata/-/gcp-metadata-3.5.0.tgz",
      "integrity": "sha512-ZQf+DLZ5aKcRpLzYUyBS3yo3N0JSa82lNDO8rj3nMSlovLcz2riKFBsYgDzeXcv75oo5eqB2lx+B14UvPoCRnA==",
      "requires": {
        "gaxios": "^2.1.0",
        "json-bigint": "^0.3.0"
      }
    },
    "google-auth-library": {
      "version": "5.10.1",
      "resolved": "https://registry.npmjs.org/google-auth-library/-/google-auth-library-5.10.1.tgz",
      "integrity": "sha512-rOlaok5vlpV9rSiUu5EpR0vVpc+PhN62oF4RyX/6++DG1VsaulAFEMlDYBLjJDDPI6OcNOCGAKy9UVB/3NIDXg==",
      "requires": {
        "arrify": "^2.0.0",
        "base64-js": "^1.3.0",
        "ecdsa-sig-formatter": "^1.0.11",
        "fast-text-encoding": "^1.0.0",
        "gaxios": "^2.1.0",
        "gcp-metadata": "^3.4.0",
        "gtoken": "^4.1.0",
        "jws": "^4.0.0",
        "lru-cache": "^5.0.0"
      }
    },
    "google-gax": {
      "version": "1.15.1",
      "resolved": "https://registry.npmjs.org/google-gax/-/google-gax-1.15.1.tgz",
      "integrity": "sha512-1T1PwSZWnbdRusA+NCZMSe56iU6swGvuZuy54eYl9vEHiRXTLYbQmUkWY2CqgYD9Fd/T4WBkUl22+rZG80unyw==",
      "requires": {
        "@grpc/grpc-js": "^0.6.18",
        "@grpc/proto-loader": "^0.5.1",
        "@types/fs-extra": "^8.0.1",
        "@types/long": "^4.0.0",
        "abort-controller": "^3.0.0",
        "duplexify": "^3.6.0",
        "google-auth-library": "^5.0.0",
        "is-stream-ended": "^0.1.4",
        "lodash.at": "^4.6.0",
        "lodash.has": "^4.5.2",
        "node-fetch": "^2.6.0",
        "protobufjs": "^6.8.9",
        "retry-request": "^4.0.0",
        "semver": "^6.0.0",
        "walkdir": "^0.4.0"
      }
    },
    "google-p12-pem": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/google-p12-pem/-/google-p12-pem-2.0.4.tgz",
      "integrity": "sha512-S4blHBQWZRnEW44OcR7TL9WR+QCqByRvhNDZ/uuQfpxywfupikf/miba8js1jZi6ZOGv5slgSuoshCWh6EMDzg==",
      "requires": {
        "node-forge": "^0.9.0"
      }
    },
    "gtoken": {
      "version": "4.1.4",
      "resolved": "https://registry.npmjs.org/gtoken/-/gtoken-4.1.4.tgz",
      "integrity": "sha512-VxirzD0SWoFUo5p8RDP8Jt2AGyOmyYcT/pOUgDKJCK+iSw0TMqwrVfY37RXTNmoKwrzmDHSk0GMT9FsgVmnVSA==",
      "requires": {
        "gaxios": "^2.1.0",
        "google-p12-pem": "^2.0.0",
        "jws": "^4.0.0",
        "mime": "^2.2.0"
      }
    },
    "https-proxy-agent": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/https-proxy-agent/-/https-proxy-agent-5.0.0.tgz",
      "integrity": "sha512-EkYm5BcKUGiduxzSt3Eppko+PiNWNEpa4ySk9vTC6wDsQJW9rHSa+UhGNJoRYp7bz6Ht1eaRIa6QaJqO5rCFbA==",
      "requires": {
        "agent-base": "6",
        "debug": "4"
      }
    },
    "inherits": {
      "version": "2.0.4",
      "resolved": "https://registry.npmjs.org/inherits/-/inherits-2.0.4.tgz",
      "integrity": "sha512-k/vGaX4/Yla3WzyMCvTQOXYeIHvqOKtnqBduzTHpzpQZzAskKMhZ2K+EnBiSM9zGSoIFeMpXKxa4dYeZIQqewQ=="
    },
    "is-stream": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/is-stream/-/is-stream-2.0.0.tgz",
      "integrity": "sha512-XCoy+WlUr7d1+Z8GgSuXmpuUFC9fOhRXglJMx+dwLKTkL44Cjd4W1Z5P+BQZpr+cR93aGP4S/s7Ftw6Nd/kiEw=="
    },
    "is-stream-ended": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/is-stream-ended/-/is-stream-ended-0.1.4.tgz",
      "integrity": "sha512-xj0XPvmr7bQFTvirqnFr50o0hQIh6ZItDqloxt5aJrR4NQsYeSsyFQERYGCAzfindAcnKjINnwEEgLx4IqVzQw=="
    },
    "isarray": {
      "version": "1.0.0",
      "resolved": "https://registry.npmjs.org/isarray/-/isarray-1.0.0.tgz",
      "integrity": "sha1-u5NdSFgsuhaMBoNJV6VKPgcSTxE="
    },
    "json-bigint": {
      "version": "0.3.0",
      "resolved": "https://registry.npmjs.org/json-bigint/-/json-bigint-0.3.0.tgz",
      "integrity": "sha1-DM2RLEuCcNBfBW+9E4FLU9OCWx4=",
      "requires": {
        "bignumber.js": "^7.0.0"
      }
    },
    "jwa": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/jwa/-/jwa-2.0.0.tgz",
      "integrity": "sha512-jrZ2Qx916EA+fq9cEAeCROWPTfCwi1IVHqT2tapuqLEVVDKFDENFw1oL+MwrTvH6msKxsd1YTDVw6uKEcsrLEA==",
      "requires": {
        "buffer-equal-constant-time": "1.0.1",
        "ecdsa-sig-formatter": "1.0.11",
        "safe-buffer": "^5.0.1"
      }
    },
    "jws": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/jws/-/jws-4.0.0.tgz",
      "integrity": "sha512-KDncfTmOZoOMTFG4mBlG0qUIOlc03fmzH+ru6RgYVZhPkyiy/92Owlt/8UEN+a4TXR1FQetfIpJE8ApdvdVxTg==",
      "requires": {
        "jwa": "^2.0.0",
        "safe-buffer": "^5.0.1"
      }
    },
    "lodash.at": {
      "version": "4.6.0",
      "resolved": "https://registry.npmjs.org/lodash.at/-/lodash.at-4.6.0.tgz",
      "integrity": "sha1-k83OZk8KGZTqM9181A4jr9EbD/g="
    },
    "lodash.camelcase": {
      "version": "4.3.0",
      "resolved": "https://registry.npmjs.org/lodash.camelcase/-/lodash.camelcase-4.3.0.tgz",
      "integrity": "sha1-soqmKIorn8ZRA1x3EfZathkDMaY="
    },
    "lodash.has": {
      "version": "4.5.2",
      "resolved": "https://registry.npmjs.org/lodash.has/-/lodash.has-4.5.2.tgz",
      "integrity": "sha1-0Z9NwQlQWMzL4rDN9O4P5Ko3yGI="
    },
    "lodash.snakecase": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/lodash.snakecase/-/lodash.snakecase-4.1.1.tgz",
      "integrity": "sha1-OdcUo1NXFHg3rv1ktdy7Fr7Nj40="
    },
    "long": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/long/-/long-4.0.0.tgz",
      "integrity": "sha512-XsP+KhQif4bjX1kbuSiySJFNAehNxgLb6hPRGJ9QsUr8ajHkuXGdrHmFUTUUXhDwVX2R5bY4JNZEwbUiMhV+MA=="
    },
    "lru-cache": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-5.1.1.tgz",
      "integrity": "sha512-KpNARQA3Iwv+jTA0utUVVbrh+Jlrr1Fv0e56GGzAFOXN7dk/FviaDW8LHmK52DlcH4WP2n6gI8vN1aesBFgo9w==",
      "requires": {
        "yallist": "^3.0.2"
      }
    },
    "mime": {
      "version": "2.4.4",
      "resolved": "https://registry.npmjs.org/mime/-/mime-2.4.4.tgz",
      "integrity": "sha512-LRxmNwziLPT828z+4YkNzloCFC2YM4wrB99k+AV5ZbEyfGNWfG8SO1FUXLmLDBSo89NrJZ4DIWeLjy1CHGhMGA=="
    },
    "ms": {
      "version": "2.1.2",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.2.tgz",
      "integrity": "sha512-sGkPx+VjMtmA6MX27oA4FBFELFCZZ4S4XqeGOXCv68tT+jb3vk/RyaKWP0PTKyWtmLSM0b+adUTEvbs1PEaH2w=="
    },
    "node-fetch": {
      "version": "2.6.0",
      "resolved": "https://registry.npmjs.org/node-fetch/-/node-fetch-2.6.0.tgz",
      "integrity": "sha512-8dG4H5ujfvFiqDmVu9fQ5bOHUC15JMjMY/Zumv26oOvvVJjM67KF8koCWIabKQ1GJIa9r2mMZscBq/TbdOcmNA=="
    },
    "node-forge": {
      "version": "0.9.1",
      "resolved": "https://registry.npmjs.org/node-forge/-/node-forge-0.9.1.tgz",
      "integrity": "sha512-G6RlQt5Sb4GMBzXvhfkeFmbqR6MzhtnT7VTHuLadjkii3rdYHNdw0m8zA4BTxVIh68FicCQ2NSUANpsqkr9jvQ=="
    },
    "once": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/once/-/once-1.4.0.tgz",
      "integrity": "sha1-WDsap3WWHUsROsF9nFC6753Xa9E=",
      "requires": {
        "wrappy": "1"
      }
    },
    "p-defer": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/p-defer/-/p-defer-3.0.0.tgz",
      "integrity": "sha512-ugZxsxmtTln604yeYd29EGrNhazN2lywetzpKhfmQjW/VJmhpDmWbiX+h0zL8V91R0UXkhb3KtPmyq9PZw3aYw=="
    },
    "process-nextick-args": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/process-nextick-args/-/process-nextick-args-2.0.1.tgz",
      "integrity": "sha512-3ouUOpQhtgrbOa17J7+uxOTpITYWaGP7/AhoR3+A+/1e9skrzelGi/dXzEYyvbxubEF6Wn2ypscTKiKJFFn1ag=="
    },
    "protobufjs": {
      "version": "6.8.9",
      "resolved": "https://registry.npmjs.org/protobufjs/-/protobufjs-6.8.9.tgz",
      "integrity": "sha512-j2JlRdUeL/f4Z6x4aU4gj9I2LECglC+5qR2TrWb193Tla1qfdaNQTZ8I27Pt7K0Ajmvjjpft7O3KWTGciz4gpw==",
      "requires": {
        "@protobufjs/aspromise": "^1.1.2",
        "@protobufjs/base64": "^1.1.2",
        "@protobufjs/codegen": "^2.0.4",
        "@protobufjs/eventemitter": "^1.1.0",
        "@protobufjs/fetch": "^1.1.0",
        "@protobufjs/float": "^1.0.2",
        "@protobufjs/inquire": "^1.1.0",
        "@protobufjs/path": "^1.1.2",
        "@protobufjs/pool": "^1.1.0",
        "@protobufjs/utf8": "^1.1.0",
        "@types/long": "^4.0.0",
        "@types/node": "^10.1.0",
        "long": "^4.0.0"
      },
      "dependencies": {
        "@types/node": {
          "version": "10.17.17",
          "resolved": "https://registry.npmjs.org/@types/node/-/node-10.17.17.tgz",
          "integrity": "sha512-gpNnRnZP3VWzzj5k3qrpRC6Rk3H/uclhAVo1aIvwzK5p5cOrs9yEyQ8H/HBsBY0u5rrWxXEiVPQ0dEB6pkjE8Q=="
        }
      }
    },
    "readable-stream": {
      "version": "2.3.7",
      "resolved": "https://registry.npmjs.org/readable-stream/-/readable-stream-2.3.7.tgz",
      "integrity": "sha512-Ebho8K4jIbHAxnuxi7o42OrZgF/ZTNcsZj6nRKyUmkhLFq8CHItp/fy6hQZuZmP/n3yZ9VBUbp4zz/mX8hmYPw==",
      "requires": {
        "core-util-is": "~1.0.0",
        "inherits": "~2.0.3",
        "isarray": "~1.0.0",
        "process-nextick-args": "~2.0.0",
        "safe-buffer": "~5.1.1",
        "string_decoder": "~1.1.1",
        "util-deprecate": "~1.0.1"
      },
      "dependencies": {
        "safe-buffer": {
          "version": "5.1.2",
          "resolved": "https://registry.npmjs.org/safe-buffer/-/safe-buffer-5.1.2.tgz",
          "integrity": "sha512-Gd2UZBJDkXlY7GbJxfsE8/nvKkUEU1G38c1siN6QP6a9PT9MmHB8GnpscSmMJSoF8LOIrt8ud/wPtojys4G6+g=="
        }
      }
    },
    "retry-request": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/retry-request/-/retry-request-4.1.1.tgz",
      "integrity": "sha512-BINDzVtLI2BDukjWmjAIRZ0oglnCAkpP2vQjM3jdLhmT62h0xnQgciPwBRDAvHqpkPT2Wo1XuUyLyn6nbGrZQQ==",
      "requires": {
        "debug": "^4.1.1",
        "through2": "^3.0.1"
      }
    },
    "safe-buffer": {
      "version": "5.2.0",
      "resolved": "https://registry.npmjs.org/safe-buffer/-/safe-buffer-5.2.0.tgz",
      "integrity": "sha512-fZEwUGbVl7kouZs1jCdMLdt95hdIv0ZeHg6L7qPeciMZhZ+/gdesW4wgTARkrFWEpspjEATAzUGPG8N2jJiwbg=="
    },
    "semver": {
      "version": "6.3.0",
      "resolved": "https://registry.npmjs.org/semver/-/semver-6.3.0.tgz",
      "integrity": "sha512-b39TBaTSfV6yBrapU89p5fKekE2m/NwnDocOVruQFS1/veMgdzuPcnOM34M6CwxW8jH/lxEa5rBoDeUwu5HHTw=="
    },
    "stream-shift": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/stream-shift/-/stream-shift-1.0.1.tgz",
      "integrity": "sha512-AiisoFqQ0vbGcZgQPY1cdP2I76glaVA/RauYR4G4thNFgkTqr90yXTo4LYX60Jl+sIlPNHHdGSwo01AvbKUSVQ=="
    },
    "string_decoder": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/string_decoder/-/string_decoder-1.1.1.tgz",
      "integrity": "sha512-n/ShnvDi6FHbbVfviro+WojiFzv+s8MPMHBczVePfUpDJLwoLT0ht1l4YwBCbi8pJAveEEdnkHyPyTP/mzRfwg==",
      "requires": {
        "safe-buffer": "~5.1.0"
      },
      "dependencies": {
        "safe-buffer": {
          "version": "5.1.2",
          "resolved": "https://registry.npmjs.org/safe-buffer/-/safe-buffer-5.1.2.tgz",
          "integrity": "sha512-Gd2UZBJDkXlY7GbJxfsE8/nvKkUEU1G38c1siN6QP6a9PT9MmHB8GnpscSmMJSoF8LOIrt8ud/wPtojys4G6+g=="
        }
      }
    },
    "through2": {
      "version": "3.0.1",
      "resolved": "https://registry.npmjs.org/through2/-/through2-3.0.1.tgz",
      "integrity": "sha512-M96dvTalPT3YbYLaKaCuwu+j06D/8Jfib0o/PxbVt6Amhv3dUAtW6rTV1jPgJSBG83I/e04Y6xkVdVhSRhi0ww==",
      "requires": {
        "readable-stream": "2 || 3"
      }
    },
    "util-deprecate": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/util-deprecate/-/util-deprecate-1.0.2.tgz",
      "integrity": "sha1-RQ1Nyfpw3nMnYvvS1KKJgUGaDM8="
    },
    "walkdir": {
      "version": "0.4.1",
      "resolved": "https://registry.npmjs.org/walkdir/-/walkdir-0.4.1.tgz",
      "integrity": "sha512-3eBwRyEln6E1MSzcxcVpQIhRG8Q1jLvEqRmCZqS3dsfXEDR/AhOF4d+jHg1qvDCpYaVRZjENPQyrVxAkQqxPgQ=="
    },
    "wrappy": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/wrappy/-/wrappy-1.0.2.tgz",
      "integrity": "sha1-tSQ9jz7BqjXxNkYFvA0QNuMKtp8="
    },
    "yallist": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/yallist/-/yallist-3.1.1.tgz",
      "integrity": "sha512-a4UGQaWPH59mOXUYnAG2ewncQS4i4F43Tv3JoAM+s2VDAmS9NsK8GpDMLrCHPksFT7h3K6TOoUNn2pb7RoXx4g=="
    }
  }
}
                                                                                                                         insta-puller/README.MD                                                                              0000644 0001750 0001750 00000007572 13670726436 016261  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            # Insta-puller

A Serverless (compute) approach to scraping Instagram feeds. This project is being used to experiment with various products across the CBR Teams (Code, Build Run)

_Note that storing data in Cloud SQL isn't a truly serverless data solution_

## Setup Instructions (for working in Cloud Shell)

1. Clone (inside Cloud Shell)
   > `gcloud source repos clone insta-puller --project=serverless-ux-playground`
2. move into the new directory
   > `cd insta-puller`
3. Create and enable virtual environment
   > `python3 -m venv .env; source .env/bin/activate`
4. Install python requirements
   > `pip3 install -r requirements.txt`

## Setup Cloud SQL Proxy (do this in a separate terminal)

1. Download Cloud Sql Proxy
   > `wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy`
2. Make it executable
   > `chmod +x cloud_sql_proxy`
3. Create a root cloudsql dir
   > `sudo mkdir /cloudsql`
4. Start the Cloud SQL Proxy
   > `sudo ./cloud_sql_proxy -dir=/cloudsql -instances=serverless-ux-playground:us-west1:instadatabase`

## Run the Python app locally (different terminal from the SQL Proxy)

1. Setup the Env variables that let us connect to our Cloud SQL DB
   > `export DB_USER='root'; export DB_PASS='ab440c97193768e9b845abd25e57066e' ; export DB_NAME='insta' ; export CLOUD_SQL_CONNECTION_NAME='serverless-ux-playground:us-west1:instadatabase'`
2. Make sure you're in the insta-puller directory
   > `cd repos/insta-puller/`
3. Enable the virtual environment
   > `source .env/bin/activate`
4. Run the app
   > `python app.py`

## Building for deployment

### Docker Build

> `docker build . --tag instapull`

### Docker Run (Cloud Run style)

> `PORT=8080 && docker run -p 9090:${PORT} -e PORT=${PORT} instapull`

### gcloud build

> `gcloud builds submit --tag gcr.io/serverless-ux-playground/instapull`

### gcloud deploy

> `gcloud run deploy --image gcr.io/serverless-ux-playground/instapull`

The deployed CR service will need all of the Environment Variables and the Cloud SQL Connection created

## Git commands after making changes

### Running mysqlclient to verify SQL Proxy

> `mysql -u root -p -S /cloudsql/serverless-ux-playground:us-west1:instadatabase`

shh....
ab440c97193768e9b845abd25e57066e

## Devops things to add

1. Multiple environments (Dev, Staging, Production)
1. Automatic deployment of Cloud Functions on commit

## Devops things added

1. Continuous Integration (CloudRun App)
1. Continuous Deployment (CloudRun App)

## Features to add

1. Download and store the associated media from posts.
1. Build an API to query for stored information (perhaps using the API Gateway)
   1. What usernames are being tracked?
   1. How many posts are stored?
   1. Return the data for a username (with time searches)
1. Maybe some unit-tests for code

## Features added

1. Automated recurring pulls for usernames in the database (Cloud Scheduler calls a Cloud Function)

## Bugs to fix

1. Download function errors sometimes, and sometimes creates a 20b file for some reason
   1. This is an example error file in storage gs://instapuller/70199965_547444809328714_8209873839849946748_n.jpg

## Bugs fixed

1. Doesn't parse JSON correctly on certain accounts (joshbloom)
1. Some usernames aren't processed correctly e.g. <https://instapuller.serverlessux.design/?username=mark__roudebush>
   1. Turned out to be missing captions on the post causing a crash

## Cloud Functions

1. There are 2 cloud functions
   1. "Instapuller-nightly-updater" every 2 hours Hits the usernames endpoint and the requests a new pull for each username. Triggered by Cloud Scheduler
   1. "instapuller-media-download" pub/sub triggered cloud function on each successful DB insert for a new post. Stores the associated media in a Cloud Storage bucket.

### Cloud Functions testing

## Random notes

Direct post page <https://www.instagram.com/p/B82Cy69nDaQ/>
Example User page <https://www.instagram.com/danaherjohn>
                                                                                                                                      insta-puller/requirements.txt                                                                       0000644 0001750 0001750 00000001255 13670726436 020356  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            astroid==2.3.3
autopep8==1.5
beautifulsoup4==4.8.2
cachetools==4.0.0
certifi==2019.11.28
chardet==3.0.4
Click==7.0
Flask==1.1.1
google-api-core==1.16.0
google-auth==1.12.0
google-cloud-pubsub==1.4.2
google-python-cloud-debugger
googleapis-common-protos==1.51.0
grpc-google-iam-v1==0.12.3
grpcio==1.27.2
idna==2.9
isort==4.3.21
itsdangerous==1.1.0
Jinja2==2.11.1
json2html==1.3.0
lazy-object-proxy==1.4.3
MarkupSafe==1.1.1
mccabe==0.6.1
protobuf==3.11.3
pyasn1==0.4.8
pyasn1-modules==0.2.8
pycodestyle==2.5.0
pylint==2.4.4
PyMySQL==0.9.3
pytz==2019.3
requests==2.23.0
rsa==4.0
six==1.14.0
soupsieve==2.0
SQLAlchemy==1.3.13
typed-ast==1.4.1
urllib3==1.25.8
Werkzeug==1.0.0
wrapt==1.11.2
                                                                                                                                                                                                                                                                                                                                                   insta-puller/scripts/                                                                               0000755 0001750 0001750 00000000000 13670726436 016556  5                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            insta-puller/scripts/convertJsonToB64.py                                                            0000644 0001750 0001750 00000003613 13670726436 022224  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            import base64
# -*- coding: utf-32 -*-

st = "🖤"

# str = '''{
#   "username": "mark__roudebush",
#   "post_id": "B2sfv8igp_H",
#   "shortcode": "B-NdHJvH6jx",
#   "direct_link": "https://www.instagram.com/p/B2sfv8igp_H",
#   "caption": "🖤Who could be so lucky? #contaxg2 #portra400",
#   "display_url": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/e35/70199965_547444809328714_8209873839849946748_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=pE8Qx0LYCBUAX8h2f-I&oh=8a47ed6be54e172f5e9079fb5a2ad121&oe=5EB90626",
#   "thumbnail_src": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/sh0.08/e35/c90.0.899.899a/s640x640/70199965_547444809328714_8209873839849946748_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=pE8Qx0LYCBUAX8h2f-I&oh=920daea13a66cfb5293d58305a814c8b&oe=5EB9A089"
# }'''

print(base64.b64encode(st.encode()))

# OUTPUT

# ewogICJ1c2VybmFtZSI6ICJtYXJrX19yb3VkZWJ1c2giLAogICJwb3N0X2lkIjogIkIyc2Z2OGlncF9IIiwKICAic2hvcnRjb2RlIjogIkItTmRISnZINmp4IiwKICAiZGlyZWN0X2xpbmsiOiAiaHR0cHM6Ly93d3cuaW5zdGFncmFtLmNvbS9wL0Iyc2Z2OGlncF9IIiwKICAiY2FwdGlvbiI6ICLwn5akXG5XaG8gY291bGQgYmUgc28gbHVja3k/XG4jY29udGF4ZzIgI3BvcnRyYTQwMCIsCiAgImRpc3BsYXlfdXJsIjogImh0dHBzOi8vc2NvbnRlbnQtc2pjMy0xLmNkbmluc3RhZ3JhbS5jb20vdi90NTEuMjg4NS0xNS9lMzUvNzAxOTk5NjVfNTQ3NDQ0ODA5MzI4NzE0XzgyMDk4NzM4Mzk4NDk5NDY3NDhfbi5qcGc/X25jX2h0PXNjb250ZW50LXNqYzMtMS5jZG5pbnN0YWdyYW0uY29tJl9uY19jYXQ9MTEwJl9uY19vaGM9cEU4UXgwTFlDQlVBWDhoMmYtSSZvaD04YTQ3ZWQ2YmU1NGUxNzJmNWU5MDc5ZmI1YTJhZDEyMSZvZT01RUI5MDYyNiIsCiAgInRodW1ibmFpbF9zcmMiOiAiaHR0cHM6Ly9zY29udGVudC1zamMzLTEuY2RuaW5zdGFncmFtLmNvbS92L3Q1MS4yODg1LTE1L3NoMC4wOC9lMzUvYzkwLjAuODk5Ljg5OWEvczY0MHg2NDAvNzAxOTk5NjVfNTQ3NDQ0ODA5MzI4NzE0XzgyMDk4NzM4Mzk4NDk5NDY3NDhfbi5qcGc/X25jX2h0PXNjb250ZW50LXNqYzMtMS5jZG5pbnN0YWdyYW0uY29tJl9uY19jYXQ9MTEwJl9uY19vaGM9cEU4UXgwTFlDQlVBWDhoMmYtSSZvaD05MjBkYWVhMTNhNjZjZmI1MjkzZDU4MzA1YTgxNGM4YiZvZT01RUI5QTA4OSIKfQo =
                                                                                                                     insta-puller/scripts/send_build_message.py                                                          0000644 0001750 0001750 00000001326 13670726436 022746  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            from httplib2 import Http
from json import dumps


#
# Hangouts Chat incoming webhook quickstart
#
def main():
    url = 'https://chat.googleapis.com/v1/spaces/AAAAn4yZytI/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=u4jlIHJF6XXsAE0ej3pW1NsajKQdT13YkaxgNSKiKBU%3D'
    bot_message = {
        'text': '<https://instapuller.serverlessux.design/stats|Insta-puller> has just built and released successfully.'}

    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),
    )

    print(response)


if __name__ == '__main__':
    main()
                                                                                                                                                                                                                                                                                                          insta-puller/source-context.json                                                                    0000644 0001750 0001750 00000000341 13670726436 020742  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            {
  "cloudRepo": {
    "repoId": {
      "projectRepoId": {
        "projectId": "serverless-ux-playground",
        "repoName": "insta-puller"
      }
    },
    "revisionId": "8b97a115d17e7d9087c03d9428e19bc56fd2017f"
  }
}                                                                                                                                                                                                                                                                                               insta-puller/sql_queries.sql                                                                        0000644 0001750 0001750 00000000550 13670726436 020144  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            select count(*) from posts;
select count(distinct username) from posts;
select distinct username from posts;
select count(*) from posts;

select username, count(username) from posts 
	group by username 
    order by count(username) desc;

select username from posts 
	group by username
    order by username;
    
select * from posts
	order by date_added desc;                                                                                                                                                        insta-puller/templates/                                                                             0000755 0001750 0001750 00000000000 13670726436 017065  5                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            insta-puller/templates/index.html                                                                   0000644 0001750 0001750 00000003642 13670726436 021067  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            <!doctype html>
<html lang="en">

<head>
	<!-- Required meta tags -->
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

	<!-- Bootstrap CSS -->
	<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"
		integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">

	<title>Index</title>
	<style>
		body {
			background-color: #e6e6e6;
		}

		.tableHolder {
			margin: 35px;
			background-color: white;
		}

		td img {
			height: 100px;
		}

	</style>
</head>

<body>
	<div class=tableHolder>
		<table class="table table-striped">
			<thead>
				<tr>
					<th scope="col">Username</th>
					<th scope="col">Caption</th>
					<th scope="col">Link</th>
					<th scope="col">Thumbnail</th>
				</tr>
			</thead>
			<tbody>
				{% for item in data %}
				<tr>
					<td scope="row">{{item.username}}</td>
					<td>{{item.caption | truncate(400)}}</td>
					<td><a href="{{item.direct_link}}">Insta Link</a>
					</td>
					<td>
						<a href="{{item.thumbnail_src}}">
							<img src="{{item.thumbnail_src}}" alt="">
						</a>
					</td>
				</tr>
				{% endfor %}
			</tbody>
		</table>
	</div>
	<!-- Optional JavaScript -->
	<!-- jQuery first, then Popper.js, then Bootstrap JS -->
	<script src="https://code.jquery.com/jquery-3.4.1.slim.min.js"
		integrity="sha384-J6qa4849blE2+poT4WnyKhv5vZF5SrPo0iEjwBvKU7imGFAV0wwj1yYfoRSJoZ+n" crossorigin="anonymous">
	</script>
	<script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js"
		integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo" crossorigin="anonymous">
	</script>
	<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js"
		integrity="sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6" crossorigin="anonymous">
	</script>
</body>

</html>
                                                                                              insta-puller/templates/stats.html                                                                   0000644 0001750 0001750 00000003065 13670726436 021115  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            <!doctype html>
<html lang="en">

<head>
	<!-- Required meta tags -->
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

	<!-- Bootstrap CSS -->
	<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"
		integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">
	<title>Stats!</title>
	<style>
		.tableHolder {
			margin: 0 auto;
			width: 350px;
		}

	</style>
</head>

<body>
	<div class=tableHolder>
		<table class="table table-striped">
			<thead>
				<tr>
					<th scope="col">Username</th>
					<th scope="col">Post Count</th>
				</tr>
			</thead>
			<tbody>
				{% for item in rows %}
				<tr>
					<td scope="row">{{item[0]}}</td>
					<td>{{item[1]}}</td>
				</tr>
				{% endfor %}
			</tbody>
		</table>
	</div>
	<!-- Optional JavaScript -->
	<!-- jQuery first, then Popper.js, then Bootstrap JS -->
	<script src="https://code.jquery.com/jquery-3.4.1.slim.min.js"
		integrity="sha384-J6qa4849blE2+poT4WnyKhv5vZF5SrPo0iEjwBvKU7imGFAV0wwj1yYfoRSJoZ+n" crossorigin="anonymous">
	</script>
	<script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js"
		integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo" crossorigin="anonymous">
	</script>
	<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js"
		integrity="sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6" crossorigin="anonymous">
	</script>
</body>

</html>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                           insta-puller/tests/                                                                                 0000755 0001750 0001750 00000000000 13670726436 016231  5                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            insta-puller/tests/main.py                                                                          0000644 0001750 0001750 00000003773 13670726436 017541  0                                                                                                    ustar   davidstanke                     davidstanke                                                                                                                                                                                                            import os
from bs4 import BeautifulSoup
import requests
import json
import unittest


def processPosts(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    scripts = soup.find_all('script')

    try:
        data = scripts[4].getText()[21:-1]  # Clean out pre-amble
        postList = json.loads(data)[
            "entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]
    except:
        data = scripts[3].getText()[21:-1]  # Clean out pre-amble
        postList = json.loads(data)[
            "entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]

    collection = getPosts(postList)
    # print(json.dumps(collection, indent=2))
    return json.dumps(collection, indent=2)


def getPosts(postList):
    postCollection = []
    for post in postList:
        item = {}
        item["id"] = post["node"]["id"]
        item["shortcode"] = post["node"]["shortcode"]
        item["direct_link"] = "https://www.instagram.com/p" + \
            post["node"]["shortcode"]
        item["caption"] = post["node"]["edge_media_to_caption"]["edges"][0]["node"]["text"]
        item["display_url"] = post["node"]["display_url"]
        item["thumbnail_src"] = post["node"]["thumbnail_src"]
        item["thumbnail_resources"] = post["node"]["thumbnail_resources"]
        postCollection.append(item)
    return postCollection


url_one = 'https://www.instagram.com/joshbloom/'
url_two = 'https://www.instagram.com/danaherjohn/'
url_three = 'https://www.instagram.com/explore/tags/ribeirojiujitsu/'


class TestSum(unittest.TestCase):

    def test_sum(self):
        self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")

    def testInstaParserOne(self):
        self.assertTrue(processPosts(url_one))

    def testInstaParserTwo(self):
        self.assertTrue(processPosts(url_two))

    def testBadParse(self):
        with self.assertRaises(KeyError):
            processPosts(url_three)


if __name__ == '__main__':
    unittest.main()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     