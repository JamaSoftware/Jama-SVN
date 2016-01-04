#!/bin/env python

#-------CONFIG--------

# Links to SVN will begin with this and end with path to repo.
# You can find this url by navigating to your repo in a browser.
# It may be helpful to create a validation branch instead of /head/
base_svn_url = "http://my-svn-repo.example.com/!/#RepoName/view/head/"
# The URL of your Jama REST API.  Ends with /rest/latest/
base_jama_url = "http://{Jama Base URL}/rest/latest/"
# This string will appear at the beginning of the items which contain source code references
base_jama_name = "Validation of " 
# These should be kept somewhere other than the source code depending on your organizations security policies
username = "API_User" 
password = "********"
# The type of relationship to create when a new source code item is created
jama_relationship = "Related to"
# The name of the set where source code items are kept (Must be the same in each Jama project)
svn_set_name = "Code Validations"
# The item type of the items which contain the source code references
svn_item_type_api_id = 78 
# The regex to apply when searching commit messages for Jama Document Keys
# "([A-Z]{1,7}-[A-Z]{1,7}-\d{1,7})" means: 1-7 capital letters, then a '-', then 1-7 capital letters, then a '-', then 1-7 numbers
jama_doc_key_regex = "([A-Z]{1,7}-[A-Z]{1,7}-\d{1,7})"

#-----END CONFIG------

import re
import requests
import sys
import os.path
import json
import time
import subprocess
import urllib

class Modification(object):
    def __init__(self, status_code, link_text):
        self.status_code = status_code
        self.link_text = link_text 

def main():
    commit_message = get_commit_message()
    jama_doc_keys = re.findall(jama_doc_key_regex, commit_message)
    if len(jama_doc_keys) > 0: # If a document key isn't found, end execution
        info_block = create_info_block(commit_message)
        for jama_doc_key in jama_doc_keys:
            update_jama(jama_doc_key, info_block)

def get_commit_message():
    # sys.argv[2] is the revision number anmd sys.argv[1] is the repository path 
    revision_and_repo = sys.argv[2] + " " + sys.argv[1]
    subprocess_command = "svnlook propget --revprop -r " + revision_and_repo + " svn:log"
    return subprocess.Popen(subprocess_command, stdout=subprocess.PIPE).communicate()[0]

def create_info_block(commit_message):
    repo_name = sys.argv[1].split(os.path.sep)[-1]
    revision = sys.argv[2]
    date = time.strftime("%b %d, %Y  %X")
    user = get_commit_author()
    message = commit_message
    modifications = get_modifications()

    return format_template(repo_name, revision, date, user, message, modifications)

def get_commit_author():
    repo_and_revision = sys.argv[2] + " " + sys.argv[1]
    subprocess_command = "svnlook author -r " + repo_and_revision
    return subprocess.Popen(subprocess_command, stdout=subprocess.PIPE).communicate()[0]

def get_modifications():
    modList = []
    for mod in get_changed_files().split("\n"):
        if mod.strip():
            # Split the status to separate the status code and file
            status_code = mod[:3].strip()
            file_changed = mod[3:].strip()
            modList.append(Modification(status_code, file_changed))
    return modList
    
def get_changed_files():
    subprocess_command = "svnlook changed " + sys.argv[1]
    return subprocess.Popen(subprocess_command, stdout=subprocess.PIPE).communicate()[0]

def format_template(reponame, revision, date, user, message, modifications):
    template_line = "<p><span style=\"font-size:13px\"><strong>{0}:&nbsp;</strong>{1}</span></p>"
    modification_template_line = "<p><span style=\"font-size:13px\">{0}:&nbsp;<a href=\"{1}\" target=\"_blank\">{2}</a></span></p>"

    info_block = template_line.format("Repository", reponame)
    info_block += template_line.format("Revision", revision)
    info_block += template_line.format("Date", date)
    info_block += template_line.format("User", user)
    info_block += template_line.format("Message", message)
    info_block += template_line.format("Modifications", "")

    for mod in modifications:
        info_block += modification_template_line.format(mod.status_code, base_svn_url + mod.link_text , mod.link_text)

    return info_block + "<br><br><br>"

def post(url, payload):
    response = requests.post(url, auth=(username, password), json=payload)
    # 429 means the server is busy, so retry in half a second
    if response.status_code == 429:
        time.sleep(500)
        return post(url, payload)
    return finish_write(response, url, payload)

def put(url, payload):
    response = requests.put(url, auth=(username, password), json=payload)
    if response.status_code == 429:
        time.sleep(500)
        return put(url, payload)
    return finish_write(response, url, payload)

def finish_write(response, url, payload):
    if response.status_code >= 400:
        terminate_on_error(response, url)
    return json.loads(response.text)

def get(url):
    results = []
    resultsPerPage = 20
    start_index = 0
    remaining_results = -1

    while remaining_results != 0:
        start_at = "startAt=" + str(start_index)

        response = requests.get(url, auth=(username, password))
        if response.status_code == 429:
            time.sleep(500)
            return get(url)
        elif response.status_code >= 400:
            terminate_on_error(response, url)
        jsonResponse = json.loads(response.text)

        if "pageInfo" not in jsonResponse:
            return jsonResponse["data"]

        page_info = jsonResponse["meta"]["page_info"]
        result_count = page_info["resultCount"]
        total_results = page_info["totalResults"]
        remaining_reusults = total_results - (start_index + result_count)
        start_index = page_info["startIndex"] + resultsPerPage

        for item in jsonResponse["data"]:
            results.append(item)
    return results

def terminate_on_error(response, url):
    # This message will propogate to the user making the commit
    sys.stderr.write("Server responded with: " + str(response.status_code) + \
		    "\nFor url: " + url + "\nWith message: " + response.text)
    sys.exit(1)
        
def update_jama(doc_key, info_block):
    items = get(base_jama_url + "abstractitems/?contains=" + doc_key)
    # No items were found matching that Document Key
    if len(items) < 1:
        return
    upstream_item = items[0] # Document keys are unique
    upstream_item_id = upstream_item["id"]
    downstream_items = get(base_jama_url + "items/" + str(upstream_item_id) + "/downstreamrelated")

    downstream_exists = False
    for ds_item in downstream_items:
        if ds_item["itemType"] == svn_item_type_api_id:
            downstream_exists = True
            add_to_existing_jama_item(ds_item["id"], info_block)
    if not downstream_exists:
        create_new_downstream_item(upstream_item_id, upstream_item["project"], base_jama_name + upstream_item["fields"]["documentKey"], info_block)

def add_to_existing_jama_item(item_id, to_prepend):
    url = base_jama_url + "items/" + str(item_id)
    put(url + "/lock", { "locked":True }) # Lock the item
    item = get(url) # GET the item
    item["fields"]["description"] = to_prepend + item["fields"]["description"] # Edit the item
    put(url, item) # PUT the item
    put(url + "/lock", { "locked":False }) # Unlock the item

def create_new_downstream_item(upstream_item_id, project_id, name, info_block):
    sanatized_contains = "abstractitems/?contains=" + urllib.quote_plus(svn_set_name)
    url = base_jama_url + sanatized_contains + "&project=" + str(project_id)
    item_sets = get(url)
    # If no set with name = svn_set_name exists in the item's project, skip the update
    for item_set in item_sets:
        if 'childItemType' in item_set and item_set["childItemType"] == svn_item_type_api_id:
            downstream_item_id = post_new_item_to_set(item_set["id"], project_id, name, info_block)
            create_relationship(upstream_item_id, downstream_item_id)

def post_new_item_to_set(set_id, project_id, name, info_block):
    payload = {
        "project":project_id,
        "itemType":svn_item_type_api_id,
        "location": {
            "parent": {
                "item": set_id
            }
        },
        "fields": {
            "name":name,
            "description":info_block
            # Additional fields go here
        }
    }
    result = post(base_jama_url + "items/", payload)
    return result["meta"]["location"].split("/")[-1]

def create_relationship(upstream_item_id, downstream_item_id):
    payload = {
        "fromItem":upstream_item_id,
        "toItem":downstream_item_id
    }
    relationship_type = get_relationshiptype_id(jama_relationship)
    if relationship_type is not None:
        payload["relationshipType"] = relationship_type
    post(base_jama_url + "relationships/", payload)

def get_relationshiptype_id(relationship_name):
    relationshiptypes = get(base_jama_url + "relationshiptypes")
    for relationshiptype in relationshiptypes:
        if relationshiptype["name"] == relationship_name:
            return relationshiptype["id"]
    return None

if __name__ == '__main__':
    sys.exit(main())

