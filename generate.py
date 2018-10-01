#!/usr/bin/env python
import jinja2
import os
import yaml
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

loader = jinja2.FileSystemLoader(os.getcwd())
jenv = jinja2.Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
hname = os.sys.argv[1]

t20 = jenv.get_template('jinja/dc-leaf.j2')


with open('{}.yml'.format(hname)) as _:
    device = yaml.load(_)
with open('dc1-global.yml') as _:
    global_vars = yaml.load(_)
with open('creds-internal.yml') as _:
    cred_vars = yaml.load(_)


f = open('tmp/pb-junos-diff/{}.gold.text'.format(hname), 'w')
print >> f, t20.render(GLOBAL=global_vars, CREDS=cred_vars, USERINPUT=device)
f.close()

