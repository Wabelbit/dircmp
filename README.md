# dircmp
_Directory comparison commandline tool_

## Usage
```
usage: dircmp.py [-h] [--recursive] [--external] [--follow-symlinks] dir_a dir_b

Compare directories based on metadata

positional arguments:
  dir_a                 First directory
  dir_b                 Second directory

options:
  -h, --help            show this help message and exit
  --recursive, -r       Recurse into subdirectories
  --external, -e        Descend into mount points
  --follow-symlinks, -s
                        Follow symlinks
```
You probably want all the options most of the time, e.g. `dircomp.py -res ~/first_folder ~/second_folder` will do.

Be careful with `--follow-symlinks` though: if you encounter `FileNotFoundError`, you should remove that option.

## Why?

Honestly this is just a dirty little script I threw together because I needed a quick way of checking whether two directories are roughly in sync.

No guarantees about reliability/correctness of results.
