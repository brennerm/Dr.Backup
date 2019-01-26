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