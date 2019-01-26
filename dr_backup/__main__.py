#!/usr/bin/env python3

import argparse
import getpass
import json
import os
import ssl
import urllib.request

LAYERS_FOLDER = 'layers'
MANIFESTS_FOLDER = 'manifests'

class DockerRegistry:
    def __init__(self, url, username=None, password=None, disable_ssl_verification=False):
        self.__url = url

        if username and password:
            DockerRegistry.__install_basic_auth_handler(url, username, password)

        if disable_ssl_verification:
            ssl._create_default_https_context = ssl._create_unverified_context

    @staticmethod
    def __install_basic_auth_handler(url, username, password):
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, username, password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)

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
            self.__make_raw_request(
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
        repos_n = len(images)

        layers_path = os.path.join(
            self.__backup_path,
            LAYERS_FOLDER
        )
        os.makedirs(layers_path, exist_ok=True)

        for i, (repo, tags) in enumerate(images.items(), 1):
            tags_n = len(tags)
            manifests_path = os.path.join(
                self.__backup_path,
                MANIFESTS_FOLDER,
                repo
            )
            os.makedirs(manifests_path, exist_ok=True)

            for j, tag in enumerate(tags, 1):
                print(f'\r\033[K[{i}/{repos_n}] {repo} [{j}/{tags_n}] {tag}', end='') # \033[K ANSI escape character that erases to end of line

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

        repos = os.listdir(manifests_path)
        repos_n = len(repos)
        for i, repo in enumerate(repos, 1):
            repo_path = os.path.join(manifests_path, repo)
            manifest_names = os.listdir(repo_path)
            tags_n = len(manifest_names)

            for j, manifest_name in enumerate(manifest_names, 1):
                tag = manifest_name.rsplit('.', maxsplit=1)[0]
                print(f'\r\033[K[{i}/{repos_n}] {repo} [{j}/{tags_n}] {tag}', end='') # \033[K ANSI escape character that erases to end of line

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


def main():
    argparser = argparse.ArgumentParser()

    group = argparser.add_mutually_exclusive_group(required=True)
    group.add_argument('-b', '--backup', action='store_true')
    group.add_argument('-r', '--restore', action='store_true')

    backup_group = argparser.add_argument_group('backup')
    backup_group.add_argument('-o', '--output', type=str, help='path the backup will be saved to')

    restore_group = argparser.add_argument_group('restore')
    restore_group.add_argument('-s', '--source', type=str, help='path pointing to the backup file we will restore from')

    argparser.add_argument('--disable-ssl-verification', action='store_true', help="disable SSL verification (default: False)")
    argparser.add_argument('-u', '--username', help="username to authenticate against registry, provide password with -p or you'll be prompted")
    argparser.add_argument('-p', '--password', help="password to authenticate against registry")
    argparser.add_argument('registry_url')
    args = argparser.parse_args()

    if args.restore and args.source is None:
        argparser.error('--source is required when restoring')

    if args.username and args.password is None:
        args.password = getpass.getpass()

    registry = DockerRegistry(args.registry_url, args.username, args.password, args.disable_ssl_verification)
    backup = DockerRegistryBackup(registry, args.output if args.output else args.source)
    if args.backup:
        backup.backup()
    elif args.restore:
        backup.restore()



if __name__ == "__main__":
    main()