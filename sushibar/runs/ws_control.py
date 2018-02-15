"""
This module receives control commands and forwards them to sushi chefs.
"""
from channels import channel_layers
from channels import Group
from channels.sessions import channel_session



def clear_group(group_name):
    print("Disconnecting previously connected chefs in group %s" % group_name)
    group = Group(group_name)
    chans = channel_layers.backends['default'].channel_layer.group_channels(group_name)
    for chan in chans:
        group.discard(chan)


@channel_session
def connect(message):
    # Expected path format: /control/<channel_id>/
    _, channel_id = message['path'].strip('/').split('/')
    group_name = 'control-' + channel_id
    clear_group(group_name)
    print("CONTROL connecting to group %s" % group_name)
    Group(group_name).add(message.reply_channel)
    message.channel_session['channel_id'] = channel_id
    message.reply_channel.send({"accept": True})


@channel_session
def receive(message):
    channel_id = message.channel_session['channel_id']
    print("CONTROL receive %s, %s" % (channel_id, message['text']))
    group_name = 'control-' + channel_id
    Group(group_name).send({'text': message['text']})


@channel_session
def disconnect(message):
    # Remove from contol group on clean disconnect
    channel_id = message.channel_session['channel_id']
    group_name = 'control-' + channel_id
    print("CONTROL disconnecting from group %s" % group_name)
    Group(group_name).discard(message.reply_channel)
