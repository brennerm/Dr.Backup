## Dr.Backup [![Build Status](https://travis-ci.org/brennerm/Dr.Backup.svg?branch=master)](https://travis-ci.org/brennerm/Dr.Backup)
## Features
- backup  Docker registry
- restore a Docker registry
- no access to the registry's filesystem required
- support for BasicAuth protected registries
- no dependencies

## Usage
```
$ dr-backup --help
usage: dr_backup [-h] (-b | -r) [-o OUTPUT] [-f] [-s SOURCE]
                 [--disable-ssl-verification] [-u USERNAME] [-p PASSWORD]
                 registry_url

positional arguments:
  registry_url

optional arguments:
  -h, --help            show this help message and exit
  -b, --backup
  -r, --restore
  --disable-ssl-verification
                        disable SSL verification (default: False)
  -u USERNAME, --username USERNAME
                        username to authenticate against registry, provide
                        password with -p or you'll be prompted
  -p PASSWORD, --password PASSWORD
                        password to authenticate against registry

backup:
  -o OUTPUT, --output OUTPUT
                        path the backup will be saved to (default:
                        ./${registry_url}_${timestamp})
  -f, --force           force overwrite of existing backup file (default:
                        False)

restore:
  -s SOURCE, --source SOURCE
                        path pointing to the backup file we will restore from
```
### Backup
```
$ dr-backup --backup --output my-old-registry.tar https://my-old-registry.com
[3/3] wordpress [1/1] latest
```
### Restore
```
$ dr-backup --restore --source my-old-registry.tar https://my-new-registry.com
[3/3] wordpress [1/1] latest
```
