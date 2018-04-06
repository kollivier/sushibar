import json
import uuid
from sushibar.ccserverlib.services import ccserver_get_node_children, get_channel_status_bulk

def set_run_options(run):
    run.extra_options = run.extra_options or {}
    statuses_dict = get_channel_status_bulk(run.content_server, run.started_by_user_token, [run.channel.channel_id.hex])
    status = statuses_dict.get(run.channel.channel_id.hex) if statuses_dict else None
    run.extra_options.update({
        'staged': status == 'staged',
        'published': status =='published'
    })
    run.save()

def load_tree_for_channel(run_dict):
    """
    Load the json tree data for `run_dict['channel_id']` from Kolibri Studio and
    cache it under `run_dict['tree_data_path']`. This can take 30secs+ for large
    channels, so we do it as background task to avoid timouts and the notorious
    sushi-eating cat being show to users!
    """
    tree = load_children_for_node(run_dict)
    with open(run_dict['tree_data_path'], 'w+') as fout:
        json.dump(tree, fout)

def load_children_for_node(run_dict, node_id=None):
    tree = []
    children = ccserver_get_node_children(run_dict, node_id=node_id)
    for child in children:
        if child.get('node_id'):
            child.update({"children": load_children_for_node(run_dict, node_id=child['node_id'])})
        tree.append(child)
    return tree

def calculate_channel_id(source_id, domain):
    domain_namespace = uuid.uuid5(uuid.NAMESPACE_DNS, domain)
    return uuid.uuid5(domain_namespace, source_id)
