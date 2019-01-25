#!/usr/bin/env python3

import argparse
import json
import os
import urllib.request

LAYERS_FOLDER = 'layers'
MANIFESTS_FOLDER = 'manifests'

class DockerRegistry:
    def __init__(self, url, username=None, password=None):
        self.__url = url
        self.__username = username
        self.__password = password

    def __make_raw_request(self, *args, **kwargs):
        request = urllib.request.Request(*args, **kwargs)
        response = urllib.request.urlopen(request)
        return response

    def __make_binary_request(self, *args, **kwargs):
        response = self.__make_raw_request(*args, **kwargs)
        return response.read()

    def __make_json_request(self, *args, **kwargs):
        response = self.__make_binary_request(*args, **kwargs)
        return json.loads(response)

    def get_all_images(self):
        images = {}

        repos = self.__make_json_request(
            f'{self.__url}/v2/_catalog'
        )['repositories']

        for repo in repos:
            tags = self.__make_json_request(
                f'{self.__url}/v2/{repo}/tags/list'
            )['tags']

            for tag in tags:
                if repo not in images:
                    images[repo] = []
                
                images[repo].append(
                    tag
                )

        return images

    def get_manifest(self, repo, tag):
        return self.__make_json_request(
            f'{self.__url}/v2/{repo}/manifests/{tag}',
            headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
        )

    def get_all_digests(self, repo, tag):
        digests = []
        
        manifest = self.get_manifest(repo, tag)

        for layer in manifest['layers']:
            digests.append(layer['digest'])

        digests.append(
            manifest['config']['digest']
        )

        return digests

    def download_layer(self, repo, digest):
        return self.__make_binary_request(
            f'{self.__url}/v2/{repo}/blobs/{digest}'
        )

    def upload_layer(self, repo, digest, layer_data):
        try:
            response = self.__make_raw_request(
                f'{self.__url}/v2/{repo}/blobs/{digest}',
                method='HEAD'
            )
            if response.status == 200:
                return
        except urllib.error.HTTPError:
            pass

        response = self.__make_raw_request(
            f'{self.__url}/v2/{repo}/blobs/uploads/',
            method='POST'
        )

        query_string = urllib.parse.urlencode(
            {
                'digest': digest
            }
        )

        upload_url = response.info()['Location']

        response = self.__make_raw_request(
            upload_url + '&' + query_string,
            method='PUT',
            headers={
                'Content-Length': len(layer_data),
                'Content-Type': 'application/octet-stream'
            },
            data=layer_data
        )

    def upload_manifest(self, repo, tag, manifest):
        data = json.dumps(manifest, indent=4).encode()
        
        try:
            response = self.__make_raw_request(
                f'{self.__url}/v2/{repo}/manifests/{tag}',
                method='PUT',
                headers={
                    'Content-Type': 'application/vnd.docker.distribution.manifest.v2+json'
                },
                data=data
            )
        except urllib.error.HTTPError as e:
            print(e.file.read())


class DockerRegistryBackup:
    def __init__(self, registry, backup_path):
        self.__registry = registry
        self.__backup_path = backup_path

    def backup(self):
        images = self.__registry.get_all_images()
        layers_path = os.path.join(
            self.__backup_path,
            LAYERS_FOLDER
        )
        os.makedirs(layers_path, exist_ok=True)

        for repo, tags in images.items():
            manifests_path = os.path.join(
                self.__backup_path,
                MANIFESTS_FOLDER,
                repo
            )
            os.makedirs(manifests_path, exist_ok=True)

            for tag in tags:
                manifest = self.__registry.get_manifest(repo, tag)
                with open(os.path.join(manifests_path, tag + '.json'), 'w') as f:
                    json.dump(manifest, f)

                digests = self.__registry.get_all_digests(repo, tag)
                for digest in digests:
                    layer_path = os.path.join(layers_path, digest)
                    if os.path.exists(layer_path):
                        continue

                    with open(layer_path, 'wb') as f:
                        layer_data = self.__registry.download_layer(repo, digest)
                        f.write(layer_data)

    def restore(self):
        layers_path = os.path.join(
            self.__backup_path,
            LAYERS_FOLDER
        )
        manifests_path = os.path.join(
            self.__backup_path,
            MANIFESTS_FOLDER
        )

        for repo in os.listdir(manifests_path):
            repo_path = os.path.join(manifests_path, repo)
            for manifest_name in os.listdir(repo_path):
                tag = manifest_name.rsplit('.', maxsplit=1)[0]
                manifest_path = os.path.join(repo_path, manifest_name)
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

                layers = list(manifest['layers'])
                layers.append(manifest['config']) # make sure we restore the config layer
                for layer in layers:
                    layer_path = os.path.join(layers_path, layer['digest'])
                    with open(layer_path, 'rb') as f:
                        layer_data = f.read()

                    self.__registry.upload_layer(repo, layer['digest'], layer_data)

                self.__registry.upload_manifest(repo, tag, manifest)
            

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()

    group = argparser.add_mutually_exclusive_group(required=True)
    group.add_argument('-b', '--backup', action='store_true')
    group.add_argument('-r', '--restore', action='store_true')

    backup_group = argparser.add_argument_group('backup')
    backup_group.add_argument('-o', '--output', type=str, help='path the backup will be saved to')

    restore_group = argparser.add_argument_group('restore')
    restore_group.add_argument('-s', '--source', type=str, help='path pointing to the backup file we will restore from')

    argparser.add_argument('registry_url')
    args = argparser.parse_args()

    registry = DockerRegistry(args.registry_url)
    backup = DockerRegistryBackup(registry, args.output if args.output else args.source)
    if args.backup:
        backup.backup()
    elif args.restore:
        backup.restore()
