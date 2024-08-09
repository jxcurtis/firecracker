#!/bin/bash
# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

while :; do
  [[ -d /sys/devices/system/cpu/cpu$1 ]] && break
done

echo 1 | tee /sys/devices/system/cpu/cpu*/online

/home/hotplug_time.o
