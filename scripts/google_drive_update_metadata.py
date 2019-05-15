import argparse
import logging
import pickle
import os.path
import sys
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest
from googleapiclient.http import build_http
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload

import json
import requests

SCOPES = ['https://www.googleapis.com/auth/drive.metadata']#'https://www.googleapis.com/auth/drive']#'https://www.googleapis.com/auth/drive.file']
CREDS_FILE = './credentials.json'
PARENT_FOLDER_ID = '1PTYWN7_qcI8BlwkGaVmVmI_8PtvN_VA1'#'13rQ1YRz012Ns_7Fh3RgDWdBwPK9YcfXW' # Root google drive folder 
logging.basicConfig(level=logging.INFO)


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


if __name__ == '__main__':

    drive_service = google_drive_oath()
    if drive_service:
        
        file_metadata = {
            'name': 'panoply_t2',
            'other_fileType':'file',
            'textType':'text',
            'folder_mimeType': 'application/vnd.google-apps.folder',
            'file_mimeType': 'application/vnd.google-apps.file'
        }

        response = drive_service.files().list(pageSize=1000,q="'{}' in parents and name='README.txt' and trashed=false".format(PARENT_FOLDER_ID),fields="nextPageToken, files(id, name)").execute()
        file_details = response.get('files',[])[0]
        print('Found file: %s (%s)' % (file_details.get('name'), file_details.get('id')))
        file = drive_service.files().get(fileId=file_details.get('id')).execute()
        metadata = {'description':"[{test:'test2',test2:{test3:[]}}]"}
        updated_file = drive_service.files().update(fileId=file_details.get('id'), body=metadata).execute()

    else:
        logging.info("Exiting, no google drive service available.")



    #main()