#!/usr/bin/env python3
#
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Maryam Yusuf
# Author: Maryam Yusuf <maryam.m.yusuf1802@gmail.com>
import datetime
import os
import sys

import kernelci
import kernelci.data
from kernelci.config import load
from kernelci.cli import Args, Command, parse_opts
from kcidb import Client
import kcidb


class cmd_run(Command):
    help = "Listen for events and send them to KCDIB"
    args = [Args.db_config]

    def __call__(self, configs, args):
        db_config = configs['db_configs'][args.db_config]
        api_token = os.getenv('API_TOKEN')
        db = kernelci.data.get_db(db_config, api_token)

        project_id = os.getenv('KCIDB_PROJECT_ID')
        topic_name = os.getenv('KCIDB_TOPIC_NAME')
        google_credential = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        client = None

        if topic_name and project_id:
            client = Client(project_id=project_id,
                            topic_name=topic_name)

        print("Listening for events... ")
        print("Press Ctrl-C to stop.")
        sys.stdout.flush()
        if not client or not google_credential:
            print("Aborting due to missing configuration")
            sys.stdout.flush()
            return

        sub_id = db.subscribe('node')
        try:
            while True:
                event = db.get_event(sub_id)
                node = db.get_node_from_event(event)
                if node['name'] != 'checkout':
                    continue
                print(f"Printing node for {node}")
                sys.stdout.flush()
                print("Submitting node to KCIDB")
                sys.stdout.flush()

                created_time = datetime.datetime.fromisoformat(node["created"])
                tz_utc = datetime.timezone(datetime.timedelta(hours=0))
                if not created_time.tzinfo:
                    created_time = datetime.datetime.\
                        fromtimestamp(created_time.timestamp(), tz=tz_utc)
                start_time = created_time.isoformat()
                revision = {
                        "builds": [],
                        "checkouts": [
                            {
                                "id": f"kernelci:{node['_id']}",
                                "origin": "kernelci",
                                "tree_name": node["revision"]["tree"],
                                "git_repository_url": node["revision"]["url"],
                                "git_commit_hash": node["revision"]["commit"],
                                "git_repository_branch":
                                    node["revision"]["branch"],
                                "start_time": start_time
                            },
                        ],
                        "tests": [],
                        "version": {
                            "major": 4,
                            "minor": 0
                        }
                    }
                self.send_revision(client, revision)

            sys.stdout.flush()

        except KeyboardInterrupt:
            print("Stopping.")
        finally:
            db.unsubscribe(sub_id)

        sys.stdout.flush()

    def send_revision(self, client, revision):
        if self.validate_revision(revision):
            return client.submit(revision)
        print(f"Aborting, invalid data")
        sys.stdout.flush()

    @staticmethod
    def validate_revision(revision):
        return kcidb.io.SCHEMA.is_valid(revision)


if __name__ == '__main__':
    opts = parse_opts('runner', globals())
    configs = kernelci.config.load('config/pipeline.yaml')
    status = opts.command(configs, opts)
    sys.exit(0 if status is True else 1)
