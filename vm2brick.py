# coding=utf-8
__author__ = 'pcuzner@redhat.com'

# Reference
# http://www.ovirt.org/Python-sdk#Querying_a_collection_using_the_oVirt_search_engine_query_and_custom_constraints:

# Requires:
# - ovirt-engine-sdk-python
# - python-argparse
# - libgfapi python bindings - https://github.com/gluster/libgfapi-python/archive/master.zip

#
# Local changes
# 1. Set USERNAME and PASSWORD

import argparse

import sys

from ovirtsdk.api import API

from glusterfs import gfapi

import time
import threading

# from ovirtsdk.xml import params

# move these to a config module
USERNAME = 'admin@internal'  # must include the domain
PASSWORD = 'redhat'
TARGET = 'localhost'
DEFAULT_PORT = 443


class GlusterVolume(object):

    def __init__(self, domain):
        if args.debug:
            print "creating GlusterVolume instance"
        self.name = domain.get_name()
        self.uuid = domain.get_id()
        self.stg = domain.get_storage()
        # stg.address, stg.path, stg.mount_options
        # Space information stored in bytes
        self.used = domain.get_used()
        self.available = domain.get_available()
        self.size = self.used + self.available
        self.mounted = False
        self.vol = None

    def connect_to_volume(self):
        self.vol = gfapi.Volume(self.stg.address, self.stg.path)
        rc = self.vol.mount()
        if rc == 0:
            self.mounted = True

    def disconnect_volume(self):
        # doesn't do anything, just here to help define the flow
        pass

    def query_placement(self, disk_path):
        if not self.mounted:
            self.connect_to_volume()
        full_path = '/'.join([self.uuid, 'images', disk_path])
        path_info = self.vol.getxattr(full_path, 'trusted.glusterfs.pathinfo', 1024)

        posix = path_info.split('<')
        path_list = ['%s:%s' % (path.split(':')[1], path[6:path.find(')')]) for path in posix if
                     path.startswith('POSIX')]

        return path_list


class Spinner(threading.Thread):

    graphics = [
        "|,/,-,\\"
        ]

    def __init__(self, spinner_type=0, time_delay=0.1):

        self.ptr = 0
        self.delay = time_delay
        self.enabled = True
        self.symbols = Spinner.graphics[spinner_type].split(',')
        self.msg = ''
        threading.Thread.__init__(self)

    def run(self):

        while self.enabled:
            time.sleep(self.delay)
            sys.stdout.write("%s %s %s\n\r\x1b[A" % (self.symbols[self.ptr], self.msg, " "*20))
            if self.ptr < (len(self.symbols) - 1):
                self.ptr += 1
            else:
                self.ptr = 0

    def stop(self):
        self.enabled = False
        self.join()
        sys.stdout.write(" ")


class VMDisk(object):

    def __init__(self, disk):
        if args.debug:
            print "creating a VM disk instance"
        self.disk_name = disk.get_name()
        self.disk_id = disk.get_image_id()
        self.vm_id = disk.get_id()
        sd_group = disk.get_storage_domains()
        sd_list = sd_group.get_storage_domain()
        self.storage_domain_id = sd_list[0].get_id()
        self.brick_path = []

    def __str__(self):
        fmtd = '%-30s\tBrick Path\n' % 'Disk Name'
        if len(self.brick_path) > 0:
            brick_paths = sorted(self.brick_path)
            fmtd += "%-30s\t%s\n" % (self.disk_name, brick_paths[0])
            for replica in brick_paths[1:]:
                fmtd += "%s\t%s\n" % (" "*30, replica)
        else:
            # brick path info is missing for this vdisk?
            fmtd += "%-30s\t%s\n" % (self.disk_name, 'vdisk file is missing or path information is corrupt/invalid')

        return fmtd


def display_results(vm_name, vm_disks, active_host):

    print "\nVM  : %s" % vm_name
    print "Host: %s\n" % active_host
    for disk in sorted(vm_disks):
        print disk


def main():

    gfs_domain = {}
    vm_disks = []

    try:
        if args.debug:
            print "opening api connection to ovirt"
        else:
            # start a spinner
            spinner = Spinner()
            spinner.start()
            pass

        api = API(url='https://%s:%d' % (TARGET, args.port), username=USERNAME, password=PASSWORD, insecure=True)
        # try and get a list of the disks for the vm provided
        if args.debug:
            print "Fetching a list of disks attached to vm '%s'" % args.vm_name

        disks = api.disks.list(query='vm_names = "%s"' % args.vm_name)

        if disks:
            if args.debug:
                print "got the vm disk list ok - %d" % len(disks)
                print "fetching vm details"

            vm_name = args.vm_name

            vm = api.vms.get(name=vm_name)
            if vm.status.state == 'up':
                active_host = api.hosts.get(id=vm.get_host().get_id()).get_name()
            else:
                active_host = 'N/A'

            vm_name += '(%s)' % vm.status.get_state()

            if args.debug:
                print "fetching a list of glusterfs domains"
            domains = api.storagedomains.list(query='type = "glusterfs"')

            for dom in domains:
                new_volume = GlusterVolume(dom)
                gfs_domain[new_volume.uuid] = new_volume

            # process each disk attached to the vm, but only act on disks on a glusterfs domain

            for disk in disks:
                vm_disk = VMDisk(disk)
                if vm_disk.storage_domain_id in gfs_domain:
                    gfs_volume = gfs_domain[vm_disk.storage_domain_id]
                    disk_path = '/'.join([vm_disk.vm_id, vm_disk.disk_id])
                    vm_disk.brick_path = gfs_volume.query_placement(disk_path)

                    vm_disks.append(vm_disk)

        else:
            print "VM doesn't exist, or has no disks"

    except Exception, e:
        print "Unexpected error: %s" % e.message

    finally:

        api.disconnect()
        for uuid in gfs_domain:
            if gfs_domain[uuid].mounted:
                gfs_domain[uuid].disconnect_volume()

        if not args.debug:
            spinner.stop()

        if disks:
            display_results(vm_name, vm_disks, active_host)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='show glusterfs bricks that relate to a given vm')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    parser.add_argument('--vm', dest='vm_name', required=True, help='name of the vm to check')
    parser.add_argument('--port', dest='port', nargs='?', default=DEFAULT_PORT, type=int,
                        help='https port of the ovirt engine (%d)' % DEFAULT_PORT)
    parser.add_argument('--debug', dest='debug', default=False, action='store_true',
                        help='adds diagnostic info to the output')

    args = parser.parse_args()

    main()
