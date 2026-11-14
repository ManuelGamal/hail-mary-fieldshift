"""Robust Kaggle kernel-output downloader (resumable, paginated, pattern filter).

Usage: KAGGLE_API_TOKEN=... python pipeline/kaggle_fetch.py <owner/kernel> <out_dir> [regex] [--list]
The stock `kaggle kernels output` reads each file in one request with no retry and ignores pagination.
"""

import os
import re
import subprocess
import sys

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import (
    ApiListKernelSessionOutputRequest,
)


def list_outputs(api, owner, slug):
    files, log, token = [], None, None
    with api.build_kaggle_client() as k:
        while True:
            req = ApiListKernelSessionOutputRequest()
            req.user_name, req.kernel_slug = owner, slug
            if token:
                req.page_token = token
            r = k.kernels.kernels_api_client.list_kernel_session_output(req)
            files += [(f.file_name, f.url) for f in r.files]
            log = log or r.log
            token = r.next_page_token
            if not token:
                break
    return files, log


def main():
    kernel, out = sys.argv[1], sys.argv[2]
    pat = (
        re.compile(sys.argv[3])
        if len(sys.argv) > 3 and not sys.argv[3].startswith("--")
        else None
    )
    owner, slug = kernel.split("/")
    api = KaggleApi()
    api.authenticate()
    files, log = list_outputs(api, owner, slug)
    if "--list" in sys.argv:
        for n, _ in files:
            print(n)
        return 0
    os.makedirs(out, exist_ok=True)
    if log:
        open(os.path.join(out, slug + ".log"), "w", encoding="utf-8").write(log)
    bad = 0
    for name, url in files:
        if pat and not pat.search(name):
            continue
        dst = os.path.join(out, name)
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        rc = subprocess.run(
            [
                "curl",
                "-sS",
                "-L",
                "--retry",
                "8",
                "--retry-all-errors",
                "--retry-delay",
                "3",
                "-C",
                "-",
                "-o",
                dst,
                url,
            ]
        ).returncode
        if rc not in (0, 33):  # 33 = range not satisfiable (already complete)
            bad += 1
            print("FAILED", name, rc)
        else:
            print("ok", name, os.path.getsize(dst))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
