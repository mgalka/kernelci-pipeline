#!/usr/bin/env python3
#
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Maryam Yusuf
# Author: Maryam Yusuf <maryam.m.yusuf1802@gmail.com>
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""KCIDB bridge service"""

import datetime
import sys

import kernelci
import kernelci.db
import kernelci.config
from kernelci.cli import Args, Command, parse_opts
from kcidb import Client
import kcidb

from base import Service


class KCIDBBridge(Service):
    def __init__(self, configs, args, name):
        super().__init__(configs, args, name)

    def _setup(self, args):
        return {
            'client': Client(
                project_id=args.kcidb_project_id,
                topic_name=args.kcidb_topic_name
            ),
            'sub_id': self._db.subscribe_node_channel(filters={
                'name': 'checkout',
                'state': 'done',
            }),
            'origin': args.origin,
        }

    def _stop(self, context):
        if context['sub_id']:
            self._db.unsubscribe(context['sub_id'])

    def _send_revision(self, client, revision):
        if kcidb.io.SCHEMA.is_valid(revision):
            return client.submit(revision)
        self.log.error("Aborting, invalid data")

    @staticmethod
    def _set_timezone(created_timestamp):
        created_time = datetime.datetime.fromisoformat(created_timestamp)
        if not created_time.tzinfo:
            tz_utc = datetime.timezone(datetime.timedelta(hours=0))
            created_time = datetime.datetime.fromtimestamp(
                created_time.timestamp(), tz=tz_utc)
        return created_time.isoformat()

    def _run(self, context):
        self.log.info("Listening for events... ")
        self.log.info("Press Ctrl-C to stop.")

        while True:
            node = self._db.receive_node(context['sub_id'])
            self.log.info(f"Submitting node to KCIDB: {node['_id']}")

            revision = {
                'builds': [],
                'checkouts': [
                    {
                        'id': f"{context['origin']}:{node['_id']}",
                        'origin': context['origin'],
                        'tree_name': node['revision']['tree'],
                        'git_repository_url': node['revision']['url'],
                        'git_commit_hash': node['revision']['commit'],
                        'git_repository_branch': node['revision']['branch'],
                        'start_time': self._set_timezone(node['created']),
                        'patchset_hash': '',
                        'misc': {
                            'submitted_by': 'kernelci-pipeline'
                        },
                    }
                ],
                'tests': [],
                'version': {
                    'major': 4,
                    'minor': 0
                }
            }
            self._send_revision(context['client'], revision)
        return True


class cmd_run(Command):
    help = "Listen for events and send them to KCDIB"
    args = [
        Args.db_config,
        {
            'name': '--kcidb-topic-name',
            'help': "KCIDB topic name",
        },
        {
            'name': '--kcidb-project-id',
            'help': "KCIDB project ID",
        },
        {
            'name': '--origin',
            'help': "CI system identifier",
        },
    ]

    def __call__(self, configs, args):
        return KCIDBBridge(configs, args, 'send_kcidb').run(args)


if __name__ == '__main__':
    opts = parse_opts('send_kcidb', globals())
    configs = kernelci.config.load('config/pipeline.yaml')
    status = opts.command(configs, opts)
    sys.exit(0 if status is True else 1)
