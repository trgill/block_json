
import os
import subprocess
import pyudev
import json

import dmpy as dm


def get_block_device_size(device):
    if not device:
        return 0
    try:
        return int(subprocess.check_output(['blockdev', '--getsize64', device]))
    except:
        return 0


# Move filesystem attributes to a "filesystem" json node.
def get_filesystem_attrs(device, filesystems_json):
    filesystem_attrs = dict()

    if device['mountpoint'] != "null" and device['mountpoint'] != None:
        filesystem_attrs['mountpoint'] = device['mountpoint']
        filesystem_attrs['fsavail'] = device['fsavail']
        filesystem_attrs['fssize'] = device['fssize']
        filesystem_attrs['fstype'] = device['fstype']
        filesystem_attrs['fsused'] = device['fsused']
        filesystem_attrs['fsuse%'] = device['fsuse%']
        filesystem_attrs['fsver'] = device['fsver']
        filesystems_json[device['maj:min']] = filesystem_attrs

    device.pop('mountpoint', None)
    device.pop('fsavail', None)
    device.pop('fssize', None)
    device.pop('fstype', None)
    device.pop('fsused', None)
    device.pop('fsuse%', None)
    device.pop('fsver', None)


def get_child_list(device, block_devices_json, children_json, filesystems_json):

    children = []

    if (not device.get('children') is None):
        for child in device['children']:
            get_filesystem_attrs(child, filesystems_json)
            child_copy = child.copy()
            child_copy.pop('children', None)
            block_devices_json[child['maj:min']] = child_copy
            children.append(child['maj:min'])
            get_child_list(child, block_devices_json,
                           children_json, filesystems_json)
    else:
        return

    children_json[device['maj:min']] = children


def get_dm_info(name, info):
    dm_info = dict()
    dm_info['name'] = name
    dm_info['deferred_remove'] = info.deferred_remove
    dm_info['event_nr'] = info.event_nr
    dm_info['exists'] = info.exists
    dm_info['inactive_table'] = info.inactive_table
    dm_info['internal_suspend'] = info.internal_suspend
    dm_info['live_table'] = info.live_table
    dm_info['major'] = info.major
    dm_info['minor'] = info.minor
    dm_info['open_count'] = info.open_count
    dm_info['read_only'] = info.read_only
    dm_info['suspended'] = info.suspended
    dm_info['target_count'] = info.target_count
    return dm_info


def get_dm_targets():
    dm_targets = dict()
    dmt_list = dm.DmTask(dm.DM_DEVICE_LIST)
    dmt_list.run()
    for d in dmt_list.get_names():
        dmt_info = dm.DmTask(dm.DM_DEVICE_INFO)
        dmt_info.set_name(d[0])
        dmt_info.run()
        info = dmt_info.get_info()
        dm_targets[str(d[1]) + ":" + str(d[2])] = get_dm_info(d[0], info)
    return dm_targets


def get_iostats(block_devices_json):
    stats = dict()
    for device in block_devices_json:
        iostats_data = json.loads(subprocess.run(
            ['iostat', '-o', 'JSON',  '-x', '-N', block_devices_json[device]['path']], stdout=subprocess.PIPE).stdout)
        stats[device] = iostats_data['sysstat']['hosts'][0]['statistics'][0]['disk']

    return stats


def build_json():

    lsblk_data = json.loads(subprocess.run(
        ['lsblk', '--json', '-b', '-O'], stdout=subprocess.PIPE).stdout)
    combined_json = dict()
    block_devices_json = dict()
    children_json = dict()
    filesystems_json = dict()

    block_devices_list = lsblk_data['blockdevices']
    for device in block_devices_list:
        if (not device.get('children') is None):
            get_child_list(device, block_devices_json,
                           children_json, filesystems_json)
        device.pop('children', None)
        get_filesystem_attrs(device, filesystems_json)
        block_devices_json[device['maj:min']] = device.copy()

    dm_targets = get_dm_targets()
    iostats = get_iostats(block_devices_json)
    combined_json = dict(block_devices=block_devices_json,
                         children=children_json,
                         filesystems=filesystems_json,
                         statistics=iostats,
                         devicemapper=dm_targets)

    print(json.dumps(combined_json, indent=2))


build_json()
