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
#from apiclient.http import MediaFileUpload

import json
import requests

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDS_FILE = './credentials.json'
PARENT_FOLDER_ID = '13rQ1YRz012Ns_7Fh3RgDWdBwPK9YcfXW' # Root google drive folder 
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

def get_absolute_paths_and_file_listing(local_path):
    local_path = os.path.abspath(local_path)
    base_path = os.path.abspath(os.path.join(local_path, os.pardir)) + "/"
    paths = []
    paths_and_files = {}
    for path, dirs, files in os.walk(local_path):
        path = path.replace(base_path,"")
        paths.append(path)
        paths_and_files[path] = []
        #print(path)
        for f in files:
            paths_and_files[path].append(f)


    return (paths, paths_and_files)

#def main():

def create_folders(paths, drive_service):
    """
    @Note: depends on user configured PARENT_FOLDER_ID representing Root google drive folder
    in which folders will be created
    """
    path_id_mappings = None
    try:
        init_parent = os.path.abspath(os.path.join(paths[0], os.pardir))# + "/"        
        common_sub_prefix = init_parent
        path_id_mappings = {"google-drive-root":PARENT_FOLDER_ID}
        #curr_parent_folder_id = PARENT_FOLDER_ID
        for path in paths:
            parent = os.path.abspath(os.path.join(path, os.pardir))
            parent = parent.replace(common_sub_prefix,"")
            if len(parent) == 0:
                parent = "google-drive-root"
            else:
                if parent[0] == '/':
                    parent = parent[1:len(parent)]
            child = os.path.basename(path)
            print("creating {} in {}".format(child,parent))
            if parent in path_id_mappings:
                curr_parent_id = path_id_mappings[parent]
            else:
                msg = "Could not get parent id for {} in {}".format(parent, path_id_mappings)
                logging.error(msg)
                raise Exception(msg)

            folder_metadata = {
                'name': child,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [curr_parent_id]
            }
            file = drive_service.files().create(body=folder_metadata,
                                            fields='id').execute()
            folder_id = file.get('id')
            folder_name = child
            if parent != "google-drive-root":
                delim = '/'
                if parent[-1] == '/':
                    delim = ''
                folder_name = parent + delim + child
            path_id_mappings[folder_name] = folder_id
    except Exception as e:
        logging.exception("Error while creating folders in Google drive!")
    
    return path_id_mappings


def copy_local_path_recursively(local_path, drive_service):
    path_listing, path_and_file_listing = get_absolute_paths_and_file_listing(local_path)
    #print(path_listing)
    create_folders(path_listing, drive_service)
    #print(path_listing)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-path-to-copy-recursively", required=True, help="the local path to copy recurively to google drive")
    args = parser.parse_args()

    local_path_to_copy_recursively = os.path.abspath(args.local_path_to_copy_recursively)
    if not os.path.exists(local_path_to_copy_recursively):
        logging.error("Local path does not exist! Exiting ...")
        sys.exit(1)

    drive_service = google_drive_oath()
    if drive_service:
        copy_local_path_recursively(local_path_to_copy_recursively,drive_service)        
    else:
        logging.info("Exiting, no google drive service available.")



    #main()