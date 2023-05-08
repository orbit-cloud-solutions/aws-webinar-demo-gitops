#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.cicd_stack import CiCdStack


app = cdk.App()


conf = app.node.try_get_context(key="config")
env = cdk.Environment(account=conf["aws_account"], region=conf["aws_region"])

CiCdStack(app, conf["prefix"]+"CiCdStack",
        env=env,
        conf=conf,
    )

app.synth()
