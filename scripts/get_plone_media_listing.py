import argparse
import json
import requests
import time
import logging
import os
import urllib
import shutil

src_base_url = 'http://media.dirisa.org/'
src_folders = ['TestFiles']#['inventory/archive/spatial']#
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

def copy_plone_media_to_local(folder_file_mapping, dest_dir, creds, metadata_output_file):
    wget_cmd = "cd {destpath} && wget -U 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)' " \
               "--post-data '__ac_name={username}&__ac_password={password}' " \
               "{fileurl} -O {dest_filename}"
    md5_cmd = "bash generate_hash_file.sh {inputfile} {outputdir}"
     
    # first create the destination folders
    all_metadata = {}
    for folder in folder_file_mapping:
        folder_end = folder.replace(src_base_url,'')
        path = os.path.abspath(dest_dir + folder_end)
        try:            
            if not os.path.exists(path):
                print('creating folder {}'.format(path))
                os.makedirs(path)
            if not os.path.exists(path + '/.md5sums'):
                print('creating metadata folder {}'.format(path + '/.md5sums'))
                os.makedirs(path + '/.md5sums')
        except Exception as e:
            logging.exception("Could not create directory %s" % (folder))

        all_metadata[folder_end] = []
        files = folder_file_mapping[folder]
        for file in files:
            #print(file['type'])
            url = file['context_path']            
            ##print("copying {} to {}".format(url,path))
            file_name = url.split('/')[-1]
            #file_path = path + '/' + file_name           
            downlod_cmd = wget_cmd.format(destpath=path, username=creds['src_user'], password=creds['src_pwd'], 
                                          fileurl=url, dest_filename=file_name)
            os.system(downlod_cmd)
            file_to_hash = path + '/' + file_name
            mdf5sum_path = path + '/.md5sums/'
            md5_hash_cmd = md5_cmd.format(inputfile=file_to_hash, outputdir=mdf5sum_path)
            print(md5_hash_cmd)
            md5sum_str = os.popen(md5_hash_cmd).read()
            print("{} MD5SUM {}".format(file_name, md5sum_str))
            file['md5sum'] = md5sum_str
            all_metadata[folder_end].append(file)
    with open(metadata_output_file,'w') as outfile:
        json.dump(all_metadata, outfile)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-user", required=True, help="user name for plone media source")
    parser.add_argument("--src-pwd", required=True, help="admin password for plone media source")
    parser.add_argument("--dest-dir", required=True, help="destination directory to where media" \
                                                          "directories and files will be copied")
    parser.add_argument("--metadata-output-file", required=True, help="file to output all plone" \
                                                                         "mediametadata json to")
    args = parser.parse_args()
    creds = {
        'src_user': args.src_user,
        'src_pwd': args.src_pwd,
    }
    folder_file_mapping = get_plone_media_listing(creds)
    copy_plone_media_to_local(folder_file_mapping, args.dest_dir, creds, args.metadata_output_file)

