import os
import re
import json
import base64
import logging
import argparse

import boto3
from truffleHogRegexes.regexChecks import regexes as hogRegexes


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
logger.addHandler(handler)


SESSION = boto3.session.Session()


def define_params():

    global SESSION
    parser = argparse.ArgumentParser()
    parser.add_argument('-profile', required=True,
                        help='profile to use for AWS access.')
    parser.add_argument('-output', default='output.txt',
                        help='path / name of output file.')
    args = parser.parse_args()
    SESSION = boto3.session.Session(profile_name=args.profile)
    return args


def get_all_regions():

    logger.info('Fetching AWS regions...')
    client = SESSION.client('ec2')
    regions = [
        x['RegionName'] for x in
        (client.describe_regions() or dict()).get(
            'Regions', list()) if x.get('RegionName')]

    logger.info('  [%02d] regions fetched.', len(regions))
    logger.info(str())
    return regions


def get_instances(client):

    instances = [
        {
            'id': instance[0].get('InstanceId'),
            'type': instance[0].get('InstanceType')
        } for instance in
        [
            reserve.get('Instances', list()) for reserve in
            (client.describe_instances(MaxResults=999) or dict())
            .get('Reservations', list())
        ]
    ]
    logger.info('  [%02d] instances fetched.', len(instances))
    return instances


def populate_userdata(client, instances):

    for instance in instances:
        userdata = (client.describe_instance_attribute(
            Attribute='userData', InstanceId=instance.get('id')) or dict()) \
            .get('UserData', dict())

        if userdata:
            logger.info('    [%d] values found for <%s>.',
                        len(userdata), instance.get('id'))
        instance['userdata'] = userdata

    return instances


def check_regexes(instances):

    if instances:
        logger.info('  Checking userdata values against regexes...')

    hogRegexes['Generic Password'] = re.compile('[A-Za-z0-9+_-]{20,255}')
    for instance in instances:
        if not instance.get('userdata'):
            continue

        matches = dict()
        for key, value in instance['userdata'].items():
            value = base64.b64decode(value).decode('utf8')
            for name, regex in hogRegexes.items():
                search = regex.search(value)
                if search:
                    matches['match'] = search.group()
                    try:
                        matches['value'] = json.loads(value)
                    except json.JSONDecodeError:
                        matches['value'] = value

                    logger.info(
                        '    Matched: %s', value[:20] + '...'
                        if len(value) > 20 else value)
                    break
            if matches:
                instance['matches'] = matches
                break

    return instances


def write_matches(args, instances, region):

    if instances:
        logger.info('  Writing matches to file...')

    data = list()
    for instance in instances:
        matches = instance.get('matches')
        if not matches:
            continue

        entry = {'id': instance.get('id')}
        entry.update(matches)
        data.append(entry)

    if not os.path.isfile(args.output):
        open(args.output, 'w')

    if data:
        try:
            content = json.load(open(args.output))
        except json.JSONDecodeError:
            content = dict()

        content[region] = data
        json.dump(content, open(args.output, 'w'), indent=2)
        logger.info('  [%s] file updated.', args.output)
    logger.info(str())


def process_region(args, region):

    logger.info('Fetching details from <%s>.', region)
    client = SESSION.client('ec2', region_name=region)
    instances = get_instances(client)
    populate_userdata(client, instances)
    check_regexes(instances)
    write_matches(args, instances, region)
    return instances


if __name__ == "__main__":

    args = define_params()
    regions = get_all_regions()

    data = list()
    for region in regions:
        process_region(args, region)
