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
import time

import json
import requests

SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.readonly']#'https://www.googleapis.com/auth/drive']#'https://www.googleapis.com/auth/drive.file']
CREDS_FILE = './credentials.json'
PARENT_FOLDER_ID = '1KSqkVM-3gZD7w7l1wQEY07T6q79kJhWp'#'13rQ1YRz012Ns_7Fh3RgDWdBwPK9YcfXW' # Root google drive folder 
logging.basicConfig(level=logging.ERROR)

UPDATE_METRICS = {
    'update_count':0,
    'successful_updates':0,
    'failed_updates':0
}


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

def get_metadata_update_request(google_file_id, local_metadata_filename):
    # Read the metadata
    with open(local_metadata_filename) as metadata_file:
        local_mdata_json = json.load(metadata_file)

    # apply the metadata
    update_metadata = {'description':str(local_mdata_json)}
    #print(metadata)
    metadata_update_request = drive_service.files().update(
        fileId=google_file_id, 
        body=update_metadata)

    return metadata_update_request

def walk_folders(google_folder_id, local_dir, base_dir='', update_batch_requests=[]):
    
    parent_folder = drive_service.files().get(
        fileId=google_folder_id, 
        fields='name').execute()
    base_dir = base_dir + parent_folder['name'] + '/'
    print("Current base directory {}".format(base_dir))

    # list current google drive folder
    current_files = list_folder(google_folder_id)

    # find corresponding metadata side car for each file / object, but not folders,
    #     and, construct metadata update http request, and add to batch list for execution
    #     later on
    metadata_dir = base_dir + '.metadata/'
    for curr_file in current_files:
        if (curr_file['mimeType'] != 'application/vnd.google-apps.folder'):
            local_metadata_file = local_dir + metadata_dir + curr_file['name'] + '.json'
            if os.path.exists(local_metadata_file):
                update_request = get_metadata_update_request(curr_file['id'], local_metadata_file)    
                update_batch_requests.append(update_request)
                #update_metadata(curr_file['id'], local_metadata_file)
                print("Found {}".format(local_metadata_file))
            else:
                print("Error, no corresponding metadata file for {}".format(curr_file['name']))
  
    # if any folders, go into them recursively and repeat above
    for curr_file in current_files:
        if (curr_file['mimeType'] == 'application/vnd.google-apps.folder') and \
                                         (curr_file['name'] != '.metadata'):
            print('Going into {}'.format(curr_file['name']))
            walk_folders(curr_file['id'], local_dir, base_dir, update_batch_requests)

    return update_batch_requests

def execute_batch_request(batch_requests):
    def callback(request_id, response, exception):
        if exception:
            # Handle error
            UPDATE_METRICS['failed_updates'] = UPDATE_METRICS['failed_updates'] + 1
            print("Error while attempting batch update")
            print(exception)
        else:
            UPDATE_METRICS['successful_updates'] = UPDATE_METRICS['successful_updates'] + 1
            print("{} metadata updated. id={}".format(response['name'],response['id']))#.get('id')))

    #batch = drive_service.new_batch_http_request(callback=callback)
    count = 0
    # split batch if larger than 100 entries
    batches = []
    current_batch = []
    for batch_request in batch_requests:
        current_batch.append(batch_request)
        count += 1
        if count == 100:
            batches.append(current_batch)
            current_batch = []
    batches.append(current_batch)
    #total_len = 0
    #for batch in batches:
    #    total_len += len(batch)

    responses = []
    for batch_requests in batches:
        batch = drive_service.new_batch_http_request(callback=callback)
        for request in batch_requests:
            batch.add(request)
        response = batch.execute()
        responses.append(response)
        # sleep between requests to avoid 403: User Rate Limit Exceeded error
        time.sleep(2)

    return responses
    #print("total length:{}".format(total_len))

        

    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-dir", required=True, help="folder containing .metadata folders")
    args = parser.parse_args()
    metadata_folder = args.metadata_dir

    drive_service = google_drive_oath()
    if drive_service:
        update_batch_requests = walk_folders(PARENT_FOLDER_ID, metadata_folder)
        #for update_request in update_batch_requests:
        #    print(update_request)
        #print(len(update_batch_requests))
        UPDATE_METRICS['update_count'] = len(update_batch_requests)
        execute_batch_request(update_batch_requests)
        print("\nUPDATE METRICS\n{}".format(UPDATE_METRICS))
        # udate file metadata
    else:
        logging.info("Exiting, no google drive service available.")



    #main()