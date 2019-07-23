import argparse
import json
import os

CHECK_METRICS = {
    'checksum_matches':0,
    'checksum_mismatches':0,
}

def download_file(file_url, creds, dest_dir, file_name):
    wget_cmd = "cd {destpath} && wget -U 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)' " \
            "--post-data '__ac_name={username}&__ac_password={password}' " \
            "{fileurl} -O {dest_filename}"
    path = os.path.abspath(dest_dir)    
    download_cmd = wget_cmd.format(destpath=path, username=creds['src_user'], password=creds['src_pwd'], 
                                    fileurl=file_url, dest_filename=file_name)
    os.system(download_cmd)

def get_checksum(dest_dir, file_name):
    md5_cmd = "bash generate_hash_file.sh {inputfile} {outputdir}"
    path = os.path.abspath(dest_dir)
    file_to_hash = path + '/' + file_name
    mdf5sum_path = path + '/.md5sums/'

    if not os.path.exists(path + '/.md5sums'):
        print('creating metadata folder {}'.format(path + '/.md5sums'))
        os.makedirs(path + '/.md5sums')

    md5_hash_cmd = md5_cmd.format(inputfile=file_to_hash, outputdir=mdf5sum_path)
    #print(md5_hash_cmd)
    md5sum_str = os.popen(md5_hash_cmd).read().replace('\n','')

    return md5sum_str

def cleanup_dir(dest_dir, file_name):
    path = os.path.abspath(dest_dir)
    file_to_remove = path + '/' + file_name
    os.system("rm {}".format(file_to_remove))
    os.system("rm {}/*".format(path + '/.md5sums'))

def download_and_compare_checksum(all_metadata_json, creds, dest_dir):
    for k in all_metadata_json:
        for record in all_metadata_json[k]:
            print("{}\n{}\n".format(record['md5sum'],record['context_path']))
            file_name = record['context_path'].split('/')[-1]
            download_file(record['context_path'], creds, dest_dir, file_name)
            md5sum_str = get_checksum(dest_dir, file_name)
            cleanup_dir(dest_dir, file_name)
            #print(md5sum_str)
            #print(record['md5sum'])
            if md5sum_str == record['md5sum']:
                print("Checksum match success: {}".format(record['context_path']))
                CHECK_METRICS['checksum_matches'] = CHECK_METRICS['checksum_matches'] + 1
            else:
                print("Checksum match failure: {}".format(record['context_path']))
                CHECK_METRICS['checksum_mismatches'] = CHECK_METRICS['checksum_mismatches'] + 1
            #print(record.keys())
        #brk
        #break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-user", required=True, help="user name for plone media source")
    parser.add_argument("--src-pwd", required=True, help="admin password for plone media source")
    parser.add_argument("--dest-dir", required=True, help="folder where files are downloaded and checked")
    parser.add_argument("--all-metadata-file", required=True, help="file containing metadata in json format")
    args = parser.parse_args()
    with open(args.all_metadata_file) as metadata_file:
        all_metadata_json = json.load(metadata_file)
    
    creds = {
        'src_user': args.src_user,
        'src_pwd': args.src_pwd,
    }
    
    download_and_compare_checksum(all_metadata_json, creds, args.dest_dir)

    print(CHECK_METRICS)
