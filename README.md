# junos config compliance

#### The goal

To be able to validate that our switches are running a standard config. If not, generate a config file to correct for missing lines or remove lines that should not be there. Use an ansible playbook to compare the "golden config" to the device's committed config and build set/delete remediation. This example uses a source golden config that only contains the system and snmp top level sections.

1. Generate a junos config (stanza format) based on standard jinja2 template using device personality parameters. This is the golden config.
2. Pull existing config from each device
3. Convert the device config to .set using a very useful tool called [junoser](https://github.com/codeout/junoser) by - Shintaro Kojima
4. Take the generated golden config, load it on the device, pull the candidate config and rollback 0    **1 notes on why we do this below
5. Convert the candidate config to .set
6. Diff the two .set configs, which are now both aligned to common formatting, and produce the remediation script

Next steps will be to provide a way for a human to "OK" the change for initial runs and subsequent playbook task to push the change.

Ultimately, I want to create a better way to handle the comparison. I'd rather use a json output to do the diff since it would be well structured, but there are a few things I need to get past in order to be able to do this. Mainly, the source template to use for comparison and the task of figuring out how to build the set/delete actions for cleanup.


**1 - the reason we need to load the config on the device and then grab the candidate for conversion/comparison is the way Junos handles quotation. For instance:

```
ansible@dc1-leaf1a# set interfaces ge-0/0/0 description "test server one"

{master:0}[edit]
ansible@dc1-leaf1a# set interfaces ge-0/0/1 description "test-server-two"

ansible@dc1-leaf1a# show interfaces
ge-0/0/0 {
    description "test server one";
}
ge-0/0/1 {
    description test-server-two;
}
```

You see that if there is no need to quote the description, it leaves it off in the config. In my templates, I have to use quotes in event that the description will contain spaces/etc. So this leaves me with the golden config containing quotes where the device config may not. Difficult to compare (with my current python experience). I see difflib may have a way to handling this with junk characters... but with unified_diff I don't know if this will work. More to try later... as I really don't want to push a config to the device

A note on why I'm using an external tool to convert to .set format. In step 4, the playbook pushes a golden config, using load override which means we need to use the junos stanza format. At that same task, I also pull the candidate config. The juniper_junos_config module allows you to define the format, but I can't use .set for the retrieve step since the format also affects the load operation... they conflict.  So, to solve for this, I just load override, pull the candidate and then convert using junoser. Since I do the same for the device config, the .set outputs are produced in a consistent manner.

Another reason to use only the junoser output is the difference in the schema conversion. Notice the lines are split.
```
 ### example display set from the junos cli
 set system ntp authentication-key 1 type md5
 set system ntp authentication-key 1 value "$9$zopTn9t1RSM87uO87-V4oz369uO"

 ### example display set from junoser
 set system ntp authentication-key 1 type md5 value "$9$zopTn9t1RSM87uO87-V4oz369uO"

```
### NOTE: 
since we need to sort the lines in order to get a clean diff, this messes with the order of firewall entries. This will break anything that needs to be applied in a specific order. My suggestions, if you use this tool, is to only use this to get an idea of what's missing. Perhaps we evaluate firewall, route policies, etc.. in a different way. I'll try to think of another way to deal with this.

#### Example playbook run
```
ansible@control:~/projects/diff$ ansible-playbook pb-junos-diff.yml

PLAY [Juniper compliance check] ******************************************************************************************

TASK [Clean diff directory] **********************************************************************************************
changed: [dc1-leaf1b -> localhost]
ok: [dc1-leaf1a -> localhost]

TASK [Create diff directory] *********************************************************************************************
changed: [dc1-leaf1a -> localhost]
ok: [dc1-leaf1b -> localhost]

TASK [generate] **********************************************************************************************************
changed: [dc1-leaf1a -> localhost]
changed: [dc1-leaf1b -> localhost]

TASK [convert golden config to set format] *******************************************************************************
changed: [dc1-leaf1a -> localhost]
changed: [dc1-leaf1b -> localhost]

TASK [saving existing config from remote device to compare] **************************************************************
ok: [dc1-leaf1b]
ok: [dc1-leaf1a]

TASK [convert device config to set format] *******************************************************************************
changed: [dc1-leaf1a -> localhost]
changed: [dc1-leaf1b -> localhost]

TASK [saving temporarily loaded config from device] **********************************************************************
changed: [dc1-leaf1a]
changed: [dc1-leaf1b]

TASK [convert golden config to set format] *******************************************************************************
changed: [dc1-leaf1a -> localhost]
changed: [dc1-leaf1b -> localhost]

PLAY [compare] ***********************************************************************************************************

TASK [script] ************************************************************************************************************
changed: [dc1-leaf1a -> localhost]
changed: [dc1-leaf1b -> localhost]

TASK [debug] *************************************************************************************************************
ok: [dc1-leaf1a] => {
    "msg": [
        "set system domain-name arpthis.net",
        "delete system domain-name arpthis.org",
        "set system name-server 8.8.4.4",
        "delete system name-server 8.8.3.3",
        "set system login message \"\\n\\n\\n\\t       * * *  W A R N I N G  * * *\\n\\tProperty of the ABC CORP\\n\\nIf you are not authorized to access this system, disconnect now.\\nUsers of this system have no expectation of privacy. By continuing,\\nyou consent to your keystrokes and data content being monitored.\\n\\n\"",
        "set system ntp server 10.23.250.1 key 1",
        "delete system ntp server 1.1.1.1",
        "delete snmp community secondbadpassword",
        "delete snmp community \"abcv2@#$asdf\""
    ]
}
ok: [dc1-leaf1b] => {
    "msg": [
        "set system login message \"\\n\\n\\n\\t       * * *  W A R N I N G  * * *\\n\\tProperty of the ABC CORP\\n\\nIf you are not authorized to access this system, disconnect now.\\nUsers of this system have no expectation of privacy. By continuing,\\nyou consent to your keystrokes and data content being monitored.\\n\\n\"",
        "delete system ntp server 2.2.2.2"
    ]
}

PLAY [compare - output to files] *****************************************************************************************

TASK [script] ************************************************************************************************************
changed: [dc1-leaf1a -> localhost]
changed: [dc1-leaf1b -> localhost]

PLAY RECAP ***************************************************************************************************************
dc1-leaf1a                 : ok=11   changed=8    unreachable=0    failed=0
dc1-leaf1b                 : ok=11   changed=8    unreachable=0    failed=0
```

#### example raw diff without set/delete conversion
```
commented out the following in junos-diff.py
#        elif line.strip().startswith('-set'):
#            line = line.replace('-set','set')
#        elif line.strip().startswith('+set'):
#            line = line.replace('+set','delete')
```
```
ansible@control:~/projects/diff$ ./junos-diff.py ./tmp/pb-junos-diff/dc1-leaf1a.gold.set ./tmp/pb-junos-diff/dc1-leaf1a.device.set
-set system domain-name arpthis.net
+set system domain-name arpthis.org
-set system name-server 8.8.4.4
+set system name-server 8.8.3.3
-set system login message "\n\n\n\t       * * *  W A R N I N G  * * *\n\tProperty of the ABC CORP\n\nIf you are not authorized to access this system, disconnect now.\nUsers of this system have no expectation of privacy. By continuing,\nyou consent to your keystrokes and data content being monitored.\n\n"
-set system ntp server 10.23.250.1 key 1
+set system ntp server 1.1.1.1
+set snmp community secondbadpassword
+set snmp community "abcv2@#$asdf"
```

#### notes for later/cleanup:
* clean up playbook, local_action/delegate
* need to handle stripping certain items from comparison (example: don't compare snmpv3 user credentials... the key always changes per device)

# lots of testing still needed, fyi
