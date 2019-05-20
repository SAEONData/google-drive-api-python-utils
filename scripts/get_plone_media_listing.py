import argparse
import json
import requests
import time
import logging
import os
import urllib
import shutil

src_base_url = 'http://media.dirisa.org/'
src_folders = ['TestFiles']
MAX_RETRIES=10
logging.basicConfig(level=logging.ERROR)

def request_plone_json(creds, src_url):
    src_url = src_url + '/jsonContent?depth=0'
    max_tries = MAX_RETRIES
    success = False
    response = None
    while(max_tries > 0 and not success):
        response = requests.get(
            url=src_url,
            auth=requests.auth.HTTPBasicAuth(
                creds['src_user'], creds['src_pwd'])
        )

        if response.status_code != 200:
            logging.error('Request failed with return code: %s on url path %s' % (
                response.status_code, src_url))
            max_tries -=1
        else:
            success = True

    results = json.loads(response.text)

    return results

def get_plone_media_listing(creds):    
    def walk_result(url, creds, folders_dict, child_json=None):
        if not child_json:
            print('Requesting json for url {}'.format(url))
            # sleep between requests to reduce server load
            time.sleep(1)
            json_obj = request_plone_json(creds, url)
        else:
            json_obj = child_json
        # If current obj has children iterate recursively, else store current obj
        if ('children' in json_obj) and (len(json_obj['children']) > 0):
            curr_children = json_obj['children']   
        else:
            curr_context_path = json_obj['context_path']
            path_parts = curr_context_path.split('/')
            curr_parent = '/'.join(path_parts[0:-1])
            if curr_parent in folders_dict:
                metadata_dict = {}
                for key in json_obj:
                    if key != 'children':
                        metadata_dict[key] = json_obj[key]
                folders_dict[curr_parent].append(metadata_dict)
            else:
                raise Exception("Parent doesn't exist!{}}".format(curr_parent))
            return []
        
        curr_context_path = json_obj['context_path']
        if curr_context_path not in folders_dict:
            folders_dict[curr_context_path] = []
        for child in curr_children:
            if child['type'] == 'Folder':      
                walk_result(url=child['context_path'], creds=creds, folders_dict=folders_dict)
            else:
                walk_result(url=child['context_path'], creds=creds, child_json=child, folders_dict=folders_dict)
    
    folders_dict = {}
    for folder in src_folders:
        filler = ''
        if src_base_url[-1] != '/':
            filler = '/'
        url = src_base_url + filler + folder
        walk_result(url, creds, folders_dict)

    return folders_dict

def copy_plone_media_to_local(folder_file_mapping, dest_dir, creds):
    wget_cmd = "cd {destpath} && wget -U 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)' " \
               "--post-data '__ac_name={username}&__ac_password={password}' " \
               "{fileurl}"
     
    # first create the destination folders
    for folder in folder_file_mapping:
        folder_end = folder.replace(src_base_url,'')
        path = os.path.abspath(dest_dir + folder_end)
        try:            
            if not os.path.exists(path):
                print('creating folder {}'.format(path))
                os.makedirs(path)
        except Exception as e:
            logging.exception("Could not create directory %s" % (folder))

        files = folder_file_mapping[folder]
        for file in files:
            #print(file['type'])
            url = file['context_path']            
            #print("copying {} to {}".format(url,path))            
            file_path = path + '/' + file['title']            
            downlod_cmd = wget_cmd.format(destpath=path, username=creds['src_user'], password=creds['src_pwd'], fileurl=url)
            print(downlod_cmd)
            os.system(downlod_cmd)
            
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-user", required=True, help="user name for plone media source")
    parser.add_argument("--src-pwd", required=True, help="admin password for plone media source")
    parser.add_argument("--dest-dir", required=True, help="destination directory to where media" \
                                                          "directories and files will be copied")
    args = parser.parse_args()
    creds = {
        'src_user': args.src_user,
        'src_pwd': args.src_pwd,
    }
    folder_file_mapping = get_plone_media_listing(creds)
    copy_plone_media_to_local(folder_file_mapping, args.dest_dir, creds)

