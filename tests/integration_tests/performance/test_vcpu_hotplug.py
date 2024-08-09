# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Testing hotplug performance"""

import platform
import re
import time
from pathlib import Path

import pandas
import pytest

from framework.utils_iperf import IPerf3Test, emit_iperf3_metrics
from host_tools.cargo_build import gcc_compile
from host_tools.fcmetrics import FCMetricsMonitor


@pytest.mark.skipif(
    platform.machine() != "x86_64", reason="Hotplug only enabled on x86_64."
)
@pytest.mark.parametrize(
    "vcpu_count", [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
)
def test_custom_udev_rule_latency(
    microvm_factory, guest_kernel_linux_acpi_only, rootfs_rw, vcpu_count, results_dir
):
    """Test the latency for hotplugging and booting CPUs in the guest"""
    gcc_compile(Path("./host_tools/hotplug_time.c"), Path("host_tools/hotplug_time.o"))
    data = []
    for i in range(50):
        uvm_hotplug = microvm_factory.build(guest_kernel_linux_acpi_only, rootfs_rw)
        uvm_hotplug.jailer.extra_args.update({"boot-timer": None, "no-seccomp": None})
        uvm_hotplug.help.enable_console()
        uvm_hotplug.spawn()
        uvm_hotplug.basic_config(vcpu_count=1, mem_size_mib=128)
        uvm_hotplug.add_net_iface()
        uvm_hotplug.start()
        uvm_hotplug.ssh.scp_put(
            Path("./host_tools/hotplug_udev.sh"), Path("/home/hotplug_udev.sh")
        )
        uvm_hotplug.ssh.scp_put(
            Path("./host_tools/hotplug_time.o"), Path("/home/hotplug_time.o")
        )
        uvm_hotplug.ssh.scp_put(
            Path("./host_tools/1-cpu-hotplug.rules"),
            Path("/usr/lib/udev/rules.d/1-cpu-hotplug.rules"),
        )
        uvm_hotplug.ssh.run(
            f"udevadm control --reload-rules && tmux new-session -d /bin/bash /home/hotplug_udev.sh {vcpu_count}"
        )

        uvm_hotplug.api.hotplug.put(Vcpu={"add": vcpu_count})
        time.sleep(2)

        # Extract API call duration
        api_duration = (
            float(
                re.findall(
                    r"Total previous API call duration: (\d+) us\.",
                    uvm_hotplug.log_data,
                )[-1]
            )
            / 1000
        )
        try:
            timestamp = (
                float(
                    re.findall(
                        r"Guest-boot-time\s+\=\s+(\d+)\s+us", uvm_hotplug.log_data
                    )[0]
                )
                / 1000
            )
        except IndexError:
            timestamp = None

        data.append({"vcpus": vcpu_count, "api": api_duration, "onlining": timestamp})

    output_file = results_dir / f"hotplug-{vcpu_count}.csv"

    csv_data = pandas.DataFrame.from_dict(data).to_csv(
        index=False,
        float_format="%.3f",
    )

    output_file.write_text(csv_data)


@pytest.mark.skipif(
    platform.machine() != "x86_64", reason="Hotplug only enabled on x86_64."
)
@pytest.mark.parametrize(
    "vcpu_count", [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
)
def test_manual_latency(
    microvm_factory, guest_kernel_linux_acpi_only, rootfs_rw, vcpu_count
):
    """Test the latency for hotplugging and booting CPUs in the guest"""
    gcc_compile(Path("./host_tools/hotplug_time.c"), Path("host_tools/hotplug_time.o"))
    data = []
    for _ in range(50):
        uvm_hotplug = microvm_factory.build(guest_kernel_linux_acpi_only, rootfs_rw)
        uvm_hotplug.jailer.extra_args.update({"boot-timer": None, "no-seccomp": None})
        uvm_hotplug.help.enable_console()
        uvm_hotplug.spawn()
        uvm_hotplug.basic_config(vcpu_count=1, mem_size_mib=128)
        uvm_hotplug.add_net_iface()
        uvm_hotplug.start()
        uvm_hotplug.ssh.scp_put(
            Path("./host_tools/hotplug.sh"), Path("/home/hotplug.sh")
        )
        uvm_hotplug.ssh.scp_put(
            Path("./host_tools/hotplug_time.o"), Path("/home/hotplug_time.o")
        )
        uvm_hotplug.ssh.run("tmux new-session -d /bin/bash /home/hotplug.sh")

        uvm_hotplug.api.hotplug.put(Vcpu={"add": vcpu_count})

        time.sleep(1.5)
        # Extract API call duration
        api_duration = (
            float(
                re.findall(
                    r"Total previous API call duration: (\d+) us\.",
                    uvm_hotplug.log_data,
                )[-1]
            )
            / 1000
        )
        try:
            timestamp = (
                float(
                    re.findall(
                        r"Guest-boot-time\s+\=\s+(\d+)\s+us", uvm_hotplug.log_data
                    )[0]
                )
                / 1000
            )
        except IndexError:
            data.append({"vcpus": vcpu_count, "api": api_duration, "onlining": None})
            continue

        data.append({"vcpus": vcpu_count, "api": api_duration, "onlining": timestamp})

    df = pandas.DataFrame.from_dict(data).to_csv(
        f"../test_results/manual-hotplug_{vcpu_count}.csv",
        index=False,
        float_format="%.3f",
    )

    output_file.write_text(csv_data)
