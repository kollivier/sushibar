import json
from sushibar.ccserverlib.services import ccserver_get_node_children, get_channel_status_bulk

def set_run_options(run):
	run.extra_options = run.extra_options or {}
	status = get_channel_status_bulk(run, [run.channel.channel_id.hex])
	status = status['statuses'].get(run.channel.channel_id.hex) if status else None
	run.extra_options.update({
		'staged': status == 'staged',
		'published': status =='published'
	})
	run.save()

def load_tree_for_channel(run):
	tree = load_children_for_node(run)
	with open(run.get_tree_data_path(), 'w+') as fout:
		json.dump(tree, fout)

def load_children_for_node(run, node_id=None):
	tree = []
	children = ccserver_get_node_children(run, node_id=node_id)
	for child in children:
		if child.get('node_id'):
			child.update({"children": load_children_for_node(run, node_id=child['node_id'])})
		tree.append(child)
	return tree

