#!/usr/bin/env python3
import os
import json

import aws_cdk as cdk

from cdk.cdk_stack import CdkStack


app = cdk.App()

app_env=os.environ.get("ENV", "dev")

with open('../config/config.json', 'r') as f:
    conf = json.load(f)

env = cdk.Environment(account=conf["aws_account"], region=conf["aws_region"])

CdkStack(app, conf["prefix"]+"CdkStack"+"-"+app_env,
        env=env,
        conf=conf,
        app_env=app_env,
    )

app.synth()
