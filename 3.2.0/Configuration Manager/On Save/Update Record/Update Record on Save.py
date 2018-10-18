from swimlane_records_updater.SruRecords import Records


config_file = '{"Swimlane": { ' \
              '  "host": "host", ' \
              '  "user": "apiUser", ' \
              '  "password": "apiKey" ' \
              ' },' \
              ' "Slack": { ' \
              '  "primaryChannel": "CHANNELID", ' \
              '  "Intgrations1": "Updated CMV1 Record: {}record/{}/{}", ' \
              '  "Intgrations2": "Updated CRM Record: {}record/{}/{}", ' \
              '  "Intgrations3": "Updated IOC Record: {}record/{}/{}", ' \
              '  "Intgrations4": "Pulled LogRythem Event Data: {}record/{}/{}"' \
              ' }' \
              '}'
recordUpdater = Records(config_file, sw_context.inputs, sw_context.config, proxySet=True, slackNotify=True)
sw_outputs = [recordUpdater.buildSwOutputs('aWKxD0xOHM_1WAJoD', ['CFG: Integration Name', 'CFG: Application Name', 'Slack Channel', 'Slack TS'], {"RecordExists": "yes"})]
del recordUpdater
