import argparse
import json
import requests
import time
import logging

#src_url = 'http://media.dirisa.org/TestFiles/jsonContent?depth=-1'
src_base_url = 'http://media.dirisa.org/'
MAX_RETRIES=10
logging.basicConfig(level=logging.ERROR)
#    response = requests.post(
#        url=url,
#        params=data,
#        auth=requests.auth.HTTPBasicAuth(
#            creds['ckan_user'], creds['ckan_pwd'])
#    )

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
    walk_result(src_base_url, creds, folders_dict)

    for folder in folders_dict:
        print("\n{}\n".format(folder))
        for item in folders_dict[folder]:
            print("{} ".format(item['context_path']))

 
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-user", required=True, help="user name for plone media source")
    parser.add_argument("--src-pwd", required=True, help="admin password for plone media source")
    args = parser.parse_args()
    creds = {
        'src_user': args.src_user,
        'src_pwd': args.src_pwd,
    }
    get_plone_media_listing(creds)