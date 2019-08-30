* Downloading data and metadata from plone

1) set the src_base_url and src_folders in get_plone_media_listing.py

2) run the dowload script

python get_plone_media_listing.py --src-user SRC_USER --src-pwd SRC_PWD
                                  --dest-dir DEST_DIR --metadata-output-file  METADATA_OUTPUT_FILE

SRC_USER and SRC_PWD are the plone login credentials 
(@note must have permissions to see the src_folders)

DEST_DIR is where all the downloads will be downloaded to.

METADATA_OUTPUT_FILE is where all the files plone metadata will be saved in json format for step 4 below.

* Uploading downloaded data to Google Drive

Upload data to Google drive using Drive File Stream:
https://dl.google.com/drive-file-stream/GoogleDriveFSSetup.exe

* Updating file metadata of google drive uploads

1) Obtain Google drive api token for upload drive permission access:
See: https://developers.google.com/drive/api/v3/quickstart/python

Place credentials.json in scripts folder.

2) set the PARENT_FOLDER_ID in google_drive_update_metadata.py
(obtain this from google drive folder url: https://drive.google.com/drive/folders/<PARENT_FOLDER_ID>
by browsing to folder of interest in Google Drive web app)

3) set new_key_name and associated lines below (depends on old and new data path locations)

4) run the metadata update script
python google_drive_update_metadata.py --all-metadata-file <metadata_file.json>
<metadata_file.json> is produced as output in step 2 above.


