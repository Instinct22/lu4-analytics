#!/bin/sh
set -e

mkdir -p /data/media
cp -a /seed/data/. /data/

exec "$@"
