# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

FROM python:3.10
MAINTAINER "KernelCI TSC" <kernelci-tsc@groups.io>

# Upgrade pip3 - never mind the warning about running this as root
RUN pip3 install --upgrade pip

RUN useradd kernelci -u 1000 -d /home/kernelci -s /bin/bash
RUN mkdir -p /home/kernelci
RUN chown kernelci: /home/kernelci
USER kernelci
ENV PATH=$PATH:/home/kernelci/.local/bin
WORKDIR /home/kernelci

# Install kcidb
RUN pip install git+https://github.com/kernelci/kcidb.git

# Install kernelci-core from pinned revision:
# kernelci/data/kernelci_api: add KernelCI_API.get_nodes_by_commit_hash
RUN pip install git+https://github.com/kernelci/kernelci-core.git@\
2d59832553cefa603b2129da8ee6efceddfe3ef7
