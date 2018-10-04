#!/usr/bin/env python3
"""[Experimental] Filter domains on subdomains and duplicates

Code to reduce number of entries in blacklist from different sources: remove subdomains and duplicates.
When combining blacklists from different sources, there may be many duplicates and redundant subdomains of parent domains.
Working on some code which filters these efficiently.
"""
import sys

input_domains = [line.rstrip() for line in open("manydomains-shuffled.blacklist")]
length = len(input_domains)
domains = []
counter = 0


def add_domain(new_domain):

    for d in domains:
        # Remove any existing subdomains of new domain
        if d.endswith(new_domain):
            domains.remove(d)
        # Do not append; new domain is duplicate or subdomain of existing domain
        elif new_domain.endswith(d):
            return
    domains.append(new_domain)


for d in input_domains:
    counter += 1
    print('\r{0} of {1}...'.format(counter, length), end='')
    add_domain(d)

with open("manydomains-filtered.blacklist", "w") as out_file:
    out_file.write("\n".join(domains))
