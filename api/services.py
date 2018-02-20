import xmltodict
from django.conf import settings
import logging
from jsonschema import validate
import copy
import zeep
from enum import Enum


logger = logging.getLogger(__name__)


class ResultStatus(Enum):
    SUCCESS = ''
    FAILURE = ''


class Result:
    def __init__(self, data=None, status=ResultStatus.FAILURE):
        self.data = data
        self.status = status.name  # type: ResultStatus.name
        self.message = status.value  # type: ResultStatus.value


class XStreamParser:
    """
    Entry point for parsing json(dict) data into a valid XStream schema
    """
    def __init__(self):
        self.template = copy.deepcopy(XSTREAM_TEMPLATE)

    def add_apm(self, json: dict):
        self.template['xmlexecute']['apmdata']['prospect']['p.cm'] = json

    def add_policy_type(self, policy_type: str):
        self.template['xmlexecute']['apmpolicy']['p.py']['Ptype'] = policy_type

    def add_risk_data(self, risk_data: dict):
        for k, v in risk_data.items():
            self.template['xmlexecute']['apmpolicy'][k] = v

    def add_polref(self, polref: str):
        self.template['xmlexecute']['apmpolicy']['p.py']['Polref'] = polref

    def add_ref(self, ref: str):
        self.add_apm({'Refno': ref})

    def add_function_type(self, function_type: str):
        self.template['xmlexecute']['parameters']['yzt']['char20.1'] = function_type

    def parse_to_xml(self):
        parsed_dict = xmltodict.unparse(self.template, full_document=False)
        return parsed_dict


def validate_json(json: dict, schema: dict):
    is_validated = False
    try:
        validate(json, schema)
        is_validated = True
    except Exception as e:
        print(e)
    return is_validated


def create_prospect(prospect_json: dict) -> Result:
    prospect_parser = XStreamParser()
    prospect_parser.add_apm(prospect_json)
    prospect_parser.add_function_type('create-cliv-prospect')
    prospect_xml = prospect_parser.parse_to_xml()
    result = SoapService.process_message(prospect_xml)
    return  result


def add_policy(policy_json: dict):
    policy_parser = XStreamParser()
    policy_parser.add_ref(policy_json['Ref'])
    policy_parser.add_policy_type(policy_json['Ptype'])
    policy_parser.add_risk_data(policy_json['Risk'])
    policy_parser.add_function_type('create-cliv-policy')
    policy_xml = policy_parser.parse_to_xml()
    result = SoapService.process_message(policy_xml)
    return result


class SoapService:
    """
    Handles all Soap IO with XStream
    """
    @staticmethod
    def _establish_client():
        """
        Creates a soap client using local wsdl file
        :return: Result
        """
        logger.debug('SoapService - _establish_client()')
        try:
            client = zeep.Client(wsdl=settings.WSDL)
        except Exception as e:
            message = 'Unable to create soap client from wsdl file, error: {}'.format(e)
            logger.error(message)
            raise IOError(message)

        return client

    @staticmethod
    def _post_to_xstream(client: zeep.Client, xml: str):
        """
        Posts xml to client
        :param client:
        :param xml:
        :return: Result
        """
        logger.debug('SoapService - _post_to_xstream() xml: {}'.format(xml))
        try:
            response = client.service.processMessage(*settings.XSTREAM_CREDENTIALS, xml, 0)
        except Exception as e:
            message = 'Failed to post to xstream, error: {}'.format(e)
            logger.error(message)
            raise IOError(message)

        return response

    @staticmethod
    def _handle_response(response: str) -> Result:
        """
        Handles xstream response, and returns Result of either errors or data if ok.
        :param response:
        :return: Result
        """
        logger.debug('SoapService - _handle_response(response: {})'.format(response))
        result = Result()
        parsed_response = xmltodict.parse(response)['xmlreply']
        response_result = parsed_response['messages']['result']

        if response_result == 'OK':
            refno = parsed_response['apmdata']['prospect']['p.cm']['refno']
            result.data = {'Refno': refno}
            result.status = True
        elif response_result == 'Error':
            errors = parsed_response['messages']['error'] if 'error' in parsed_response['messages'] else None  # type: list
            result.status = False

        return result

    @staticmethod
    def process_message(xml: str) -> Result:
        client = SoapService._establish_client()
        response = SoapService._post_to_xstream(client, xml)
        result = SoapService._handle_response(response)
        return result


XSTREAM_TEMPLATE = {
    'xmlexecute': {
        'job': {
            'queue': '1'
        },
        'parameters': {
            'yzt': {
                'Char20.1': None
            }
        },
        'apmdata': {
            'prospect': {
                'p.cm': None
            }
        },
        'apmpolicy': {
            'p.py': {
                'Ptype': None
            }
        }
    }
}
