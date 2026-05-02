from config import server_api_url, server_auth_key
from server_actions import client
from server_actions.responses import *
from aiohttp import ClientError


async def annotate(link, **kwargs):
    try:
        async with client.session.post(
            f'{server_api_url}/pool/annotate_video',
            json = { 'link': link, **kwargs },
            headers = { 'Cookie': f'uid={server_auth_key}' }
        ) as response:
            if not response.ok:
                text = await response.text()
                raise APIError(f'Annotation failure: {response.status} - {text}')

            body = await response.json()
            return AnnotationResponse(**body)

    except ClientError as e:
        raise APIError(f'Request error: {e}')


async def whitelist(link, value: bool = True):
    return await annotate(link, whitelisted=value)


async def set_eligibility(link, eligibility, reason=None):
    if eligibility == 'default':
        return await annotate(link, eligibility='default')

    return await annotate(link, eligibility=eligibility, reason=reason)


async def set_reupload(reupload_link, original_link):
    try:
        async with client.session.post(
            f'{server_api_url}/pool/set_reupload',
            json = { 'reupload_link': reupload_link, 'original_link': original_link },
            headers = { 'Cookie': f'uid={server_auth_key}' }
        ) as response:
            if not response.ok:
                text = await response.text()
                raise APIError(f'Failure: {response.status} - {text}')

            body = await response.json()
            return SetReuploadResponse(**body)

    except ClientError as e:
        raise APIError(f'Request error: {e}')


async def get_video_data(link):
    try:
        async with client.session.post(
            f'{server_api_url}/ballot/validate?all_data=true',
            json = { 'link': link }
        ) as response:
            if not response.ok:
                text = await response.text()
                raise APIError(f'Validation failure: {response.status} - {text}')

            response = await response.json()

            # Allowing possible KeyErrors since a result only matters if video data is present
            video_data = response['video_data']
            video_data['annotations'] = response['field_flags']

            return video_data

    except ClientError as e:
        raise APIError(f'Request error: {e}')
