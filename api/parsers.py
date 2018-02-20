import json
from os.path import join, dirname
from jsonschema import validate


prospect_schema = {
    'type': 'object',
    'properties': {
        'Name': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 30
        },
        'Addr1': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 30
        },
        'Addr2': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 30
        },
        'Addr3': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 30
        },
        'Addr4': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 30
        },
        'Pcode': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 10
        },
        'Tel': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 20
        },
        'Email': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 50
        },
    },
    'required': [
        'Pcode', 'Email', 'Tel', 'Name', 'Addr1'
    ],
    'additionalProperties': False
}

policy_schema = {
    'type': 'object',
    'properties': {
        'Ptype': {
            'type': 'string',
            'minLength': 2,
            'maxLength': 2
        },
        'Ref': {
            'type': 'string',
            'minLength': 7,
            'maxLength': 7
        },
        'Risk': {
            'type': 'object',
            'properties': {
                'CLT1': {
                    'type': 'object',
                    'properties': {
                        'indem.yn': {'enum': ['yes', 'no']},
                    },
                    'required': [
                        'indem.yn'
                    ],
                    'additionalProperties': False
                }
            },
            'required': [
                'CLT1'
            ],
            'additionalProperties': False
        }
    },
    'required': [
        'Ref', 'Ptype'
    ],
    'additionalProperties': False
}

transaction_schema = {
    'type': 'object',
    'properties': {
        'Polref': {
            'type': 'string',
            'minLength': 11,
            'maxLength': 11
        }
    }
}