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
PARENT_FOLDER_ID = '1kIHacMlBtpyF42rGyvML43dmXE02T_h7'#'13rQ1YRz012Ns_7Fh3RgDWdBwPK9YcfXW' # Root google drive folder 
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

    # list the .md5sum folder if it exists
    md5_sum_folder_id = None
    for res in results:
        #print(res['name'])
        if res['name'] == '.md5sums':
            md5_sum_folder_id = res['id']
            #print("Found {}".format(res['name']))
    md5_results = []
    if md5_sum_folder_id:
        response = drive_service.files().list(
            pageSize=1000,
            q="'{}' in parents and trashed=false".format(md5_sum_folder_id),
            fields="nextPageToken, files(id, name, mimeType)").execute()
        md5_results = response.get('files',[])
        #print("MD5s {}".format(md5_results))
    return (results, md5_results)

def get_metadata_update_request(google_file_id, metadata_record):
    # apply the metadata
    update_metadata = {'description':str(metadata_record)}
    #print(metadata)
    metadata_update_request = drive_service.files().update(
        fileId=google_file_id, 
        body=update_metadata)

    return metadata_update_request

def walk_folders(google_folder_id, all_metadata_json, base_dir='', update_batch_requests=[]):
    
    parent_folder = drive_service.files().get(
        fileId=google_folder_id, 
        fields='name').execute()
    base_dir = base_dir + parent_folder['name'] + '/'
    print("Current base directory {}".format(base_dir))

    # list current google drive folder and md5sum folder
    (current_files,curr_md5sum_files) = list_folder(google_folder_id)

    # find corresponding metadata side car for each file / object, but not folders,
    #     and, construct metadata update http request, and add to batch list for execution
    #     later on
    #metadata_dir = base_dir + '.metadata/'
    for curr_file in current_files:
        if (curr_file['mimeType'] != 'application/vnd.google-apps.folder'):


            #local_metadata_file = local_dir + metadata_dir + curr_file['name'] + '.json'
            curr_fname = curr_file['name']
            hits = 0
            md5_match = None
            for md5_sum_file in curr_md5sum_files:
                md5_hash = md5_sum_file['name'].split('.')[-1]
                if md5_sum_file['name'].replace('.' + md5_hash,'') == curr_fname:
                    md5_match = md5_hash#md5_sum_file['name']
                    hits += 1
            if md5_match and hits == 1:
                print("Found unique md5sum match for {}".format(curr_fname))
            else:
                print("Error! No unique md5sum match for {}".format(curr_fname))
            if (hits > 1):
                print("Error! Duplicate md5sum for {}".format(curr_fname))
           
            # get metadata from all metadata for this file using path and corresponding hash
            #print('getting mdata for {} and {}'.format(base_dir, md5_match))
            update_request = None
            base_dir_sub = base_dir[0:len(base_dir) - 1]
            if base_dir_sub in all_metadata_json.keys():
                metadata_record = None
                for record in all_metadata_json[base_dir_sub]:
                    curr_hash = record['md5sum']
                    #print("ebiscuit {} {}".format(curr_hash, md5_match))
                    if curr_hash == md5_match:
                        metadata_record = record
                        break
                if metadata_record:
                    print("Constructing metadata update request for {}".format(curr_file['name']))
                    update_request = get_metadata_update_request(curr_file['id'], metadata_record)
                    pass
                else:
                    print("Error! no metadata record found for {}".format(curr_file['name']))
            else:
                print("Error! no metadata records for folder {}".format(base_dir))
                print(all_metadata_json.keys())

            if update_request:
                print("Adding update request to batch")
                update_batch_requests.append(update_request)
            else:
                print("Error! Update request not created.")
  
    # if any folders, go into them recursively and repeat above
    for curr_file in current_files:
        if (curr_file['mimeType'] == 'application/vnd.google-apps.folder') and \
                                         (curr_file['name'] != '.md5sums'):
            print('Going into {}'.format(curr_file['name']))
            walk_folders(curr_file['id'], all_metadata_json, base_dir, update_batch_requests)

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
    parser.add_argument("--all-metadata-file", required=True, help="file containing metadata in json format")
    args = parser.parse_args()
    with open(args.all_metadata_file) as metadata_file:
        all_metadata_json = json.load(metadata_file)

    drive_service =google_drive_oath()
    if drive_service:
        update_batch_requests = walk_folders(PARENT_FOLDER_ID, all_metadata_json)
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