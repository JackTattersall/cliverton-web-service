from django.urls import path
from api.views import Prospect, Transact, Policy

urlpatterns = [
    path('prospect', Prospect.as_view()),
    path('risk', Policy.as_view()),
    path('transact', Transact.as_view())
]