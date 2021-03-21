#!/usr/bin/env python3

import os
import sys
import pathlib
import logging
import argparse
from fnmatch import fnmatch
from contextlib import suppress
from subprocess import check_output as yld, DEVNULL

from common import YAML

log = logging.getLogger(__name__)


def build_kustomization(path):
    # XXX: We use the following extra flags for kustomize:
    # `load_restrictor`: Allow loading files outside of the root folder of the
    # kustomization.
    return yld(["kustomize", "build", "--load_restrictor", "none", path],
               stderr=DEVNULL)


def find_kustomizations(path, overlay=None, include_patterns=["*"],
                        exclude_patterns=[]):
    """Find all kustomization files in given directory."""
    kustomizations = []
    for root, _, files in os.walk(path):
        if "kustomization.yaml" in files:
            kname = os.path.basename(root)
            if overlay and kname != overlay:
                continue
            included = False
            for include_pattern in include_patterns:
                if fnmatch(pathlib.PurePath(root).relative_to(path), include_pattern):
                    included = True
            if not included:
                continue
            for exclude_pattern in exclude_patterns:
                if fnmatch(pathlib.PurePath(root).relative_to(path), exclude_pattern):
                    continue
            kustomizations.append(root)

    return kustomizations


def parse_args():
    parser = argparse.ArgumentParser()
    default_root_path = "."
    with suppress(Exception):
        repo_path = yld(["git", "rev-parse", "--show-toplevel"])
        default_root_path = repo_path.decode("utf-8").strip()

    print(default_root_path)
    parser.add_argument("--root-path", type=str, default=default_root_path,
                        help="Root path to search for kustomizations.")
    parser.add_argument("--include-patterns", nargs="+", default=["*"],
                        help="Path patterns to include.")
    parser.add_argument("--exclude-patterns", nargs="+", default=["*"],
                        help="Path patterns to exclude.")
    return parser.parse_args()


def main():
    # Detect kustomizations
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    kustomizations = find_kustomizations(
        args.root_path, include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns)

    errors = []
    for kust in kustomizations:
        try:
            build_kustomization(kust)
        except Exception as e:
            errors.append(e)
            log.error("Failed to build kustomization `%s`: %s",
                      pathlib.PurePath(kust).relative_to(args.root_path), e)
            continue
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
