#!/usr/bin/env python3
"""[Experimental] Filter domains on subdomains and duplicates

Code to reduce number of entries in blacklist from different sources: remove subdomains and duplicates.
When combining blacklists from different sources, there may be many duplicates and redundant subdomains of parent domains.
Working on some code which filters these efficiently.
"""

from random import shuffle
import sys

input_domains = [line.rstrip() for line in open("manydomains.blacklist")]
domains = []
shuffle(input_domains)


# Check if domain is subdomain of existing domain
# Remove any subdomains of domain to be added
def add_domain(new_domain):

    # Only for first domain in list
    if not domains:
        domains.append(new_domain)
        return

    for d in domains:
        if d.endswith(new_domain):
            # print("{1} -> {0}".format(new_domain, d))
            domains.remove(d)
        elif new_domain.endswith(d):
            if new_domain == d:
                print("Skipping duplicate {0}".format(new_domain))
                return
            else:
                # print("New domain {0} is subdomain of {1}, so skipping {0}.".format(new_domain, d))
                return
    domains.append(new_domain)


counter = 0
length = len(input_domains)

for d in input_domains:
    counter += 1
    print('\r{0} of {1}...'.format(counter, length), end='')
    add_domain(d)

with open("manydomains-filtered.blacklist", "w") as out_file:
    out_file.write("\n".join(domains))
