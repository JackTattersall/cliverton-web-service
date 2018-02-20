from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, renderers
from api.services import validate_json, create_prospect, add_policy
from api.parsers import prospect_schema, policy_schema, transaction_schema


class Prospect(APIView):
    http_method_names = ['post']
    renderer_classes = [renderers.JSONRenderer]

    def post(self, request, *args, **kwargs):

        prospect_data = self.request.data
        is_validated = validate_json(prospect_data, prospect_schema)

        if not is_validated:
            return Response({'message': 'Malformed request'}, status=status.HTTP_400_BAD_REQUEST)

        prospect_created = create_prospect(prospect_data)

        if not prospect_created.status:
            return Response({'message': 'Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(prospect_created.data, status=status.HTTP_200_OK)


class Policy(APIView):
    http_method_names = ['post']
    renderer_classes = [renderers.JSONRenderer]

    def post(self, request, *args, **kwargs):
        policy_data = self.request.data
        is_validated = validate_json(policy_data, policy_schema)

        if not is_validated:
            return Response({'message': 'Malformed request'}, status=status.HTTP_400_BAD_REQUEST)

        policy_added = add_policy(policy_data)
        return Response(policy_data, status=status.HTTP_200_OK)


class Transact(APIView):
    http_method_names = ['post']
    renderer_classes = [renderers.JSONRenderer]

    def post(self, request, *args, **kwargs):
        transaction_data = self.request.data
        print(transaction_data)
        validated_data = validate_json(transaction_data, transaction_schema)

        if not validated_data:
            return Response({'message': 'Malformed request'}, status=status.HTTP_400_BAD_REQUEST)

        # result = create_prospect(prospect_data)
        return Response(validated_data, status=status.HTTP_200_OK)
