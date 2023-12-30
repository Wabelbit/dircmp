#!/usr/bin/python3
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from stat import S_ISDIR, S_ISLNK, S_ISSOCK, S_ISBLK, S_ISCHR, S_ISFIFO


RESTORE_CURSOR = "\033[u"
STORE_CURSOR = "\033[s"
GREY = "\033[0;90m"
RED = "\033[0;31m"
ORANGE = "\033[0;33m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;93m"
NO_COLOUR = "\033[0m"

is_tty = sys.stdout.isatty()


def tty_print(*args, **kwargs):
    if is_tty:
        print(*args, **kwargs)


def rethrow(ex: Optional[BaseException]):
    if ex is not None:
        print()
        sys.stdout.flush()
        raise ex


processed = 0
total = 0


def main(dir_a: Path, dir_b: Path, recursive: bool, external: bool, follow_symlinks: bool, output: Optional[Path]) -> int:
    if not dir_a.is_dir():
        print(f"{dir_a} is not a directory", file=sys.stderr)
        return 2
    if not dir_b.is_dir():
        print(f"{dir_b} is not a directory", file=sys.stderr)
        return 2

    if not is_tty:
        print("Hint: running in script-mode, no progress output will be printed to stdout", file=sys.stderr)

    changes = []
    ex = None
    try:
        tty_print(end=STORE_CURSOR)
        cmp_dir(changes, dir_a, dir_b, recursive, external, follow_symlinks)
    except BaseException as e:
        ex = e
        tty_print(end=RESTORE_CURSOR)
        tty_print(end=ORANGE)
        print(f"Warning: search aborted by {type(ex).__name__}, results will be incomplete!")
        tty_print(end=NO_COLOUR)
        sys.stdout.flush()

        print(ex, file=sys.stderr)
        sys.stderr.flush()
    else:
        tty_print(end=RESTORE_CURSOR)
    finally:
        if processed == total:
            tty_print(end=GREEN)
        else:
            tty_print(end=YELLOW)
        print(f"Processed {processed} of {total} found items.", end=' ')

        # check for results
        if len(changes) == 0:
            print()
            tty_print(end=GREEN)
            print("No differences discovered, directory contents seem superficially identical.")
            tty_print(end=NO_COLOUR)
            rethrow(ex)
            return 0

        # print differences
        tty_print(end=YELLOW)
        print(f"Discovered {len(changes)} difference{'' if len(changes) == 1 else 's'}:")
        tty_print(end=NO_COLOUR)
        print()
        changeset: tuple
        for changeset in changes:
            print(f"{changeset[0]}\t\t{changeset[1]}")
        print()

        # save differences in file, if requested
        if output:
            print(f"Writing results to '{output}'...", end=' ')
            with output.open("w", encoding="UTF-8") as f:
                json.dump(changes, f, ensure_ascii=False, indent=2)
                print(file=f)
            print("Done.")

        rethrow(ex)


def cmp_dir(changes: list,
            dir_a: Path, dir_b: Path, recursive: bool, external: bool, follow_symlinks: bool,
            recursion_depth: int = 0):
    global processed, total

    ex_a = None
    ex_b = None
    try:
        items_a = sorted(dir_a.iterdir())
    except Exception as e:
        ex_a = type(e).__name__
        items_a = []
        tty_print(end=RED)
        print(f"Failed to list '{dir_a}' due to {ex_a}")
        tty_print(end=NO_COLOUR)

    try:
        items_b = sorted(dir_b.iterdir())
    except Exception as e:
        ex_b = type(e).__name__
        items_b = []
        tty_print(end=RED)
        print(f"Failed to list '{dir_b}' due to {ex_b}")
        tty_print(end=NO_COLOUR)

    if ex_a != ex_b:
        append_change(changes, dir_a, f"{ex_a} & {ex_b}")
        return

    item_names_b = {x.name: x for x in items_b}
    total += len(items_a)

    # print progress
    tty_print(end=RESTORE_CURSOR)
    tty_print(f"{GREY}Searching {len(items_a)} ({processed}/{total}), depth {recursion_depth}, discovered {len(changes)}{NO_COLOUR}", end=' ')
    if is_tty and len(items_a) >= 1000:
        # make sure our status update is on-screen if the search could take a while
        sys.stdout.flush()

    # match items in B-list to items in A-list
    for item_a in items_a:
        processed += 1

        if item_a.name not in item_names_b:
            append_change(changes, item_a, "deleted")
            continue
        item_b = item_names_b[item_a.name]
        del item_names_b[item_a.name]

        # handle symlinks
        stat_a = item_a.stat(follow_symlinks=False)
        stat_b = item_b.stat(follow_symlinks=False)
        if S_ISLNK(stat_a.st_mode):
            # check if B is also a symlink
            if not S_ISLNK(stat_b.st_mode):
                append_change(changes, item_a, "is_symlink")
                continue

            # do not escape out of original search-path
            if follow_symlinks:
                if not str(item_a.resolve()).startswith(str(dir_a)):
                    print(f"Absolute symlink at {item_a} points outside of searched filesystem, refusing to follow")
                else:
                    # resolve symlink
                    stat_a = item_a.stat(follow_symlinks=True)
                    stat_b = item_b.stat(follow_symlinks=True)

        # handle subdirectories
        if S_ISDIR(stat_a.st_mode):
            if not S_ISDIR(stat_b.st_mode):
                append_change(changes, item_a, "is_dir")
                continue
            if recursive:
                # run comparison for this subdirectory
                #print("recurse", item_a)
                cmp_dir(changes, item_a, item_b, recursive, external, follow_symlinks, recursion_depth + 1)
        else:
            # compare file size only for files, not folders, because different filesystem drivers
            # have different understandings of what 'size' is on directories, which makes it incomparable
            if cmp_prop("stat.st_size", item_a, stat_a.st_size, stat_b.st_size, changes): continue

        # compare some more relevant metadata
        if cmp_prop("stat.st_uid", item_a, stat_a.st_uid, stat_b.st_uid, changes): continue
        if cmp_prop("stat.st_gid", item_a, stat_a.st_gid, stat_b.st_gid, changes): continue
        if cmp_prop("stat.st_mtime", item_a, stat_a.st_mtime, stat_b.st_mtime, changes): continue

        # handle mount-points
        if item_a.is_mount():
            if not item_b.is_mount():
                append_change(changes, item_a, "is_mount")
                continue
            # this didn't really work well and also doesn't really make sense for what we're trying to achieve...
            #if external:
            #    #print("mount recurse", item_a)
            #    cmp_dir(changes, item_a, item_b, recursive, external, follow_symlinks, recursion_depth + 1)

        # compare less relevant modes
        if cmp_prop("is_fifo", item_a, S_ISFIFO(stat_a.st_mode), S_ISFIFO(stat_b.st_mode), changes): continue
        if cmp_prop("is_block_device", item_a, S_ISBLK(stat_a.st_mode), S_ISBLK(stat_b.st_mode), changes): continue
        if cmp_prop("is_char_device", item_a, S_ISCHR(stat_a.st_mode), S_ISCHR(stat_b.st_mode), changes): continue
        if cmp_prop("is_socket", item_a, S_ISSOCK(stat_a.st_mode), S_ISSOCK(stat_b.st_mode), changes): continue

        # catch other modes
        if cmp_prop("stat.st_mode", item_a, stat_a.st_mode, stat_b.st_mode, changes): continue

    # anything left over in the item_names_b array is something that doesn't exist in dir_a (reverse difference)
    for item_b in item_names_b.values():
        changes.append(("missing", str(item_b)))

    return changes


def append_change(changes: list, item_a: Path, prop_name: str):
    path_a = str(item_a)
    if item_a.is_dir():
        path_a += os.sep
    changes.append((path_a, prop_name))


def cmp_prop(prop_name: str, item_a: Path, prop_a, prop_b, changes: list) -> bool:
    if prop_a != prop_b:
        append_change(changes, item_a, prop_name + f"({prop_a}|{prop_b})")
        return True
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Compare directories based on metadata")
    parser.add_argument("dir_a", type=Path, help="First directory")
    parser.add_argument("dir_b", type=Path, help="Second directory")
    parser.add_argument("--recursive", "-r", action="store_true", default=False, help="Recurse into subdirectories")
    #parser.add_argument("--external", "-e", action="store_true", default=False, help="Descend into mount points")
    parser.add_argument("--follow-symlinks", "-s", action="store_true", default=False, help="Follow symlinks")
    parser.add_argument("--output", "-o", type=Path, help="Results output file (JSON format). Useful if many differences are expected")
    args = parser.parse_args()
    sys.exit(main(args.dir_a, args.dir_b, args.recursive, False, args.follow_symlinks, args.output))
