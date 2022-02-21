import boto3
import botocore
import logging
from crhelper import CfnResource

helper = CfnResource()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@helper.create
def create(event, context):
    logger.info("setting up AWS recycle bin")

    client = boto3.client('rbin')

    retention = event['ResourceProperties']['RetentionPeriodValue']
    resource_type = event['ResourceProperties']['ResourceType']

    resource_tags = event['ResourceProperties'].get('ResourceTags')
    description = event['ResourceProperties'].get('Description')
    tags = event['ResourceProperties'].get('Tags')

    rule = {
        'RetentionPeriod': {
            'RetentionPeriodValue': int(retention),
            'RetentionPeriodUnit': 'DAYS'
        },
        'ResourceType': resource_type
    }

    if resource_tags:
        rule['ResourceTags'] = resource_tags

    if description:
        rule['Description'] = description

    if tags:
        rule['Tags'] = tags

    logger.info(f"creating rule with payload: {rule}")

    response = client.create_rule(**rule)

    return response['Identifier']


@helper.update
def update(event, context):
    logger.info(f"updating AWS recycle bin {event['PhysicalResourceId']}")
    aws_account_id = context.invoked_function_arn.split(":")[4]
    region = context.invoked_function_arn.split(":")[3]
    
    client = boto3.client('rbin')

    retention = event['ResourceProperties']['RetentionPeriodValue']
    resource_type = event['ResourceProperties']['ResourceType']

    resource_tags = event['ResourceProperties'].get('ResourceTags')
    description = event['ResourceProperties'].get('Description')
    tags = event['ResourceProperties'].get('Tags', [])

    rule = {
        'Identifier': event['PhysicalResourceId'],
        'RetentionPeriod': {
            'RetentionPeriodValue': int(retention),
            'RetentionPeriodUnit': 'DAYS'
        },
        'ResourceType': resource_type
    }

    if resource_tags:
        rule['ResourceTags'] = resource_tags

    if description:
        rule['Description'] = description

    if tags:
        logger.info(f"updating tags")
        client.tag_resource(
            ResourceArn=f"arn:aws:rbin:{region}:{aws_account_id}:rule/{event['PhysicalResourceId']}",
            Tags=tags
        )

    tag_list = client.list_tags_for_resource(
        ResourceArn=f"arn:aws:rbin:{region}:{aws_account_id}:rule/{event['PhysicalResourceId']}"
    )

    if tag_list['Tags']:
        current_tag_keys = [tag['Key'] for tag in tag_list['Tags']]
        new_tag_keys = [tag['Key'] for tag in tags]

        tags_to_remove = list(set(current_tag_keys) - set(new_tag_keys))

        if tags_to_remove:
            logger.info(f"removing tags {tags_to_remove}")
            client.untag_resource(
                ResourceArn=f"arn:aws:rbin:{region}:{aws_account_id}:rule/{event['PhysicalResourceId']}",
                TagKeys=tags_to_remove
            )

    logger.info(f"updating rule with payload: {rule}")

    client.update_rule(**rule)


@helper.delete
def delete(event, context):
    logger.info(f"deleting AWS recycle bin {event['PhysicalResourceId']}")

    client = boto3.client('rbin')

    try:
        client.delete_rule(
            Identifier=event['PhysicalResourceId']
        )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.info('rule not found, skipping delete')
        else:
            raise error


def lambda_handler(event, context):
    helper(event, context)