#!/usr/bin/env python3.6
# encoding: utf-8
'''
'''
import yaml
import requests
import os
import sys
import hashlib
import shutil

# Required for correct utf8 formating on python2
if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

config_file = None
# List to print the used sources as comments in blacklist
used_sources = []


# Load yaml config
def load_config():
    global config_file

    if len(sys.argv) is 2:
        config_file = os.path.abspath(sys.argv[1])
    else:
        sys.exit('Script only accepts a single argument: the config file.')

    try:
        f = open(config_file, 'r')
    except:
        print('Error opening {0}: {1}'.format(config_file, sys.exc_info()[0]))
        sys.exit()

    try:
        yaml_config = yaml.load(f)
    except yaml.YAMLError as exc:
        print("Error in configuration file: {0}".format(exc))
        sys.exit()

    print('Using config file "{}"'.format(config_file))
    return yaml_config


def get_general(config):
    if 'dns-blackhole' in config:
        if 'general' in config['dns-blackhole']:
            if 'whitelist' in config['dns-blackhole']['general'] and config['dns-blackhole']['general']['whitelist'] is not None:
                whitelist = config['dns-blackhole']['general']['whitelist']
            else:
                whitelist = os.path.dirname(config_file) + '/whitelist'

            if 'blacklist' in config['dns-blackhole']['general'] and config['dns-blackhole']['general']['blacklist'] is not None:
                blacklist = config['dns-blackhole']['general']['blacklist']
            else:
                blacklist = os.path.dirname(config_file) + '/blacklist'
        else:
            print('Missing general section in config file')
            sys.exit()
    else:
        print('Cannot find dns-blackhole section in config file.')
        sys.exit()

    return whitelist, blacklist


def get_service(config):
    if 'dns-blackhole' in config:
        if 'config' in config['dns-blackhole']:
            zone_file = config['dns-blackhole']['config']['zone_file']
            zone_file_dir = config['dns-blackhole']['config']['zone_file_dir']
            zone_data = config['dns-blackhole']['config']['zone_data']
            lists = config['dns-blackhole']['config']['blackhole_lists']
            if 'prefix' in config['dns-blackhole']['config']:
                prefix = config['dns-blackhole']['config']['prefix']
            else:
                prefix = ""
            if 'suffix' in config['dns-blackhole']['config']:
                suffix = config['dns-blackhole']['config']['suffix']
            else:
                suffix = ""
        else:
            print('Cannot find "config" section in config file.')
            sys.exit()
    else:
        print('Cannot find dns-blackhole section in config file.')
        sys.exit()

    return zone_file, zone_file_dir, zone_data, lists, prefix, suffix


def process_host_file_url(bh_list, white_list, host_file_urls):
    for url in host_file_urls:
        try:
            print('[!] Fetch and parse URL: {0}'.format(url))
            r = requests.get(url)
        except:
            sys.exit('Request to {0} failed: {1}'.format(url, sys.exc_info()[0]))

        if r.status_code != 200:
            sys.exit('Incorrect return code from {0}: {1}.'.format(url, r.status_code))
        else:
            used_sources.append(r.url)
            for line in r.iter_lines():
                try:
                    # If utf8 decode fails jumps next item
                    line = line.decode('utf-8')
                except:
                    continue

                if line.startswith('127.0.0.1') or line.startswith('0.0.0.0'):
                    # Remove ip
                    try:
                        n_host = line.split('127.0.0.1')[1]
                    except IndexError:
                        n_host = line.split('0.0.0.0')[1]
                    except:
                        continue

                    # Fix some host lists having \t instead of space
                    if n_host.startswith('\t'):
                        n_host = n_host.lstrip('\t')

                    # Ensure we only keep host as some list add comments
                    n_host = n_host.split('#')[0].rstrip()
                    # Some leave ports
                    n_host = n_host.split(':')[0]
                    # Some leave spaces prefixed
                    n_host = n_host.replace(' ', '')
                    # Some put caps
                    n_host = n_host.lower()

                    # Remove local domains
                    if n_host == 'localhost.localdomain' or n_host == 'localhost':
                        continue

                    # Ignore empty string
                    if n_host == '':
                        continue

                    # Now add the hosts to the list
                    if n_host not in white_list:
                        bh_list.append(n_host[::-1])

    return bh_list


def process_easylist_url(bh_list, white_list, easy_list_url):
    for url in easy_list_url:
        try:
            print('[!] Fetch and parse URL: {0}'.format(url))
            r = requests.get(url)
        except:
            sys.exit('Request to {0} failed: {1}.'.format(url, sys.exc_info()[0]))

        if r.status_code != 200:
            sys.exit('Incorrect return code from {0}: {1}.'.format(url, r.status_code))
        else:
            used_sources.append(r.url)
            for line in r.iter_lines():
                try:
                    # If utf8 decode fails jumps next item
                    line = line.decode('utf-8')
                except:
                    continue

                if line.startswith('||'):
                    # I don't want to bother with wildcards
                    if '*' in line:
                        continue

                    # Keep domain
                    try:
                        n_host = line.split('^')[0]
                    except:
                        continue

                    # and get rid of those '$'
                    try:
                        n_host = n_host.split('$')[0]
                    except IndexError:
                        pass

                    # Remove leading '||'
                    n_host = n_host.lstrip('||')

                    # Some entries are urls
                    if '/' in n_host:
                        n_host = n_host.split('/')[0]

                    # Some entries are no domains...
                    if '.' not in n_host:
                        continue

                    # Some leave a final '.'
                    n_host = n_host.rstrip('.')

                    # Some put caps
                    n_host = n_host.lower()

                    # ignore empty string
                    if n_host == '':
                        continue

                    # Now add the hosts to the list
                    if n_host not in white_list:
                        bh_list.append(n_host[::-1])
    return bh_list


def process_disconnect_url(bh_list, white_list, d_url, d_cat):
    try:
        print('[!] Fetch and parse URL: {0}'.format(d_url))
        r = requests.get(d_url)
    except:
        print('Request to {0} failed: {1}'.format(d_url, sys.exc_info()[0]))
        sys.exit()

    if r.status_code == 200:
        try:
            j = r.json()
        except:
            print('Seems like we did not fetch a json dict')
            sys.exit()
    else:
        print('Incorrect return code from {0}: {1}. Zonefile not created.'.format(d_url, r.status_code))
        sys.exit(1)

    used_sources.append(r.url)
    if 'categories' in j:
        for category in j['categories']:
            if category in d_cat:
                for sub_dict in j['categories'][category]:
                    for entity in sub_dict:
                        for main_url in sub_dict[entity]:
                            h_list = sub_dict[entity][main_url]
                            if isinstance(h_list, list):
                                for host in h_list:
                                    if host == '':
                                        continue
                                    if host not in white_list:
                                        bh_list.append(host[::-1])
    else:
        print('"categories" key not found in dict, nothing to process')
        return bh_list
    return bh_list


def process_black_list(bh_list, black_list):
    for bl_host in black_list:
        bh_list.append(bl_host[::-1])

    return bh_list


def build_bw_lists(bh_whitelist, bh_blacklist):
    white_list = []
    black_list = []
    w = None
    b = None

    # Open whitelist
    try:
        w = open(bh_whitelist, 'r')
    except:
        print('Cannot open {0}: {1}'.format(bh_whitelist, sys.exc_info()[0]))

    # Open blacklist
    try:
        b = open(bh_blacklist, 'r')
    except:
        print('Cannot open {0}: {1}'.format(bh_blacklist, sys.exc_info()[0]))

    if w:
        for line in w.readlines():
            # Ignore comments
            if not line.startswith('#'):
                # If there's a comment after the domain
                if '#' in line:
                    white_list.append(line.split('#')[0].strip())
                else:
                    # Ignore empty lines
                    if not line.strip() == '':
                        white_list.append(line.strip())

    if b:
        for line in b.readlines():
            # Ignore comments
            if not line.startswith('#'):
                # If there's a comment after the domain
                if '#' in line:
                    black_list.append(line.split('#')[0].strip())
                else:
                    # Ignore empty lines
                    if not line.strip() == '':
                        black_list.append(line.strip())
    if white_list:
        print('Using {0} domains from whitelist "{1}"'.format(len(white_list), bh_whitelist))
        used_sources.append("Custom local whitelist")
    if black_list:
        print('Using {0} domains from blacklist "{1}"'.format(len(black_list), bh_blacklist))
        used_sources.append("Custom local blacklist")
    return white_list, black_list


def make_zone_file(bh_list, zone_file, zone_file_dir, zone_data, prefix, suffix):
    f = open(zone_file, 'w')

    # First print all sources as comments
    f.write("# Sources: \n")
    used_sources_commented = ["# " + u for u in used_sources]
    f.write(("\n").join(used_sources_commented))
    f.write("\n")

    # Define Unbound specific view:
    # f.write("view:    \nname: blacklistview\n")
    if prefix:
        f.write(prefix)

    # Un-reverse all elements
    bh_list = [d[::-1] for d in bh_list]

    # Sort and remove duplicates
    bh_list = sorted(list(set(bh_list)))

    for d in bh_list:
        f.write(zone_data.format(**{'domain': d}) + "\n")

    if suffix:
        f.write(suffix)
    f.close()

    # Create checksum file and move blacklistview and checksum file to specified dir
    open(zone_file + ".checksum", "w").write(sha256sum(zone_file))
    shutil.move(os.path.abspath(zone_file), zone_file_dir + zone_file)
    shutil.move(os.path.abspath(zone_file + ".checksum"), zone_file_dir +
                zone_file + ".checksum")
    print("Saved zone file to " + zone_file_dir + zone_file)


def remove_subdomains(bh_list):
    bh_list.sort()
    bh_list_filtered = ["dummy_element"]
    for d in bh_list:
        # Only add d to new list if d does not start with last element in new list
        if not d.find(bh_list_filtered[-1]) == 0:
            bh_list_filtered.append(d)
        # else:
        #     print("{0} starts with last element {1}".format(d, bh_list_filtered[-1]))

    # Remove dummy_element
    del bh_list_filtered[0]
    return bh_list_filtered


def sha256sum(filename):
    h = hashlib.sha256()
    with open(filename, 'rb', buffering=0) as f:
        for b in iter(lambda: f.read(128 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    # Get config as dict from yaml file
    config = load_config()

    # Get general settings
    bh_white, bh_black = get_general(config)

    # Get service config
    zone_file, zone_file_dir, zone_data, lists, prefix, suffix = get_service(config)

    # Build whitelist/blacklist
    white_list, black_list = build_bw_lists(bh_white, bh_black)

    # Now populate bh_list based on our config
    bh_list = []

    # First process host files if set
    if 'hosts' in lists:
        bh_list = process_host_file_url(bh_list, white_list, lists['hosts'])

    # Then easylist
    if 'easylist' in lists:
        bh_list = process_easylist_url(bh_list, white_list, lists['easylist'])

    # Finally disconnect
    if 'disconnect' in lists:
        d_url = lists['disconnect']['url']
        d_cat = lists['disconnect']['categories']
        bh_list = process_disconnect_url(bh_list,
                                         white_list,
                                         d_url,
                                         d_cat)

    # bh_list = [line.rstrip()[::-1] for line in open("10-domains.blacklist")]

    # Add hosts from blacklist
    bh_list = process_black_list(bh_list, black_list)

    # Remove subdomains
    bh_list = remove_subdomains(bh_list)

    # Create pdns file
    make_zone_file(bh_list, zone_file, zone_file_dir, zone_data, prefix, suffix)


if __name__ == "__main__":
    main()
