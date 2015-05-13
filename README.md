# vm2brick

## Overview
This is a command line tool to show the relationships between the virtual disks of a vm, and the corresponding glusterfs bricks. The tool is installed on the ovirt engine machine/vm which allows the relationships to be queried for active and inactive virtual machines.  

'vm2brick' queries ovirt and glusterfs through their respective API interfaces, keeping the code as minimal as possible.

## Installation  
To install the tool there are several pre-requisite packages that need to be installed.  

1. glusterfs-api  
2. ovirt-engine-sdk-python 
3. python-argparse (not installed by default on RHEL)
4. python-libgfapi module  

Items 1-3 are packages available in either the OS repo, or ovirt's. Item 4 however, is a python module that you'll need to download from github and install mannually.  

* Download the libgfapi module from https://github.com/gluster/libgfapi-python  
* unzip the archive
* install the module with  


    python setup.py install  

* test the module by opening a python console and attempting to import the gfapi module


    python  
    from glusterfs import gfapi  


## Usage
At the moment, before you can use the tool you need to update the USERNAME and PASSWORD global variables in vm2brick.py to match your ovirt environment.  

Here's a few examples that show the tool being used;  


    python vm2brick.py -h  
    usage: vm2brick.py [-h] [--version] --vm VM_NAME [--port [PORT]] [--debug] 
 
    show glusterfs bricks that relate to a given vm  

    optional arguments:  
    -h, --help     show this help message and exit  
    --version      show program's version number and exit  
    --vm VM_NAME   name of the vm to check  
    --port [PORT]  https port of the ovirt engine (443)  
    --debug        adds diagnostic info to the output  


And a run to show how the data is presented;  

    python vm2brick.py --vm fio-clone-1  

    VM  : fio-clone-1(down)
    Host: None
    
    Disk Name                     	Brick Path
    rh7-guest1_Disk1              	gprfc087.sbu.lab.eng.bos.redhat.com:/glusterfs/brick1/vmdomain
                                  	gprfc086.sbu.lab.eng.bos.redhat.com:/glusterfs/brick1/vmdomain
                                  	gprfc085.sbu.lab.eng.bos.redhat.com:/glusterfs/brick1/vmdomain  

