#!/bin/bash
set -ex
docker run -it --rm -v $(pwd)/../:/home/shtest/sh --entrypoint=/bin/bash amoffat/shtest $@
