import os
import re
import json
import base64
import logging
import argparse

from multiprocessing import Pipe, Process

import boto3
from botocore.exceptions import ClientError
from truffleHogRegexes.regexChecks import regexes as hogRegexes


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s: %(message)s'))
logger.addHandler(handler)


SESSION = boto3.session.Session()
hogRegexes['Generic Password'] = re.compile('[A-Za-z0-9+-]{40,255}')


class _ClientError(Exception):
    pass


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
            'type': instance[0].get('InstanceType'),
            'state': instance[0].get('State', dict()).get('Name', str())
        } for instance in
        [
            reserve.get('Instances', list()) for reserve in
            (client.describe_instances(Filters=[{
                'Name': 'instance-state-name',
                'Values': ['running', 'stopped']
            }], MaxResults=999) or dict())
            .get('Reservations', list())
        ]
    ]
    logger.info('  [%d] instances fetched.', len(instances))
    return instances


def populate_userdata(client, instances):

    for instance in instances:
        try:
            userdata = (client.describe_instance_attribute(
                Attribute='userData', InstanceId=instance.get(
                    'id')) or dict()).get('UserData', dict())

            if userdata:
                logger.info('    [%d] values found for <%s>.',
                            len(userdata), instance.get('id'))
                instance['userdata'] = userdata
        except ClientError as exc:
            if 'InvalidInstanceID.NotFound' not in str(exc):
                raise _ClientError(str(exc))


def populate_tags(client, instances):

    logger.info('  Populating resource tags...')
    tags = (client.describe_tags(
        MaxResults=1000) or dict()).get('Tags', list())

    count = 0
    for instance in instances:
        for tag in tags:
            if not tag.get('ResourceId') == instance.get('id'):
                continue
            instance['name'] = tag.get('Value')
            count += 1
    logger.info('    [%d] tags populated.', count)


def get_templates(client):

    templates = [
        {
            'id': x.get('LaunchTemplateId'),
            'name': x.get('LaunchTemplateName'),
            'created_by': x.get('CreatedBy')
        } for x in (client.describe_launch_templates(
            MaxResults=200) or dict()).get('LaunchTemplates', list())]

    logger.info('  [%d] templates listed.', len(templates))
    return templates


def populate_templates(client, templates):

    for template in templates:
        versions = [
            {
                'number': x.get('VersionNumber'),
                'description': x.get('VersionDescription'),
                'data': x.get('LaunchTemplateData', dict())
            } for x in (client.describe_launch_template_versions(
                LaunchTemplateId=template.get('id'), MaxResults=200) or dict())
            .get('LaunchTemplateVersions', list())]

        logger.info('\t[%d] version found for <%s>', len(
            versions), template.get('id'))

        for version in versions:
            if version['data'].get('UserData'):
                version['data']['UserData'] = base64.b64decode(
                    version['data']['UserData']).decode('utf8')

            content = json.dumps(version['data'])
            for name, regex in hogRegexes.items():
                search = regex.search(content)
                if search:
                    if template.get('matches'):
                        template['matches'].append({
                            'version': version.get('number'), 
                            'match': search.group()
                        })
                    else:
                        template['matches'] = [{
                            'version': version.get('number'),
                            'match': search.group()
                        }]
                    logger.info(
                        '\t  Matched: %s', search.group()[:20] + '...'
                        if len(search.group()) > 20 else search.group())


def check_regexes(instances):

    if instances:
        logger.info('  Checking userdata values against regexes...')

    for instance in instances:
        if not instance.get('userdata'):
            continue

        matches = dict()
        for key, value in instance['userdata'].items():
            value = base64.b64decode(value).decode('utf8')
            for name, regex in hogRegexes.items():
                search = regex.search(value)
                if search:
                    if instance.get('matches'):
                        instance['matches'].append({key: search.group()})
                    else:
                        instance['matches'] = [{key: search.group()}]
                    try:
                        instance[key] = json.loads(value)
                    except json.JSONDecodeError:
                        instance[key] = value
                    logger.info(
                        '\tMatched: %s', search.group()[:20] + '...'
                        if len(search.group()) > 20 else search.group())
                    break

            instance.pop('userdata')
    return instances


def write_matches(args, data, region):

    for entry in data.copy():
        if not entry.get('matches'):
            data.remove(entry)

    if not data:
        return

    logger.info('  Writing matches to file...')
    if not os.path.isfile(args.output):
        open(args.output, 'w')

    try:
        content = json.load(open(args.output))
    except json.JSONDecodeError:
        content = dict()

    if content.get(region):
        content[region].extend(data)
    else:
        content[region] = data

    json.dump(content, open(args.output, 'w'), indent=2)
    logger.info('  [%s] file updated.', args.output)
    logger.info(str())


def process_region(args, region, pchild):

    logger.info('Fetching details from <%s>.', region)
    client = SESSION.client('ec2', region_name=region)
    instances = get_instances(client)
    populate_userdata(client, instances)
    populate_tags(client, instances)

    check_regexes(instances)
    write_matches(args, instances, region)

    templates = get_templates(client)
    populate_templates(client, templates)
    write_matches(args, templates, region)


if __name__ == "__main__":

    args = define_params()
    regions = get_all_regions()
    if os.path.isfile(args.output):
        open(args.output, 'w')

    conns, processes = list(), list()
    for region in regions:
        parent, child = Pipe()
        process = Process(target=process_region, args=(args, region, child))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()
