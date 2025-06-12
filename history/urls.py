
# lr_booking/urls.py

from django.urls import path
from . import views



urlpatterns = [
   path('lr-bokking/check_history/', views.RetrieveLRBookingHistoryView.as_view(), name='lr-bokking-check-ds'),
   
]
  
