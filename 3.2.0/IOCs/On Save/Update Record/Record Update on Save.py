from swimlane_records_updater.SruRecords import Records


recordUpdater = Records(r"D:\SwimlanePython\fixed\config.ini", sw_context.inputs, sw_context.config, proxySet=True, slackNotify=True)
sw_outputs = [recordUpdater.buildSwOutputs('aaSTtpSoZmjPuJtqj', ['Tracking Id', 'Slack TS', 'Slack Channel'], {"RecordExists": "yes"})]
del recordUpdater