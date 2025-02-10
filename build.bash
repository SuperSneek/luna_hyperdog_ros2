#!/usr/bin/env bash

if ! [[ "$_" == "$0" ]] ; then
   echo "I'm not meant to be sourced - run me!"
   # return and not exit when sourced
   return 1
fi

# change to ws dir
cd $(dirname "$0")

# make sure ros is sourced in this bash env
source /opt/ros/rolling/setup.bash

# add args as packages
PACKAGES="$1"
if [ -n "$PACKAGES" ]; then
  PACKAGES="--packages-select ${PACKAGES}"
fi

colcon build --symlink-install --executor sequential --cmake-args --no-warn-unused-cli -DBUILD_TESTING=0 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON $PACKAGES
