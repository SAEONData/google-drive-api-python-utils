import argparse
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

def walk_folders(google_folder_id, results_dict={}):

    # list current folder
    current_files = list_folder(google_folder_id)

    # list metadata folder, get json for each file
    metadata_files = None
    for curr_file in current_files:
        if curr_file['name'] == '.metadata':
            metadata_files = list_folder(curr_file['id'])
            break
    # apply metadata json to files in current folder properties field
    if metadata_files:
        for md_file in metadata_files:
            md_fname = md_file['name']
            applied_mdata = False
            for curr_file in current_files:
                if curr_file['name'] == md_fname.replace('.json',''):
                    # download the corresponding metadata file
                    request = drive_service.files().get_media(fileId=md_file['id'])
                    fh = BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        print("Download {}".format(int(status.progress() * 100)))
                    metadata_json = fh.getvalue().decode('UTF-8')

                    # apply the metadata
                    update_metadata = {'description':metadata_json}
                    #print(metadata)
                    updated_file = drive_service.files().update(
                        fileId=curr_file['id'], 
                        body=update_metadata).execute()
                    if updated_file:
                        print("applied metadata to {}".format(curr_file['name']))
                        applied_mdata = True
                    else:
                        print("metadata update failed!")
                    break
            if not applied_mdata:
                print('Error! could not find matching file to apply metadata')

    # if any folders, go into them recursively and repeat above
    for curr_file in current_files:
        if (curr_file['mimeType'] == 'application/vnd.google-apps.folder') and \
                                         (curr_file['name'] != '.metadata'):
            walk_folders(curr_file['id'])
        else:
            return


            
    # else return


    #if not folder:
    #    file = drive_service.files().get(
    #        fileId=file_details.get('id'), 
    #        fields='name').execute()
        

if __name__ == '__main__':

    drive_service = google_drive_oath()
    if drive_service:
        walk_folders(PARENT_FOLDER_ID)    
        # udate file metadata

        """
        print('getting files ...')
        response = drive_service.files().list(
            pageSize=1000,
            q="'{}' in parents and trashed=false".format(PARENT_FOLDER_ID),
            fields="nextPageToken, files(id, name)").execute()
        print(response)
        file_details = response.get('files',[])
        for f in file_details:
            print("got {}".format(f))
        
        file_details = response.get('files',[])[0]
        print('Found file: %s (%s)' % (file_details.get('name'), file_details.get('id')))
        metadata = {'description':"[{test99:'test2',test2:{test3:[]}}]",
                    'properties':{"testfield10":"testvalue10","testfield20":"testvalue20x"}
                   }
        updated_file = drive_service.files().update(fileId=file_details.get('id'), body=metadata).execute()

        # check file metadata
        response = drive_service.files().list(
                 pageSize=1000,
                 q="'{}' in parents and name='README.txt' and trashed=false".format(PARENT_FOLDER_ID),
                 fields="nextPageToken, files(id, name, properties)").execute()
        file_details = response.get('files',[])[0]
        print("Updated file metadata properties field:\n{}".format(file_details.get('properties')))
        file = drive_service.files().get(fileId=file_details.get('id'), fields='properties').execute()
        """

    else:
        logging.info("Exiting, no google drive service available.")



    #main()