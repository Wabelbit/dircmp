#!/usr/bin/python3
import argparse
import sys
from pathlib import Path

is_tty = sys.stdout.isatty()


def cool_print(*args, **kwargs):
    if is_tty:
        print(*args, **kwargs)


processed = 0
total = 0


def main(dir_a: Path, dir_b: Path, recursive: bool, external: bool, follow_symlinks: bool) -> int:
    if not dir_a.is_dir():
        print(f"{dir_a} is not a directory")
        return 2
    if not dir_b.is_dir():
        print(f"{dir_b} is not a directory")
        return 2

    if not is_tty:
        print("Hint: running in script-mode, no progress output will be printed to stdout", file=sys.stderr)

    changes = []
    try:
        cool_print(end="\033[s")
        cmp_dir(changes, dir_a, dir_b, recursive, external, follow_symlinks)
    finally:
        cool_print(end="\033[u")
        print(f"{total} items in total. Found differences:")
        changeset: tuple
        for changeset in changes:
            print(f"{changeset[0]}\t\t{changeset[1]}")

        sys.stdout.flush()


def cmp_dir(changes: list,
            dir_a: Path, dir_b: Path, recursive: bool, external: bool, follow_symlinks: bool):
    global processed, total

    items_a = sorted(dir_a.glob("*"))
    items_b = sorted(dir_b.glob("*"))
    item_names_b = {x.name: x for x in items_b}

    total += len(items_a)

    cool_print(end="\033[u")
    cool_print(f"{processed}/{total}")

    for item_a in items_a:
        processed += 1

        if item_a.name not in item_names_b:
            changes.append((item_a, "deleted"))
            continue
        item_b = item_names_b[item_a.name]
        del item_names_b[item_a.name]

        # compare lstat
        stat_a = item_a.stat(follow_symlinks=follow_symlinks)
        stat_b = item_b.stat(follow_symlinks=follow_symlinks)
        if cmp_prop("stat.st_mode", item_a, stat_a.st_mode, stat_b.st_mode, changes): continue
        if cmp_prop("stat.st_nlink", item_a, stat_a.st_nlink, stat_b.st_nlink, changes): continue
        if cmp_prop("stat.st_uid", item_a, stat_a.st_uid, stat_b.st_uid, changes): continue
        if cmp_prop("stat.st_gid", item_a, stat_a.st_gid, stat_b.st_gid, changes): continue
        if cmp_prop("stat.st_mtime", item_a, stat_a.st_mtime, stat_b.st_mtime, changes): continue

        if item_a.is_symlink():
            if not item_b.is_symlink():
                changes.append((item_a, "is_symlink"))
                continue
            if follow_symlinks and recursive and item_a.is_dir():
                #print("symlink recurse", item_a)
                cmp_dir(changes, item_a, item_b, recursive, external, follow_symlinks)

        if item_a.is_dir():
            if not item_b.is_dir():
                changes.append((item_a, "is_dir"))
                continue
            if recursive and item_a.is_dir():
                #print("recurse", item_a)
                cmp_dir(changes, item_a, item_b, recursive, external, follow_symlinks)

        if item_a.is_mount():
            if not item_b.is_mount():
                changes.append((item_a, "is_mount"))
                continue
            if external:
                #print("mount recurse", item_a)
                cmp_dir(changes, item_a, item_b, recursive, external, follow_symlinks)

        if cmp_prop("is_fifo", item_a, item_a.is_fifo(), item_b.is_fifo(), changes): continue
        if cmp_prop("is_block_device", item_a, item_a.is_block_device(), item_b.is_block_device(), changes): continue
        if cmp_prop("is_char_device", item_a, item_a.is_char_device(), item_b.is_char_device(), changes): continue
        if cmp_prop("is_socket", item_a, item_a.is_socket(), item_b.is_socket(), changes): continue

    for item_b in item_names_b.values():
        changes.append(("missing", item_b))

    return changes


def cmp_prop(prop_name: str, item_a: Path, prop_a, prop_b, changes: list) -> bool:
    if prop_a != prop_b:
        changes.append((item_a, prop_name))
        return True
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Compare directories based on metadata")
    parser.add_argument("dir_a", type=Path, help="First directory")
    parser.add_argument("dir_b", type=Path, help="Second directory")
    parser.add_argument("--recursive", "-r", action="store_true", default=False, help="Recurse into subdirectories")
    parser.add_argument("--external", "-e", action="store_true", default=False, help="Descend into mount points")
    parser.add_argument("--follow-symlinks", "-s", action="store_true", default=False, help="Follow symlinks")
    args = parser.parse_args()
    sys.exit(main(args.dir_a, args.dir_b, args.recursive, args.external, args.follow_symlinks))
