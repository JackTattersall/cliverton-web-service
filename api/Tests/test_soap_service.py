import re

from django.test import TestCase
from api.soap_service import SoapService, Result
from unittest import mock
from django.conf import settings
import xml.etree.ElementTree as ET
import zeep


class EstablishClientTests(TestCase):

    @mock.patch('api.soap_service.zeep.Client')
    def test_sets_self_client_on_success(self, zeep_client):
        """
        On success, returns Result(client)
        """
        # Arrange
        zeep_client.return_value = 'test'

        # Act
        result = SoapService._establish_client()

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.data, 'test')

    @mock.patch('api.soap_service.logger.error')
    @mock.patch('api.soap_service.zeep.Client')
    def test_errors_handled_gracefully(self, zeep_client: mock.MagicMock, mock_logger: mock.MagicMock):
        """
        On failure, error is caught, logged, and returns Result - success false
        """
        # Arrange
        zeep_client.side_effect = Exception()

        # Act
        result = SoapService._establish_client()

        # Assert
        mock_logger.assert_called_once_with('Unable to create soap client from wsdl file, error: ')
        self.assertTrue(result.message)
        self.assertFalse(result.data)
        self.assertFalse(result.success)


class GetXmlTemplateTests(TestCase):
    def test_get_success(self):
        """
        On success, returns Result(xml_template)
        """
        # Act
        result = SoapService._get_xml_template(settings.XML_TEMPLATES['prospect_create']['template'])

        # Assert
        self.assertTrue(result.success)
        self.assertTrue(result.data)
        self.assertFalse(result.message)

    @mock.patch('api.soap_service.logger.error')
    def test_errors_handled_gracefully(self, mock_logger: mock.MagicMock):
        """
        On failure, error is caught, logged, and returns Result - success false
        """
        # Act
        result = SoapService._get_xml_template('bad_url')

        # Assert
        mock_logger.assert_called_once_with(
            "Unable to get xml template, error: [Errno 2] No such file or directory: 'bad_url'"
        )
        self.assertFalse(result.success)
        self.assertFalse(result.data)
        self.assertTrue(result.message)


class ParseCreateTests(TestCase):

    def strip(self, xml_string: str) -> str:
        """
        Removes tabs white space and newlines from a string
        :param xml_string:
        :return: str
        """
        return re.sub(r"[\\n\\t\s]*", "", xml_string)

    def setUp(self):
        self.mock_xml_template = ET.parse('templates\\prospect_create.xml')

    def test_parse_valid_data(self):
        """
        Test that valid json data is parsed as expected
        """
        # Arrange
        mock_json = {
            'function_type': 'prospect_create',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Dob': '23/07/1986',
                'Exec': '£$%'
            },
            'Ptype': 'YT'
        }

        expected_result = ET.tostring(ET.parse('templates\\test_xml\\prospect_create.xml').getroot(), encoding='unicode')

        # Act
        result = SoapService._parse_create(mock_json, self.mock_xml_template)

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(self.strip(result.data), self.strip(expected_result))
        self.assertEquals(str, type(result.data))

    @mock.patch('api.soap_service.logger.error')
    def test_p_type_required(self, mock_logger: mock.MagicMock):
        """
        Test invalid json due to no Ptype being provided is handled and logged
        """
        # Arrange
        mock_json = {
            'function_type': 'prospect_create',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Dob': '23/07/1986',
                'Exec': '£$%'
            },
        }

        # Act
        result = SoapService._parse_create(mock_json, self.mock_xml_template)

        # Assert
        self.assertFalse(result.success)
        self.assertEquals(result.message, "Failed to _parse_create, error: 'Ptype'")
        mock_logger.assert_called_once_with("Failed to _parse_create, error: 'Ptype'")

    @mock.patch('api.soap_service.logger.error')
    def test_p_cm_required(self, mock_logger: mock.MagicMock):
        """
        Test invalid json due to no p.cm being provided is handled and logged
        """
        # Arrange
        mock_json = {
            'function_type': 'prospect_create',
            'Ptype': 'YT'
        }

        # Act
        result = SoapService._parse_create(mock_json, self.mock_xml_template)

        # Assert
        self.assertFalse(result.success)
        self.assertEquals(result.message, "Failed to _parse_create, error: 'p.cm'")
        mock_logger.assert_called_once_with("Failed to _parse_create, error: 'p.cm'")


class PostToXStreamTests(TestCase):

    def test_successful_post(self):
        # Arrange
        mock_client = mock.Mock()
        mock_client.service.processMessage.return_value = '<xmlreply><messages><result>OK</result></messages></xmlreply>'

        # Act
        result = SoapService._post_to_xstream(mock_client, '<xmlexecute></xmlexecute>')

        # Assert
        self.assertTrue(result.data)
        self.assertTrue(result.success)

    @mock.patch('api.soap_service.logger.error')
    def test_post_errors(self, mock_logger: mock.MagicMock):
        # Arrange
        mock_client = mock.Mock()
        mock_client.service.processMessage.side_effect = Exception('Timed out')

        # Act
        result = SoapService._post_to_xstream(mock_client, '<xmlexecute></xmlexecute>')

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Failed to post to xstream, error: Timed out')
        mock_logger.assert_called_once_with('Failed to post to xstream, error: Timed out')


class HandleResponseTests(TestCase):
    def test_success(self):
        # Arrange
        mock_response = """
        <xmlreply>
            <messages>
                <result>OK</result>
            </messages>
            <apmdata>
                <apmpolicy>
                    <p.py>
                        <polref>12345</polref>
                        <refno>12345</refno>
                    </p.py>
                </apmpolicy>
            </apmdata>
        </xmlreply>"""

        # Act
        result = SoapService._handle_response(mock_response)

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.data['ref'], '12345')
        self.assertEqual(result.data['polref'], '12345')

    def test_error_returned(self):
        # Arrange
        mock_response = '<xmlreply><messages><result>Error</result><error>Error 1</error><error>Error 2</error></messages></xmlreply>'

        # Act
        result = SoapService._handle_response(mock_response)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(len(result.data), 2)
        self.assertIn('Error 1', result.data)
        self.assertIn('Error 2', result.data)

    def test_response_result_text_not_accounted_for(self):
        # Arrange
        mock_response = '<xmlreply><messages><result>Fred</result></messages></xmlreply>'

        # Act
        result = SoapService._handle_response(mock_response)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Response result text not accounted for, text: Fred')

    def test_no_response_result_text(self):
        # Arrange
        mock_response = '<xmlreply><messages><result></result></messages></xmlreply>'

        # Act
        result = SoapService._handle_response(mock_response)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(
            result.message,
            'Response has empty result, response: <xmlreply><messages><result /></messages></xmlreply>'
        )


class CreateProspectTests(TestCase):

    def setUp(self):
        self.mock_json = {
            'function_type': 'prospect_create',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Dob': '23/07/1986',
                'Exec': '£$%'
            },
        }

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_with_valid_data(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt, mock_ec: mock.Mock):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=True, data='client')
        mock_gxt.return_value = Result(success=True, data='template')
        mock_pc.return_value = Result(success=True, data='xml')
        mock_ptx.return_value = Result(success=True, data='response')
        mock_hr.return_value = Result(
            data={'ref': '1', 'polref': '1'},
            success=True
        )

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertEqual(result.data['ref'], '1')
        self.assertEqual(result.data['polref'], '1')
        mock_ec.assert_called_once()
        mock_gxt.assert_called_once_with('templates\\prospect_create.xml')
        mock_pc.assert_called_once_with(self.mock_json, 'template')
        mock_ptx.assert_called_once_with('client', 'xml')
        mock_hr.assert_called_once_with('response')

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_establish_client_fails(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt: mock.Mock, mock_ec):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=False, message='Error')

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Error')
        mock_ec.assert_called_once()
        mock_gxt.assert_not_called()
        mock_pc.assert_not_called()
        mock_ptx.assert_not_called()
        mock_hr.assert_not_called()

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_get_xml_template_fails(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt: mock.Mock, mock_ec):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=True, data='client')
        mock_gxt.return_value = Result(success=False, message='Error')

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Error')
        mock_ec.assert_called_once()
        mock_gxt.assert_called_once_with('templates\\prospect_create.xml')
        mock_pc.assert_not_called()
        mock_ptx.assert_not_called()
        mock_hr.assert_not_called()

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_parse_create_fails(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt: mock.Mock, mock_ec):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=True, data='client')
        mock_gxt.return_value = Result(success=True, data='template')
        mock_pc.return_value = Result(success=False, message='Error')

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Error')
        mock_ec.assert_called_once()
        mock_gxt.assert_called_once_with('templates\\prospect_create.xml')
        mock_pc.assert_called_once_with(self.mock_json, 'template')
        mock_ptx.assert_not_called()
        mock_hr.assert_not_called()

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_post_to_xstream_fails_without_response_data(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt: mock.Mock, mock_ec):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=True, data='client')
        mock_gxt.return_value = Result(success=True, data='template')
        mock_pc.return_value = Result(success=True, data='xml')
        mock_ptx.return_value = Result(success=False, message='Error')

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Error')
        mock_ec.assert_called_once()
        mock_gxt.assert_called_once_with('templates\\prospect_create.xml')
        mock_pc.assert_called_once_with(self.mock_json, 'template')
        mock_ptx.assert_called_once_with('client', 'xml')
        mock_hr.assert_not_called()

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_handle_response_fails(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt: mock.Mock, mock_ec):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=True, data='client')
        mock_gxt.return_value = Result(success=True, data='template')
        mock_pc.return_value = Result(success=True, data='xml')
        mock_ptx.return_value = Result(success=True, data='response')
        mock_hr.return_value = Result(success=False, message='Error')

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Error')
        mock_ec.assert_called_once()
        mock_gxt.assert_called_once_with('templates\\prospect_create.xml')
        mock_pc.assert_called_once_with(self.mock_json, 'template')
        mock_ptx.assert_called_once_with('client', 'xml')
        mock_hr.assert_called_once_with('response')

    @mock.patch('api.soap_service.SoapService._establish_client')
    @mock.patch('api.soap_service.SoapService._get_xml_template')
    @mock.patch('api.soap_service.SoapService._parse_create')
    @mock.patch('api.soap_service.SoapService._post_to_xstream')
    @mock.patch('api.soap_service.SoapService._handle_response')
    @mock.patch('api.soap_service.SoapService._validate_json')
    def test_run_handle_response_with_error_response(self, mock_vj, mock_hr, mock_ptx, mock_pc, mock_gxt: mock.Mock, mock_ec):
        # Arrange
        mock_vj.return_value = Result(data=self.mock_json)
        mock_ec.return_value = Result(success=True, data='client')
        mock_gxt.return_value = Result(success=True, data='template')
        mock_pc.return_value = Result(success=True, data='xml')
        mock_ptx.return_value = Result(success=True, data='response')
        mock_hr.return_value = Result(success=False, data=['Error 1', 'Error 2'], message='Errors')

        # Act
        result = SoapService().process_message(self.mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertEqual('Errors', result.message)
        self.assertIn('Error 1', result.data)
        self.assertIn('Error 2', result.data)
        mock_ec.assert_called_once()
        mock_gxt.assert_called_once_with('templates\\prospect_create.xml')
        mock_pc.assert_called_once_with(self.mock_json, 'template')
        mock_ptx.assert_called_once_with('client', 'xml')
        mock_hr.assert_called_once_with('response')


class CalculateQuoteTests(TestCase):
    pass


class CreateProspectIntegrationTests(TestCase):

    def stest_valid_json_prospect_create(self):
        # Arrange
        mock_json = {
            'function_type': 'prospect_create',
            'Ptype': 'YT',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Dob': '23/07/1986',
                'Exec': '£$%'
            },
        }

        # Act
        result = SoapService.process_message(mock_json)

        # Assert
        self.assertTrue(result.data['ref'])
        self.assertTrue(result.data['polref'])
        self.assertFalse(result.data['value'])


class ValidateJsonTests(TestCase):
    def test_prospect_create_valid(self):
        """
        Rules -
        * Ptype required and always 2 characters
        * p.cm required
        * Name required
        * Addr1 required max30
        * Addr2 max30 optional
        * Addr3 max30 optional
        * Addr4 max30 optional
        * Pcode required max10
        * Tel required max20
        * Exec required default ABA1
        * Agent required default 0000
        * Cust.class required default Consumer
        * Cust.class.mf required default Consumer  ???????????????????????? todo ask Graeme
        * Char1 required default TBC  todo get this confirmed
        * Email required max50
        """
        # Arrange
        mock_json = {
            'function_type': 'prospect_create',
            'Ptype': 'YT',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Email': 'j@j.com',
            }
        }

        expected_result = {
            'Ptype': 'YT',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Addr2': None,
                'Addr3': None,
                'Addr4': None,
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Email': 'j@j.com',
                'Exec': 'ABA1',
                'Agent': '0000',
                'Cust.class': 'Consumer',
                'Cust.class.mf': 'Consumer',
                'Char1': 'TBC'
            }
        }

        # Act
        result = SoapService._validate_json(mock_json)

        self.assertTrue(result.success)
        self.assertEqual(result.data, expected_result)
        print(result.data)

    def test_required_field_missing(self):
        # Arrange
        # Required field missing
        mock_json = {
            'function_type': 'prospect_create',
            'Ptype': 'YT',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                # 'Email': 'j@j.com',
            }
        }

        # Act
        result = SoapService._validate_json(mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertIn("error: Key 'p.cm'",  result.message, msg='p.cm error message')
        self.assertIn("Missing keys: 'Email'",  result.message, msg='email error message')

    def test_string_length_too_large(self):
        # Arrange
        # Required field missing
        mock_json = {
            'function_type': 'prospect_create',
            'Ptype': 'Too, many, characters',
            'p.cm': {
                'Name': 'Bob Test',
                'Addr1': '3 Test Rd',
                'Pcode': 'TT1 TT2',
                'Tel': '1234567890',
                'Email': 'j@j.com',
            }
        }

        # Act
        result = SoapService._validate_json(mock_json)

        # Assert
        self.assertFalse(result.success)
        self.assertIn("Invalid Ptype length",  result.message, msg='p.cm error message')
