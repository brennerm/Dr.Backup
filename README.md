## Dr.Backup [![Build Status](https://travis-ci.org/brennerm/Dr.Backup.svg?branch=master)](https://travis-ci.org/brennerm/Dr.Backup)
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
