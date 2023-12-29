# dircmp
_Directory comparison commandline tool_

## Usage
```
usage: dircmp [-h] [--recursive] [--follow-symlinks] [--output OUTPUT] dir_a dir_b

Compare directories based on metadata

positional arguments:
dir_a                 First directory
dir_b                 Second directory

options:
-h, --help            show this help message and exit
--recursive, -r       Recurse into subdirectories
--follow-symlinks, -s
                      Follow symlinks
--output OUTPUT, -o OUTPUT
                      Results output file (JSON format). Useful if many differences are expected
```
Example invocation: `python3 dircomp.py -r ~/first_folder ~/second_folder`

Be careful with `--follow-symlinks`: if you encounter `FileNotFoundError`, you should remove that option.
In any case it will however refuse to follow symlinks which point outside the original search directory.

## What is this and why?

Honestly this is just a dirty little script I threw together because I needed a quick way of checking whether two directories are roughly in sync.

No guarantees about reliability/correctness of results.
