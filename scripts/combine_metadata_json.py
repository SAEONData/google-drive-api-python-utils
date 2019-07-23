import json
import sys

json_files = [
    'mdata/inventory.archive.mdata/inventory.media.measey-ii.measy.iii.json',
    'mdata/inventory.archive.mdata/inventory.media.measey.samref.composite.collections.presence-learning-network.pulications.samref.json',
    'mdata/inventory.archive.mdata/inventory.spatial.observations.multi.structured.json']

all_json_mdata = []
for f in json_files:
    with open(f,'r') as jf:
        json_mdata = json.load(jf)
    all_json_mdata.append(json_mdata)

all_json_dict = {}
for json_mdata in all_json_mdata:
    for k in json_mdata.keys():
        if k not in all_json_dict:
            all_json_dict[k] = json_mdata[k]
        else:
            print('Duplicate key found!')
            sys.exit(0)

with open('./all_metadata.json','w') as outfile:
    json.dump(all_json_dict, outfile)
    outfile.close()
