import json
import argparse
import google_drive_update_metadata
from googleapiclient import errors

PARENT_FOLDER_ID = '1RydbeOWJ6CGfG2S1e4wkSk56mhoHcce6'
FILE_COUNT = {'file_count':0}

def count_files(all_metadata_json):
    for k in all_metadata_json:
        for record in all_metadata_json[k]:
            FILE_COUNT['file_count'] = FILE_COUNT['file_count'] + 1

def pop_matches(md5files, all_metadata_json):
    folder_keys = all_metadata_json.keys()
    for json_rec in md5files:
        for i in range(len(folder_keys)):
            folder_key = folder_keys[i]
            records = all_metadata_json[folder_key]
            index = 0
            
            for k in range(len(records)):
                md5sum = records[index]['md5sum']
                match_md5sum = json_rec['name'].split('.')[-1]
                if md5sum == match_md5sum:
                    records.pop(index)
                    index = index - 1
                index += 1 


def list_folder(google_folder_id):
    def googleapi_list_folder(google_folder_id):
        result = []
        page_token = None
        while True:
            try:
                param = {}
                if page_token:
                  param['pageToken'] = page_token
                #else:
                param['pageSize'] = 1000
                param['q'] = "'{}' in parents and trashed=false".format(google_folder_id)
                param['fields'] = "nextPageToken, files(id, name, mimeType)"

                files = drive_service.files().list(**param).execute()        
                result.extend(files.get('files',[]))#['items'])
                page_token = files.get('nextPageToken')
                if not page_token:
                  break
                else:
                    print("Page token!!!!")
            except errors.HttpError, error:
                print("Error! couldn't list google folder. {}".format(error))
                break
        return result

    results = googleapi_list_folder(google_folder_id)

    md5_sum_folder_id = None
    for res in results:
        #print(res['name'])
        if res['name'] == '.md5sums':
            md5_sum_folder_id = res['id']
            #print("Found {}".format(res['name']))
    md5_results = []
    if md5_sum_folder_id:
        md5_results = googleapi_list_folder(md5_sum_folder_id)
    return (results, md5_results)

def walk_folders(google_folder_id, all_metadata_json, base_dir='', md5files=[]):
    #print(md5files)
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
                    md5files.append(md5_sum_file)
            if md5_match and hits == 1:
                print("Found unique md5sum match for {}".format(curr_fname))
            else:
                print("Error! No unique md5sum match for {}".format(curr_fname))
            if (hits > 1):
                print("Error! Duplicate md5sum for {}".format(curr_fname))
            
            # get metadata from all metadata for this file using path and corresponding hash
            #print('getting mdata for {} and {}'.format(base_dir, md5_match))
            
    
    # if any folders, go into them recursively and repeat above
    for curr_file in current_files:
        if (curr_file['mimeType'] == 'application/vnd.google-apps.folder') and \
                                            (curr_file['name'] != '.md5sums'):
            print('Going into {}'.format(curr_file['name']))
            walk_folders(curr_file['id'], all_metadata_json, base_dir, md5files)

    return md5files


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-metadata-file", required=True, help="file containing metadata in json format")
    args = parser.parse_args()
    with open(args.all_metadata_file) as metadata_file:
        all_metadata_json = json.load(metadata_file)
    drive_service = google_drive_update_metadata.google_drive_oath()
    if drive_service:
        md5files = walk_folders(PARENT_FOLDER_ID, all_metadata_json)

    #md5files = [{u'mimeType': u'application/octet-stream', u'id': u'1FQHkvuqbNdSKkNbBwsWArAh5DkNE85IG', u'name': u'arid-lands.476dcd4b0fb8c735c2a26ba6e619f8f8'}, {u'mimeType': u'application/octet-stream', u'id': u'1EXS0ucxHzdgVGdC6hsQmsupPDXm6QIR7', u'name': u'Td4%202013-01-02.5186507d1667007db59b26290ecde9f1'}, {u'mimeType': u'application/octet-stream', u'id': u'1EtCGL5O_qhujuRHCdrS3IQapVOPdZpO_', u'name': u'C5%202013-04-22.627a5a786e682c1aed13e4ca5d564d2f'}, {u'mimeType': u'application/octet-stream', u'id': u'1EqQh7m-eYN6-OZbP4pvpp02gBwKcZq_4', u'name': u'C11%202013-07-19.8ab71b59a8f83e20cd022707f9e19b6a'}, {u'mimeType': u'application/octet-stream', u'id': u'1EkKYfwT_2CyZaPad45LPAnRtbhj-lRgo', u'name': u'L12%202012-11-20.d65346f53e08d1f71203ebfb80c52642'}, {u'mimeType': u'application/octet-stream', u'id': u'1F--b202KlHxmtk38e_GpcCX0K-uCHa2z', u'name': u'C5%202013-03-04.d866db641c2203eaae09d868144f368a'}, {u'mimeType': u'application/octet-stream', u'id': u'1EiLg-h5Y2dbNmeZwZXq1KO4F60yzEXVm', u'name': u'L12%202014-02-06.4833aedfd2bcca86ef9b87b656e96228'}, {u'mimeType': u'application/octet-stream', u'id': u'1EgXOKjgsmpswL3G8kFSmdFkxtP6lAZ8t', u'name': u'L16%202012-09-13.3fb95aae79db80d6813e4a2ef4445be4'}, {u'mimeType': u'application/octet-stream', u'id': u'1Eqr6JJQJa_NBidUnffuexdeSR3M-6VeF', u'name': u'C10%202013-01-02.cf149a2b1d9860a46989e8ea309f40e6'}]
    print("all-matches {} ".format(len(md5files)))
    #count_files(all_metadata_json)
    print("\n\nPopping matches ...\n\n")
    pop_matches(md5files, all_metadata_json)
    print("\n Counting remaining unmatched ...")
    count_files(all_metadata_json)
    #count_files(all_metadata_json)
    print(FILE_COUNT)
    print("writing unmatched json to file")
    with open('remaining_unmatched.json','w') as outfile:
        json.dump(all_metadata_json, outfile)

    #print(all_metadata_json)