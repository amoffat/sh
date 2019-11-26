#!/bin/bash
set -ex
docker run -it --rm -v $(pwd)/../:/home/shtest/sh amoffat/shtest $@
