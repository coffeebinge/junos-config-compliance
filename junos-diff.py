#!/usr/bin/env python
import difflib
import sys
import os

gold_config = os.sys.argv[1]
device_config = os.sys.argv[2]


with open('{}'.format(gold_config)) as gold:
    lines1 = gold.readlines()
with open('{}'.format(device_config)) as device:
    lines2 = device.readlines()

for line in difflib.unified_diff(lines1, lines2, fromfile='file1', tofile='file2', lineterm='', n=0):
    for prefix in ('---', '+++', '@@', '#'):
        if line.startswith(prefix):
            break
        elif line.strip().startswith('-set snmp v3 usm'):
            break
        elif line.strip().startswith('+set snmp v3 usm'):
            break
        elif line.strip().startswith('-set'):
            line = line.replace('-set','set')
        elif line.strip().startswith('+set'):
            line = line.replace('+set','delete')
            
    else:
        print line,
#    else:
#        print line,


#####
## need to ignore "set version x.x.x" in configs, use another method to verify correct junos version
## need to handle deactivated sections of code... if deactivated, throw warning to intervene
## need to present a message saying  "device in compliance statement" and have follow up 
##   ansible playbook play take that message and stop moving forward
## later, add in collection of device config so that if we ever use apply-groups, we include
##   the "display inheritence" extra bits so items are not lost. (if needed??-- jinja will likely present the same data)
## will need to deal with strings being quoted in jinja output vs not quoted in junos config output
## ***WILL also need to deal with delete then set order
## *** also, need to exclude snmp v3 users since the stored key will always be different
