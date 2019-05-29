import argparse
import json
import logging
import pickle
import os.path
import sys
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest
from googleapiclient.http import build_http
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload 
from apiclient.http import MediaFileUpload

import json
import requests

SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.readonly']#'https://www.googleapis.com/auth/drive']#'https://www.googleapis.com/auth/drive.file']
CREDS_FILE = './credentials.json'
PARENT_FOLDER_ID = '1-3UeRNYRVGrdwItZpUmb22LZvYafA4uE'#'13rQ1YRz012Ns_7Fh3RgDWdBwPK9YcfXW' # Root google drive folder 
logging.basicConfig(level=logging.ERROR)


def google_drive_oath():
    """
    Signs into google drive and saves an OAUTH token locally.
    Requires google drive generated CREDS_FILE as input.
    @Note: see https://developers.google.com/drive/api/v3/quickstart/python
           see "ENABLE THE DRIVE API"
    @Return: a google drive api service object
    """
    service = None
    try:
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                print("Reusing local token.")
                logging.info("Reusing local token.")
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDS_FILE, SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
                logging.info("Token successfully saved locally")
        #print("#### creds ####")
        #print(creds.token)
        service = build('drive', 'v3', credentials=creds)
        logging.info("Google drive api serice connected.")
    except Exception as e:
        logging.exception("Error, could not create google drive api service")
    
    return service

def list_folder(google_folder_id):
    response = drive_service.files().list(
            pageSize=1000,
            q="'{}' in parents and trashed=false".format(google_folder_id),
            fields="nextPageToken, files(id, name, mimeType)").execute()
    results = response.get('files',[])

    return results

def update_metadata(google_file_id, local_metadata_filename):
    # Read the metadata
    with open(local_metadata_filename) as metadata_file:
        local_mdata_json = json.load(metadata_file)

    # apply the metadata
    update_metadata = {'description':str(local_mdata_json)}
    #print(metadata)
    updated_file = drive_service.files().update(
        fileId=google_file_id, 
        body=update_metadata).execute()
    if updated_file:
        print("applied metadata to {}".format(updated_file['name']))
        applied_mdata = True
    else:
        print("metadata update failed!")

def walk_folders(google_folder_id, local_dir, base_dir=''):
    
    parent_folder = drive_service.files().get(
        fileId=google_folder_id, 
        fields='name').execute()
    base_dir = base_dir + parent_folder['name'] + '/'
    print("Current base directory {}".format(base_dir))

    # list current google drive folder
    current_files = list_folder(google_folder_id)

    # find corresponding metadata side car for each file / object, but not folders
    #     and apply metadata to corresponding google file
    metadata_dir = base_dir + '.metadata/'
    for curr_file in current_files:
        if (curr_file['mimeType'] != 'application/vnd.google-apps.folder'):
            local_metadata_file = local_dir + metadata_dir + curr_file['name'] + '.json'
            if os.path.exists(local_metadata_file):
                update_metadata(curr_file['id'], local_metadata_file)
                print("Found {}".format(local_metadata_file))
            else:
                print("Error, no corresponding metadata file for {}".format(curr_file['name']))
  
    # if any folders, go into them recursively and repeat above
    for curr_file in current_files:
        if (curr_file['mimeType'] == 'application/vnd.google-apps.folder') and \
                                         (curr_file['name'] != '.metadata'):
            print('Going into {}'.format(curr_file['name']))
            walk_folders(curr_file['id'], local_dir, base_dir)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-dir", required=True, help="folder containing .metadata folders")
    args = parser.parse_args()
    metadata_folder = args.metadata_dir

    drive_service = google_drive_oath()
    if drive_service:
        walk_folders(PARENT_FOLDER_ID, metadata_folder)    
        # udate file metadata
    else:
        logging.info("Exiting, no google drive service available.")



    #main()