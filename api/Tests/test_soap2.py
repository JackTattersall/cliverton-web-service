from api.soap2 import *
from django.test import TestCase


class ValidatorTests(TestCase):
    def test_valid_prospect_data(self):
        # Arrange
        mock_json = {
            'Name': 'Bob Test',
            'Addr1': '3 Test Rd',
            'Pcode': 'TT1 TT2',
            'Tel': '1234567890',
            'Email': 'j@j.com',
        }

        expected_result = {
            'Name': 'Bob Test',
            'Addr1': '3 Test Rd',
            'Pcode': 'TT1 TT2',
            'Tel': '1234567890',
            'Email': 'j@j.com',
        }

        # Act
        result = validate_json(mock_json, 'p.cm')

        self.assertTrue(result)
        self.assertEqual(result, expected_result)
        print(result)