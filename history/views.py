from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from lr_booking.models import LR_Bokking, LR_Bokking_Description, PartyMaster
from django.http import JsonResponse
# Create your views here.

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from lr_booking.models import StandardRate,LR_Bokking,LR_Other_Charges
from .serializers import PartyBillingSerializer,VoucherPaymentBranchSerializer,CashStatmentLRSerializer,TruckUnloadingReportSerializer,LocalMemoDeliverySerializer,DeliveryStatementSerializer,LR_BokkingDescriptionSerializer, LRBokkingSerializer,TripMemoSerializer, StandardRateSerializer,LR_Other_ChargesSerializer, BookingMemoSerializer, CollectionSerializer
from items.models import ItemDetailsMaster,QuotationTypes,SubItemDetailsMaster
from branches.models import BranchMaster
from vehicals.models import VehicalMaster
from parties.models import PartyMaster
from destinations.models import DestinationMaster
from transactions.models import LoadTypes, PaidTypes, CollectionTypes, DeliveryTypes,PayTypes
from django.core.exceptions import ObjectDoesNotExist
from company.models import CompanyMaster,FinancialYears
from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from django.shortcuts import render, get_object_or_404
import json
from weasyprint import HTML, CSS
import base64
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from datetime import datetime
from collection.models import Collection,BookingMemo,BookingMemoLRs, TripBokkingMemos, TripMemo

from delivery.models import LocalMemoDelivery,DeliveryStatement, TruckUnloadingReport,TruckUnloadingReportDetails

from rest_framework.exceptions import ValidationError
from users.models import UserProfile
from company.filters import apply_filters
from company.views import send_email_with_attachment,send_sms
import os
from account.models import PartyBilling,VoucherReceiptBranch,MoneyReceipt,VoucherPaymentBranch,CashStatmentLR

from django.db.models import Q
from rest_framework.permissions import AllowAny
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models import F
from datetime import timedelta



class RetrieveLRBookingHistoryView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        # Expecting 'lr_number' in the POST data
        lr_number = request.data.get('lr_number')

        # Check if 'lr_number' is provided
        if not lr_number:
            return Response({
                'message': 'LR_Bokking lr_number is required',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the LR_Bokking instance by lr_number
            lr_booking = LR_Bokking.objects.get(lr_number=lr_number)

            # Fetch related collections
            collections = Collection.objects.filter(lr_booking=lr_booking)

            # Fetch related BookingMemoLRs and BookingMemo
            booking_memo_lrs = BookingMemoLRs.objects.filter(lr_booking=lr_booking)
            booking_memo = BookingMemo.objects.filter(lr_list__in=booking_memo_lrs).distinct()

            # Fetch related TripMemo
            trip_bokking_memos = TripBokkingMemos.objects.filter(booking_memo__in=booking_memo)
            trip_memo = TripMemo.objects.filter(booking_memos__in=trip_bokking_memos).distinct()

            # Fetch related TUR
            truck_unloading_report_details = TruckUnloadingReportDetails.objects.filter(lr_booking=lr_booking)
            truck_unloading_report = TruckUnloadingReport.objects.filter(tur_details__in=truck_unloading_report_details).distinct()

            # Fetch related LDM
            local_memo_delivery = LocalMemoDelivery.objects.filter(lr_booking=lr_booking)

            # Fetch related DS
            delivery_statement = DeliveryStatement.objects.filter(lr_booking=lr_booking)

            # by ritika
            try:
                filtered_delivery_statements = []
                for ds in delivery_statement:
                    # Filter only the relevant lr_booking
                    relevant_lr_booking = ds.lr_booking.filter(lr_no=lr_booking.lr_no)  # Use `.filter()` for ORM queryset
                    if relevant_lr_booking.exists():
                        ds_dict = DeliveryStatementSerializer(ds).data
                        ds_dict['lr_booking'] = LRBokkingSerializer(relevant_lr_booking, many=True).data
                        filtered_delivery_statements.append(ds_dict)
               
            except Exception as e:
                # Handle errors during filtering or serialization
                print(f"An error occurred while filtering delivery statements: {e}")
                filtered_delivery_statements = []  # Default to an empty list in case of errors
            # end by ritika
                    

            # Fetch related PartyBilling
            party_billing = PartyBilling.objects.filter(lr_booking=lr_booking)

            # Fetch related CashStatmentLR
            voucher_reciept_branch = CashStatmentLR.objects.filter(lr_booking=lr_booking)

            # Fetch related MoneyReceipt
            money_receipt = MoneyReceipt.objects.filter(lr_booking=lr_booking)
            
            # Fetch related VoucherPaymentBranch
            voucher_pay_branch = VoucherPaymentBranch.objects.filter(lr_no=lr_booking)

            # Serialize the data
            lr_booking_serializer = LRBokkingSerializer(lr_booking)
            collection_serializer = CollectionSerializer(collections, many=True)
            booking_memo_serializer = BookingMemoSerializer(booking_memo, many=True)
            trip_memo_serializer = TripMemoSerializer(trip_memo, many=True)
            truck_unloading_report_serializer = TruckUnloadingReportSerializer(truck_unloading_report,many=True)
            local_memo_delivery_serializer = LocalMemoDeliverySerializer(local_memo_delivery,many=True)
            # delivery_statement_serializer = DeliveryStatementSerializer(delivery_statement,many=True)
           
            party_billing_serializer = PartyBillingSerializer(party_billing,many=True)
            voucher_reciept_branch_serializer = CashStatmentLRSerializer(voucher_reciept_branch,many=True)
            # money_receipt_serializer = MoneyReceiptSerializer(money_receipt,many=True)
            voucher_pay_branch_serializer = VoucherPaymentBranchSerializer(voucher_pay_branch,many=True)

            # Return the combined data
            return Response({
                'message': 'LR_Bokking history retrieved successfully',
                'status': 'success',
                'lr_booking': lr_booking_serializer.data,
                'collection_momo': collection_serializer.data,
                'booking_memos': booking_memo_serializer.data,
                'trip_memos': trip_memo_serializer.data,
                'truck_unloading_report':truck_unloading_report_serializer.data,
                'local_memo_delivery':local_memo_delivery_serializer.data,
                # 'delivery_statement':delivery_statement_serializer.data,
                'delivery_statement':filtered_delivery_statements,
                'party_billing':party_billing_serializer.data,
                'voucher_reciept_branch':voucher_reciept_branch_serializer.data,
                
                'voucher_pay_branch':voucher_pay_branch_serializer.data,

            }, status=status.HTTP_200_OK)

        except LR_Bokking.DoesNotExist:
            return Response({
                'message': 'LR_Bokking not found',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# /////////////////////////////////////////////////////////


