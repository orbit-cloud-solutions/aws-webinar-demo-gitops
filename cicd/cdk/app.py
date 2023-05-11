#!/usr/bin/env python3
import json

import aws_cdk as cdk

from cdk.cicd_stack import CiCdStack


app = cdk.App()


with open('../../config/config.json', 'r') as f:
    conf = json.load(f)

env = cdk.Environment(account=conf["aws_account"], region=conf["aws_region"])

CiCdStack(app, conf["prefix"]+"CiCdStack",
        env=env,
        conf=conf,
    )

app.synth()
