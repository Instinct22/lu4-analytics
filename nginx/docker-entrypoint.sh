#!/bin/sh
set -e

cp -a /seed/data/wiki /data/
cp -a /seed/data/datasets /data/
cp -a /seed/data/raid-bosses /data/

exec "$@"
