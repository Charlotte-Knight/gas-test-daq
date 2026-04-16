#!/bin/bash

# this script is used to backup the database to vols
# is ran as a cron job from one of the lx machines
# 47 * * * * /vols/dune/mdk16/TestStand/backup_db.sh

TMP=$(ssh teststand "mktemp /tmp/db_backup_XXXXXX.db")
backup_cmd="sqlite3 -cmd \"PRAGMA busy_timeout=5000\" /home/mdk16/gas-test-daq/daq.db \".backup '$TMP'\""
#echo $backup_cmd
ssh teststand $backup_cmd > /dev/null
rsync -az teststand:$TMP /vols/dune/mdk16/TestStand/daq.db
ssh teststand "rm $TMP"
