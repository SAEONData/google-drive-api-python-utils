import argparse
import json
import requests


#src_url = 'http://media.dirisa.org/TestFiles/jsonContent?depth=-1'
src_url = 'http://media.dirisa.org/jsonContent?depth=-1'

#    response = requests.post(
#        url=url,
#        params=data,
#        auth=requests.auth.HTTPBasicAuth(
#            creds['ckan_user'], creds['ckan_pwd'])
#    )

def get_plone_media_listing(creds):
    response = requests.get(
        url=src_url,
        auth=requests.auth.HTTPBasicAuth(
            creds['src_user'], creds['src_pwd'])
    )

    if response.status_code != 200:
        raise RuntimeError('Request failed with return code: %s' % (
            response.status_code))
    results = json.loads(response.text)

    folders_dict = {}

    def walk_result(json_obj, folders_dict):
        # If current obj has children iterate recursively, else store current obj
        if ('children' in json_obj) and (len(json_obj['children']) > 0):
            curr_children = json_obj['children']   
        else:
            #curr_title = json_obj['title']
            #curr_type = json_obj['type']
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
            #print("{}, {}".format(curr_title, curr_type))
            return []
        
        curr_context_path = json_obj['context_path']
        if curr_context_path not in folders_dict:
            folders_dict[curr_context_path] = []
        #print(' -- {} {} children --'.format(json_obj['title'], json_obj['type']))
        for child in curr_children:            
            walk_result(child, folders_dict)

    walk_result(results, folders_dict)

    for folder in folders_dict:
        print("\n{}\n".format(folder))
        for item in folders_dict[folder]:
            print("{} ".format(item['type']))#,item["context_path"]))
            #print('\n')
        #print("\n{}\n: {}".format(folder, folders_dict[folder]))
        



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