from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from branches.models import BranchMaster
from .models import GSTMaster,PartyBilling,VoucherReceiptType,VoucherReceiptBranch,MoneyReceipt,VoucherPaymentType,VoucherPaymentBranch,CashBook,BillingSubmission,DeductionReasonType,Deduction
from .serializers import GSTMasterSerializer,DeductionLRetrieveSerializer,PartyBillingSerializer,VoucherReceiptTypeSerializer,VoucherReceiptBranchSerializer,MoneyReceiptSerializer,VoucherPaymentTypeSerializer,VoucherPaymentBranchSerializer,CashBookSerializer,BillingSubmissionSerializer,DeductionReasonTypeSerializer,DeductionSerializer
from django.core.exceptions import ObjectDoesNotExist
from lr_booking.models import LR_Bokking
from parties.models import PartyMaster
from django.db import transaction
from decimal import Decimal
from weasyprint import HTML, CSS

from django.http import HttpResponse
from company.models import CompanyMaster
from delivery.models import CustomerOutstanding
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from users.models import UserProfile
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from company.filters import apply_filters
from company.views import send_email_with_attachment,send_sms
import os
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone

class GSTMasterCreateView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = GSTMasterSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response({
                    'status': 'success',
                    'message': 'GST Master created successfully.',
                    'data': [serializer.data]
                }, status=status.HTTP_201_CREATED)
            return Response({
                'status': 'error',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GSTMasterRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = GSTMaster.objects.get(pk=gst_id)
            serializer = GSTMasterSerializer(instance)
            return Response({'msg': 'GST Master retrieved successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
        except GSTMaster.DoesNotExist:
            return Response({'msg': 'GST Master not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class GSTMasterRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve all GSTMaster instances where `flag=True`, ordered by `id` in descending order
            instances = GSTMaster.objects.filter(flag=True).order_by('-id')
            serializer = GSTMasterSerializer(instances, many=True)

            # Custom response structure
            response_data = {
                'msg': 'GST records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving GST records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GSTMasterRetrieveFilteredView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = GSTMaster.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = GSTMasterSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered GST records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered GST records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GSTMasterUpdateView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = GSTMaster.objects.get(pk=gst_id)
            serializer = GSTMasterSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response({'msg': 'GST Master updated successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
            return Response({'msg': 'Validation failed', 'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except GSTMaster.DoesNotExist:
            return Response({'msg': 'GST Master not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class GSTMasterDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = GSTMaster.objects.get(pk=gst_id)
            instance.flag = False
            instance.save()
            return Response({'msg': 'GST Master soft deleted successfully', 'status': 'success', 'data': {}}, status=status.HTTP_200_OK)
        except GSTMaster.DoesNotExist:
            return Response({'msg': 'GST Master not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

from num2words import num2words

class GeneratePartyBillingPDF(APIView):
    def get(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(PartyBilling, bill_no=delivery_no)
        bookings = statement.lr_booking.all()

        bookingss = statement.lr_booking.prefetch_related('descriptions').all()
        for booking in bookingss:
            print(f"LR No: {booking.lr_number}, Descriptions: {list(booking.descriptions.all())}")

        # print("bookingss")

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Generate barcode for the delivery_no
        barcode_base64 = generate_barcode(delivery_no)

        bill_total=statement.totla_amt
        bill_total_words = num2words(bill_total, lang='en').upper()

        # Get the logged-in user's name
        user_profile = UserProfile.objects.get(user=statement.created_by)
        user_name = user_profile.first_name + " "+user_profile.last_name

        # Render HTML to string
        html_string = render(request,'party_billing/party_billing.html', {
            'company': company,
            'statement': statement,  
            'bookings': bookings,     
            'barcode_base64': barcode_base64,
            'bill_total_words':bill_total_words,
            'user_name': user_name,
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Vouch_pay_branch_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response


class GeneratePartyBillingBillNumberViews(APIView):   
    def post(self, request, *args, **kwargs):
        print(request.data)
        try:

            branch_id = request.data.get('branch_id')

            if not branch_id:
                response_data = {
                    'msg': 'branch_id are required',
                    'status': 'error',
                    'data': None
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


            # Retrieve and validate the active branch
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Combine the financial year prefix and branch code
            # prefix = f"{branch_code}"
            prefix=25000

            # Get the last non-null and non-blank lr_number for this branch with matching financial year prefix
            last_booking_memo = PartyBilling.objects.filter(
                # branch_name_id=branch_id,
                bill_no__startswith=prefix
            ).exclude(bill_no__isnull=True).exclude(bill_no__exact='').order_by('-bill_no').first()

            if last_booking_memo:
                last_sequence_number = int(last_booking_memo.bill_no[5:])# important 5 is len of prefix replace if changed 
                new_delivery_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
            else:
                new_delivery_no = f"{prefix}00001"

            # On successful LR number generation
            response_data = {
                'msg': 'Bill number generated successfully',
                'status': 'success',
                'data': {
                    'bill_no': new_delivery_no
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            # Handle case where FinancialYear or BranchMaster doesn't exist
            response_data = {
                'status': 'error',
                'message': 'The specified branch was not found.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            # Handle cases where lr_number conversion fails or other value-related errors occur
            response_data = {
                'status': 'error',
                'message': 'An error occurred during Bill number generation due to invalid data.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any other unexpected exceptions
            response_data = {
                'status': 'error',
                'message': 'An error occurred while generating the Bill number.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CreatePartyBillingView(APIView):    
    def post(self, request, *args, **kwargs):
        data = request.data
        lr_booking_ids = data.pop('lr_booking', [])
        requested_billing_party = data.get('billing_party')

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("bill_no")
        # Validate if branch_id and lr_number are provided
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and bill_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert lr_number to a string and ensure it has at least 5 digits
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid bill Number format.")

            # Extract the first 5 digits of lr_number
            lr_branch_code = memo_no[:5]

            # Fetch the branch using branch_id
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Validate that the first 5 digits of lr_number match the branch code
            # if lr_branch_code != branch_code:
            #     return Response({
            #         "status": "error",
            #         "msg": "The branch code in bill Number does not match the requested branch."
            #     }, status=status.HTTP_400_BAD_REQUEST)

            
            
        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid bill  Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            try:
                billing_party = PartyMaster.objects.get(id=requested_billing_party)
            except PartyMaster.DoesNotExist:
                    return Response({
                        "message": f"PartyMaster with lr_no {requested_billing_party} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
            if int(billing_party.party_type_id) != 2 :                                        
                        return Response({
                            "msg": (
                                f"PartyMaster with lr_no {requested_billing_party} has not party_type 'Billing'. "                        
                            ),
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)
                        
            # Validate each LR_Bokking in the requested list
            for lr_no in lr_booking_ids:
                # Get the LR_Bokking object
                try:
                    lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
                except LR_Bokking.DoesNotExist:
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                try:
                    lr_billing=lr_booking.billing_party_id
                    lr_billing_party=PartyMaster.objects.get(id=lr_billing)
                    
                    if lr_billing_party.branch_id != branch_id:
                        return Response({
                            "status": "error",
                            "msg": "The billing party branch does not match the requested branch."
                        }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({
                        "message": "An error occurred while retriving Party of Billing",
                        "status": "error",
                        "details": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Validation 1: Ensure lr_booking is not already associated with an active PartyBilling
                if PartyBilling.objects.filter(
                    lr_booking=lr_booking,
                    is_active=True,
                    flag=True
                ).exists():
                    return Response({
                        "msg": f"LR_Bokking with lr_no {lr_no} is already associated with an active PartyBilling.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validation 2: Check pay_type and billing_party               
                if int(lr_booking.pay_type_id) != 3 :                                        
                        return Response({
                            "msg": (
                                f"LR_Bokking with lr_no {lr_no} has not pay_type 'TBB'. "                        
                            ),
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)
                if int(lr_booking.billing_party_id) != int(requested_billing_party):    
                        return Response({
                            "msg": (
                                f"LR_Bokking with lr_no {lr_no} has billing_party does not match the requested billing_party "                        
                            ),
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)
                    

            # If all validations pass, proceed with creation
            with transaction.atomic():
                serializer = PartyBillingSerializer(data=data)
                if serializer.is_valid():
                    party_biilling = serializer.save()

                    # Add LR_Bokking entries to the ManyToMany field
                    lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                    if len(lr_bookings) != len(lr_booking_ids):
                        raise ValueError("One or more LR_Booking IDs not found.")
                    party_biilling.lr_booking.set(lr_bookings)
                    party_biilling.created_by = request.user

                    response_serializer = PartyBillingSerializer(party_biilling)
                    return Response({
                        "message": "Party Billing Statement created successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    "message": "Failed to create Party Billing",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "message": "An error occurred while creating Party Billing",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class PartyBillingRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        # Expecting 'id' in the POST data
        standard_rate_id = request.data.get('id')

        # Check if 'id' is provided
        if not standard_rate_id:
            return Response({
                'message': 'Party Billing ID is required',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the StandardRate instance
            standard_rate = PartyBilling.objects.get(id=standard_rate_id)
        except PartyBilling.DoesNotExist:
            return Response({
                'message': 'Party Billing not found',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the retrieved instance
        serializer = PartyBillingSerializer(standard_rate)

        # Return the data with success status
        return Response({
            'message': 'Party Billing retrieved successfully',
            'status': 'success',
            'data': [serializer.data]
        }, status=status.HTTP_200_OK)

class PartyBillingRetrieveViewBybill_no(APIView):
    def post(self, request, *args, **kwargs):
        # Expecting 'id' in the POST data
        standard_rate_id = request.data.get('bill_no')

        # Check if 'id' is provided
        if not standard_rate_id:
            return Response({
                'message': 'Party Billing bill_no is required',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the StandardRate instance
            standard_rate = PartyBilling.objects.get(bill_no=standard_rate_id)
        except PartyBilling.DoesNotExist:
            return Response({
                'message': 'Party Billing not found',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the retrieved instance
        serializer = PartyBillingSerializer(standard_rate)

        # Return the data with success status
        return Response({
            'message': 'Party Billing retrieved successfully',
            'status': 'success',
            'data': [serializer.data]
        }, status=status.HTTP_200_OK)
 
class PartyBillingRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get("branch_id")
            user_profile = UserProfile.objects.get(user=request.user)            
            allowed_branches = user_profile.branches.all()

            if not branch_id:
                return Response({
                    "status": "error",
                    "message": "Branch ID is required."
                }, status=status.HTTP_400_BAD_REQUEST)


            # Retrieve all items from the database
            items = PartyBilling.objects.filter(
                flag=True
                ).filter(
                Q(branch_name__in=allowed_branches) 
                ).filter(
                Q(branch_name_id=branch_id)
                ).order_by('-id')

            # Serialize the items data
            serializer = PartyBillingSerializer(items, many=True)

            # Return a success response with the items data
            return Response({
                "status": "success",
                "message": "Items retrieved successfully.",
                "data": [serializer.data]
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                "status": "error",
                "message": "An unexpected error occurred.",
                "error": str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class PartyBillingRetrieveActiveView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Filter the queryset for active StandardRate instances
            queryset = PartyBilling.objects.filter(is_active=True,flag=True).order_by('-id')
            serializer = PartyBillingSerializer(queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Party Billing retrieved successfully',
                'status': 'success',
                'data': [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PartyBillingRetrieveVoucherReceiptView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Filter the queryset for active StandardRate instances
            queryset = PartyBilling.objects.filter(is_active=True,flag=True).order_by('-id')
            validated_queryset = [
                party_billing for party_billing in queryset
                if not  CashStatmentBill.objects.filter(
                    party_billing=party_billing,
                    is_active=True,
                    flag=True
                ).exists()
            ]   
            serializer = PartyBillingSerializer(validated_queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Party Billing retrieved successfully',
                'status': 'success',
                'data': [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PartyBillingRetrieveMoneyReceiptView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Filter the queryset for active StandardRate instances
            queryset = PartyBilling.objects.filter(is_active=True,flag=True).order_by('-id')
            validated_queryset = [
                party_billing for party_billing in queryset
                if not  MoneyReceipt.objects.filter(
                    party_billing=party_billing,
                    is_active=True,
                    flag=True
                ).exists()
            ]   
            serializer = PartyBillingSerializer(validated_queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Party Billing retrieved successfully',
                'status': 'success',
                'data': [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PartyBillingRetrieveBillingSubmissionView(APIView):
    def post(self, request, *args, **kwargs):
        print("request",request.data)
        try:
            # Expecting 'id' in the POST data
            branch_name = request.data.get('branch_name')
            print("party billing", branch_name)
            # Check if 'id' is provided
            if not branch_name:
                return Response({
                    'message': 'Party Billing branch_name is required',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            # Filter the queryset for active StandardRate instances
            queryset = PartyBilling.objects.filter(is_active=True,flag=True,branch_name_id=branch_name).order_by('-id')
            validated_queryset = [
                party_billing for party_billing in queryset
                if not  BillingSubmission.objects.filter(
                    bill_no=party_billing,
                    is_active=True,
                    flag=True
                ).exists()
            ]   
            serializer = PartyBillingSerializer(validated_queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Party Billing retrieved successfully',
                'status': 'success',
                'data': [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class PartyBillingRetrieveCSBillView(APIView):
    def post(self, request, *args, **kwargs):
        print("request",request.data)
        try:
            # Expecting 'id' in the POST data
            party = request.data.get('party')
            print("party billing", party)
            # Check if 'id' is provided
            if not party:
                return Response({
                    'message': 'Party Billing party is required',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            # Filter the queryset for active StandardRate instances
            queryset = PartyBilling.objects.filter(is_active=True,flag=True,billing_party_id=party).order_by('-id')
            # validated_queryset = [
            #     party_billing for party_billing in queryset
            #     if  BillingSubmission.objects.filter(
            #         bill_no=party_billing,
            #         is_active=True,
            #         flag=True
            #     ).exists()
                
            # ]  
            validated_queryset = [
                party_billing for party_billing in queryset
                if BillingSubmission.objects.filter(
                    bill_no=party_billing,
                    is_active=True,
                    flag=True
                ).exists()
                and not CashStatmentBill.objects.filter(
                    party_billing=party_billing,
                    is_active=True,
                    flag=True
                ).exists()
            ]
 
            serializer = PartyBillingSerializer(validated_queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Party Billing retrieved successfully',
                'status': 'success',
                'data': [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class PartyBillingFilterView(APIView): 
    def post(self, request, *args, **kwargs):        
        try:       
            # Extract filters from the request body
            filters = request.data.get("filters", {})
            print("filters party billing",filters)
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(PartyBilling, filters)

            print("queryset",queryset)

            # Serialize the filtered data
            serializer = PartyBillingSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data}, status=200)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)



class UpdatePartyBillingView(APIView):    
    def post(self, request, *args, **kwargs):
        data = request.data
        delivery_statement_id = data.get('id')  # Retrieve the ID of the PartyBilling to update
        lr_booking_ids = data.pop('lr_booking', [])
        requested_billing_party = data.get('billing_party')

        if not delivery_statement_id:
            return Response({
                "message": "ID of the PartyBilling record is required.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("bill_no")
        # Validate if branch_id and lr_number are provided
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and bill_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert lr_number to a string and ensure it has at least 5 digits
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid bill Number format.")

            # Extract the first 5 digits of lr_number
            lr_branch_code = memo_no[:5]

            # Fetch the branch using branch_id
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Validate that the first 5 digits of lr_number match the branch code
            # if lr_branch_code != branch_code:
            #     return Response({
            #         "status": "error",
            #         "msg": "The branch code in bill Number does not match the requested branch."
            #     }, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid bill Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            try:
                billing_party = PartyMaster.objects.get(id=requested_billing_party)
            except PartyMaster.DoesNotExist:
                    return Response({
                        "message": f"PartyMaster with lr_no {requested_billing_party} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
            if int(billing_party.party_type_id) != 2 :                                        
                        return Response({
                            "msg": (
                                f"PartyMaster with lr_no {requested_billing_party} has not Party_Type 'Billing'. "                        
                            ),
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)
            
            # Fetch the PartyBilling instance
            try:
                party_billing = PartyBilling.objects.get(id=delivery_statement_id, is_active=True, flag=True)
            except PartyBilling.DoesNotExist:
                return Response({
                    "message": f"PartyBilling with id {delivery_statement_id} does not exist or is inactive.",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)

            # Validate each LR_Bokking in the requested list
            for lr_no in lr_booking_ids:
                # Get the LR_Bokking object
                try:
                    lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
                except LR_Bokking.DoesNotExist:
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                try:
                    lr_billing=lr_booking.billing_party_id
                    lr_billing_party=PartyMaster.objects.get(id=lr_billing)
                    
                    if lr_billing_party.branch_id != branch_id:
                        return Response({
                            "status": "error",
                            "msg": "The billing party branch does not match the requested branch."
                        }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({
                        "message": "An error occurred while retriving Party of Billing",
                        "status": "error",
                        "details": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validation 1: Ensure lr_booking is not already associated with another active PartyBilling
                if PartyBilling.objects.filter(
                    lr_booking=lr_booking,
                    is_active=True,
                    flag=True
                ).exclude(id=delivery_statement_id).exists():
                    return Response({
                        "msg": f"LR_Bokking with lr_no {lr_no} is already associated with another active PartyBilling.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validation 2: Check pay_type and billing_party               
                if int(lr_booking.pay_type_id) != 3 :                                        
                        return Response({
                            "msg": (
                                f"LR_Bokking with lr_no {lr_no} has not pay_type 'TBB'. "                        
                            ),
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)
                if int(lr_booking.billing_party_id) != int(requested_billing_party):    
                        return Response({
                            "msg": (
                                f"LR_Bokking with lr_no {lr_no} has billing_party does not match the requested billing_party "                        
                            ),
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)

            # If all validations pass, proceed with the update
            with transaction.atomic():
                serializer = PartyBillingSerializer(party_billing, data=data, partial=True)
                if serializer.is_valid():
                    updated_party_billing = serializer.save(updated_by=request.user)

                    # Update LR_Bokking entries in the ManyToMany field
                    lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                    if len(lr_bookings) != len(lr_booking_ids):
                        raise ValueError("One or more LR_Booking IDs not found.")
                    updated_party_billing.lr_booking.set(lr_bookings)

                    response_serializer = PartyBillingSerializer(updated_party_billing)
                    return Response({
                        "message": "Party Billing Statement updated successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_200_OK)

                return Response({
                    "message": "Failed to update Party Billing",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "message": "An error occurred while updating Party Billing",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class PartyBillingSoftDeleteAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract ID from request data
        driver_master_id = request.data.get('id')
        
        if not driver_master_id:
            return Response({
                'msg': 'ID is required',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Retrieve the StandardRate instance
            instance = PartyBilling.objects.get(pk=driver_master_id)
            
            # Set is_active to False to soft delete
            instance.flag = False
            instance.save()
            
            return Response({
                'msg': 'Party Billing deactivated (soft deleted) successfully',
                'status': 'success',
                'data': {}
            }, status=status.HTTP_200_OK)
        
        except PartyBilling.DoesNotExist:
            return Response({
                'msg': 'StandardRate not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)
        
class PartyBillingPermanentDeleteAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract ID from request data
        receipt_type_id = request.data.get('id')
        
        if not receipt_type_id:
            return Response({
                'msg': 'ID is required',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Retrieve the StandardRate instance
            instance = PartyBilling.objects.get(pk=receipt_type_id)
            
            # Permanently delete the instance
            instance.delete()
            
            return Response({
                'msg': 'Party Billing permanently deleted successfully',
                'status': 'success',
                'data': {}
            }, status=status.HTTP_200_OK)
        
        except PartyBilling.DoesNotExist:
            return Response({
                'msg': 'StandardRate not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

# class PartyBillingPendingForBillingSubmission(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
            
#             billing_party = request.data.get('billing_party')

#             # Base queryset with fixed filters
#             queryset = PartyBilling.objects.filter(
#                 is_active=True,
#                 flag=True
#             ).order_by('-date')

#             # Apply optional billing_party filter if provided
#             if billing_party:
#                 queryset = queryset.filter(billing_party_id=billing_party)

#             validated_queryset = []

#             # Loop to filter out PartyBilling records already in BillingSubmission
#             for party_billing in queryset:
#                 if BillingSubmission.objects.filter(
#                     bill_no=party_billing,
#                     is_active=True,
#                     flag=True
#                 ).exists():
#                     continue  # Skip if already exists in BillingSubmission

#                 validated_queryset.append(party_billing)

#             # Serialize the validated queryset data
#             serializer = PartyBillingSerializer(validated_queryset, many=True)

#             return Response({
#                 'msg': 'Pending PartyBilling retrieved successfully',
#                 'status': 'success',
#                 'data': serializer.data
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({
#                 'status': 'error',
#                 'message': 'An unexpected error occurred',
#                 'error': str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PartyBillingPendingForBillingSubmission(APIView):
    def post(self, request, *args, **kwargs):
        try:
            filters = request.data.get("filters", {})
            
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(PartyBilling, filters)
            

            # Base queryset with fixed filters
            queryset = queryset.filter(
                is_active=True,
                flag=True
            ).order_by('-date')


            validated_queryset = []

            # Loop to filter out PartyBilling records already in BillingSubmission
            for party_billing in queryset:
                if BillingSubmission.objects.filter(
                    bill_no=party_billing,
                    is_active=True,
                    flag=True
                ).exists():
                    continue  # Skip if already exists in BillingSubmission

                validated_queryset.append(party_billing)

            # Serialize the validated queryset data
            serializer = PartyBillingSerializer(validated_queryset, many=True)

            return Response({
                'msg': 'Pending PartyBilling retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ////////////////////////////////////////////////////////////////

from datetime import timedelta

# class PartyBillingPendingForcs(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
#             filters = request.data.get("filters", {})
            
#             if not isinstance(filters, dict):
#                 raise ValidationError("Filters must be a dictionary.")

#             # Apply dynamic filters
#             queryset = apply_filters(PartyBilling, filters)
            

#             # Base queryset with fixed filters
#             queryset = queryset.filter(
#                 is_active=True,
#                 flag=True
#             ).order_by('-date')


#             validated_queryset = []

#             # Loop to filter out PartyBilling records already in BillingSubmission
#             # for party_billing in queryset:
#             #     if BillingSubmission.objects.filter(
#             #         bill_no=party_billing,
#             #         is_active=True,
#             #         flag=True
#             #     ).exists():
#             #         validated_queryset.append(party_billing)


#             for party_billing in queryset:
#                 billing_submission = BillingSubmission.objects.filter(
#                     bill_no=party_billing,
#                     is_active=True,
#                     flag=True
#                 ).first()

#                 # if billing_submission:  ******skip condition bcz want all party billing with or without billsubmossion *******
#                 validated_queryset.append({
#                         "party_billing": party_billing,
#                         "billing_submission": billing_submission
#                     })


#             validated_cs_queryset = []

#              # Loop to filter out PartyBilling records already in BillingSubmission
#             # for item  in validated_queryset:
#             #     party_billing = item["party_billing"]
#             #     if CashStatmentBill.objects.filter(
#             #         party_billing__in=[party_billing],  # Use __in for ManyToManyField filtering
#             #         is_active=True,
#             #         flag=True
#             #     ).exists():
#             #         continue  
                    
#             #     validated_cs_queryset.append(item)  # Add if it exists in CashStatmentBill



#             # Serialize the validated queryset data
#             # serializer = PartyBillingSerializer(validated_cs_queryset, many=True)
            
#             from datetime import date, timedelta

#             final_data = []

#             for item in validated_queryset:
#                     party_billing = item["party_billing"]
#                     billing_submission = item["billing_submission"]

#                     # Serialized data
#                     pb_data = PartyBillingSerializer(party_billing).data
#                     bs_data = BillingSubmissionSerializer(billing_submission).data if billing_submission else None

#                     # Calculate PaymentDueDate
#                     credit_days = party_billing.billing_party.credit_period or 0
#                     payment_due_date = party_billing.date + timedelta(days=credit_days)

#                     # Determine BillStatus
#                     bill_status = "Finalised" if billing_submission else "Non Finalised"

#                     # Aging calculation only if CS is NOT done
#                     cs_done = CashStatmentBill.objects.filter(
#                         party_billing__in=[party_billing],
#                         is_active=True,
#                         flag=True
#                     ).exists()

#                     # cs_done = bool(cs_obj)
#                     # csbl_no = cs_obj.csbl_no if cs_obj else None
                    
#                     bill_status = "Finalised" if cs_done else "Non Finalised"
#                     # csbl_no = cs_done.csbl_no if cs_done else None
                    
#                     aging_30 = aging_60 = aging_90 = aging_above = 0

#                     if not cs_done:
#                         days_diff = (date.today() - party_billing.date).days

#                         if 0 < days_diff <= 30:
#                             aging_30 = float(party_billing.totla_amt)
#                         elif 30 < days_diff <= 60:
#                             aging_60 = float(party_billing.totla_amt)
#                         elif 60 < days_diff <= 90:
#                             aging_90 = float(party_billing.totla_amt)
#                         elif days_diff > 90:
#                             aging_above = float(party_billing.totla_amt)

#                     final_data.append({
#                         "party_billing": pb_data,
#                         "billing_submission": bs_data,
#                         "BillStatus": bill_status,
#                         "PaymentDueDate": payment_due_date.strftime("%Y-%m-%d"),
#                         "30Days": aging_30,
#                         "60Days": aging_60,
#                         "90Days": aging_90,
#                         "Above": aging_above,
#                         "csbl_no": csbl_no  # Include csbl_no if exists
#                     })


#             return Response({
#                 'msg': 'Pending PartyBilling for cs retrieved successfully',
#                 'status': 'success',
#                 'data': final_data
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({
#                 'status': 'error',
#                 'message': 'An unexpected error occurred',
#                 'error': str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PartyBillingPendingForcs(APIView):
    def post(self, request, *args, **kwargs):
        try:
            filters = request.data.get("filters", {})
            
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(PartyBilling, filters)
            

            # Base queryset with fixed filters
            queryset = queryset.filter(
                is_active=True,
                flag=True
            ).order_by('-date')


            validated_queryset = []

            # Loop to filter out PartyBilling records already in BillingSubmission
            # for party_billing in queryset:
            #     if BillingSubmission.objects.filter(
            #         bill_no=party_billing,
            #         is_active=True,
            #         flag=True
            #     ).exists():
            #         validated_queryset.append(party_billing)


            for party_billing in queryset:
                billing_submission = BillingSubmission.objects.filter(
                    bill_no=party_billing,
                    is_active=True,
                    flag=True
                ).first()

                # if billing_submission:  ******skip condition bcz want all party billing with or without billsubmossion *******
                validated_queryset.append({
                        "party_billing": party_billing,
                        "billing_submission": billing_submission
                    })


            validated_cs_queryset = []

             # Loop to filter out PartyBilling records already in BillingSubmission
            # for item  in validated_queryset:
            #     party_billing = item["party_billing"]
            #     if CashStatmentBill.objects.filter(
            #         party_billing__in=[party_billing],  # Use __in for ManyToManyField filtering
            #         is_active=True,
            #         flag=True
            #     ).exists():
            #         continue  
                    
            #     validated_cs_queryset.append(item)  # Add if it exists in CashStatmentBill



            # Serialize the validated queryset data
            # serializer = PartyBillingSerializer(validated_cs_queryset, many=True)
            
            from datetime import date, timedelta

            final_data = []

            for item in validated_queryset:
                    party_billing = item["party_billing"]
                    billing_submission = item["billing_submission"]

                    # Serialized data
                    pb_data = PartyBillingSerializer(party_billing).data
                    bs_data = BillingSubmissionSerializer(billing_submission).data if billing_submission else None

                    # Calculate PaymentDueDate
                    credit_days = party_billing.billing_party.credit_period or 0
                    payment_due_date = party_billing.date + timedelta(days=credit_days)

                    # Determine BillStatus
                    # bill_status = "Finalised" if billing_submission else "Non Finalised"

                    # Aging calculation only if CS is NOT done
                    cs_done = CashStatmentBill.objects.filter(
                        party_billing__in=[party_billing],
                        is_active=True,
                        flag=True
                    ).first()

                    # cs_done = bool(cs_obj)
                    # csbl_no = cs_obj.csbl_no if cs_obj else None
                    
                    bill_status = "Finalised" if cs_done else "Non Finalised"
                    csbl_no = cs_done.csbl_no if cs_done else None
                    
                    aging_30 = aging_60 = aging_90 = aging_above = 0

                    if not cs_done:
                        days_diff = (date.today() - party_billing.date).days

                        if 0 < days_diff <= 30:
                            aging_30 = float(party_billing.totla_amt)
                        elif 30 < days_diff <= 60:
                            aging_60 = float(party_billing.totla_amt)
                        elif 60 < days_diff <= 90:
                            aging_90 = float(party_billing.totla_amt)
                        elif days_diff > 90:
                            aging_above = float(party_billing.totla_amt)

                    final_data.append({
                        "party_billing": pb_data,
                        "billing_submission": bs_data,
                        "BillStatus": bill_status,
                        "PaymentDueDate": payment_due_date.strftime("%Y-%m-%d"),
                        "30Days": aging_30,
                        "60Days": aging_60,
                        "90Days": aging_90,
                        "Above": aging_above,
                        "csbl_no": csbl_no  # Include csbl_no if exists
                    })


            return Response({
                'msg': 'Pending PartyBilling for cs retrieved successfully',
                'status': 'success',
                'data': final_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#/////////////////////////////////////////////////////////////////

# class GenerateVoucherReceiptCSNumberViews(APIView):   
#     def post(self, request, *args, **kwargs):
#         try:
#             # Extract branch_id from request data
#             branch_id = request.data.get('branch_id')

#             if not branch_id:
#                 response_data = {
#                     'msg': 'branch_id is required',
#                     'status': 'error',
#                     'data': None
#                 }
#                 return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

#             # Retrieve the branch and validate
#             branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
#             branch_code = branch.branch_code

#             # Define the prefix based on the branch code
#             prefix = f"{branch_code}"

#             # Retrieve the last generated `cs_no` for this branch
#             last_voucher_receipt = VoucherReceiptBranch.objects.filter(
#                 branch_name_id=branch_id,
#                 cs_no__startswith=prefix
#             ).exclude(cs_no__isnull=True).exclude(cs_no__exact='').order_by('-cs_no').first()

#             if last_voucher_receipt:
#                 # Extract the numeric part of the last `cs_no` and increment
#                 last_sequence_number = int(last_voucher_receipt.cs_no[len(prefix):])
#                 new_cs_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
#             else:
#                 # Start with the first sequence number if no `cs_no` exists
#                 new_cs_no = f"{prefix}00001"

#             # Successful generation
#             response_data = {
#                 'msg': 'CS number generated successfully',
#                 'status': 'success',
#                 'data': {
#                     'cs_no': new_cs_no
#                 }
#             }
#             return Response(response_data, status=status.HTTP_200_OK)

#         except ObjectDoesNotExist as e:
#             # Handle case where branch doesn't exist
#             response_data = {
#                 'status': 'error',
#                 'message': 'The specified branch was not found.',
#                 'error': str(e)
#             }
#             return Response(response_data, status=status.HTTP_404_NOT_FOUND)

#         except ValueError as e:
#             # Handle invalid data issues
#             response_data = {
#                 'status': 'error',
#                 'message': 'An error occurred during CS number generation due to invalid data.',
#                 'error': str(e)
#             }
#             return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             # Catch any other unexpected errors
#             response_data = {
#                 'status': 'error',
#                 'message': 'An error occurred while generating the CS number.',
#                 'error': str(e)
#             }
#             return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VoucherReceiptTypeCreateView(APIView):    
    def post(self, request, *args, **kwargs):
        try:
            serializer = VoucherReceiptTypeSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response({
                    'status': 'success',
                    'message': 'Voucher Receipt Type created successfully.',
                    'data': [serializer.data]
                }, status=status.HTTP_201_CREATED)
            return Response({
                'status': 'error',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherReceiptTypeRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherReceiptType.objects.get(pk=gst_id)
            serializer = VoucherReceiptTypeSerializer(instance)
            return Response({'msg': 'Voucher Receipt Type retrieved successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
        except VoucherReceiptType.DoesNotExist:
            return Response({'msg': 'Voucher Receipt Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class VoucherReceiptTypeRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve all GSTMaster instances where `flag=True`, ordered by `id` in descending order
            instances = VoucherReceiptType.objects.filter(flag=True).order_by('-id')
            serializer = VoucherReceiptTypeSerializer(instances, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Voucher Receipt Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving Voucher Receipt Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherReceiptTypeRetrieveFilteredView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = VoucherReceiptType.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = VoucherReceiptTypeSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered Voucher Receipt Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered Voucher Receipt Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherReceiptTypeRetrieveMoneyReceiptView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = VoucherReceiptType.objects.filter(is_active=True, flag=True).exclude(id=3).order_by('-id')
            serializer = VoucherReceiptTypeSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered Voucher Receipt Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered Voucher Receipt Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherReceiptTypeUpdateView(APIView):
    def post(self, request, *args, **kwargs):        
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherReceiptType.objects.get(pk=gst_id)
            serializer = VoucherReceiptTypeSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response({'msg': 'Voucher Receipt Type updated successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
            return Response({'msg': 'Validation failed', 'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except VoucherReceiptType.DoesNotExist:
            return Response({'msg': 'Voucher Receipt Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class VoucherReceiptTypeDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherReceiptType.objects.get(pk=gst_id)
            instance.flag = False
            instance.save()
            return Response({'msg': 'Voucher Receipt Type soft deleted successfully', 'status': 'success', 'data': {}}, status=status.HTTP_200_OK)
        except VoucherReceiptType.DoesNotExist:
            return Response({'msg': 'Voucher Receipt Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)



def generate_barcode(memo_no):
    # Convert memo_no to string as the barcode library expects a string
    memo_no_str = str(memo_no)

    # Create an in-memory bytes buffer to store the barcode image
    buffer = BytesIO()

    # Generate the barcode using CODE128 format without text below
    CODE128 = barcode.get_barcode_class('code128')
    barcode_image = CODE128(memo_no_str, writer=ImageWriter())

    # Disable text rendering (don't show the memo_no below the barcode)
    barcode_image.write(buffer, {'write_text': False})

    # Encode the barcode image to base64 so that it can be embedded in HTML
    buffer.seek(0)
    barcode_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return barcode_base64

class GenerateVoucherReceiptBranchPDF(APIView):
    def get(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(VoucherReceiptBranch, id=delivery_no)
        bookings = statement.lr_booking.all()
        parties = statement.party_billing.all()

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Generate barcode for the delivery_no
        barcode_base64 = generate_barcode(statement.cs_no)
        print("cs no",statement.cs_no)

        # Get the logged-in user's name
        user_profile = UserProfile.objects.get(user=statement.created_by)
        user_name = user_profile.first_name + " "+user_profile.last_name

        # Render HTML to string
        html_string = render(request, 'Vouch_rpt_branch/Vouch_rpt_branch.html', {
            'company': company,
            'statement': statement,
            'bookings': bookings,
            'parties':parties,
            'barcode_base64': barcode_base64,
            'user_name': user_name,
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Vouch_rpt_branch_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response
    

class GenerateCashStatementLRPDF(APIView):
    def get(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(CashStatmentLR, id=delivery_no)
        bookings = statement.lr_booking.all()
        # parties = statement.party_billing.all()

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Generate barcode for the delivery_no
        barcode_base64 = generate_barcode(statement.cslr_no)
        print("cslr_no no",statement.cslr_no)

        # Get the logged-in user's name
        user_profile = UserProfile.objects.get(user=statement.created_by)
        user_name = user_profile.first_name +" "+user_profile.last_name

        bill_total=statement.total_amt
        cslr_total_words = num2words(bill_total, lang='en').upper()

        # Render HTML to string
        html_string = render(request, 'Vouch_rpt_branch/Vouch_rpt_branch.html', {
            'company': company,
            'statement': statement,
            'bookings': bookings,
            'cslr_total_words':cslr_total_words,
            'barcode_base64': barcode_base64,
            'user_name': user_name,
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Vouch_rpt_branch_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response
    

# class CreateVoucherReceiptBranchView(APIView):    
#     def post(self, request, *args, **kwargs):
#         data = request.data
#         lr_booking_ids = data.pop('lr_booking', [])
#         party_billing_ids = data.get('party_billing', [])
#         receipt_type = data.get('receipt_type')

#         branch_id = request.data.get("branch_name")
#         memo_no = request.data.get("cs_no")
#         # Validate if branch_id and lr_number are provided
#         if not branch_id or not memo_no:
#             return Response({
#                 "status": "error",
#                 "msg": "Both branch and cs_no are required."
#             }, status=status.HTTP_400_BAD_REQUEST)
#         try:
#             # Convert lr_number to a string and ensure it has at least 5 digits
#             memo_no = str(memo_no).strip()
#             if len(memo_no) < 5:
#                 raise ValueError("Invalid CS Number format.")

#             # Extract the first 5 digits of lr_number
#             lr_branch_code = memo_no[:5]

#             # Fetch the branch using branch_id
#             branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
#             branch_code = branch.branch_code

#             # Validate that the first 5 digits of lr_number match the branch code
#             if lr_branch_code != branch_code:
#                 return Response({
#                     "status": "error",
#                     "msg": "The branch code in CS Number does not match the requested branch."
#                 }, status=status.HTTP_400_BAD_REQUEST)



#         except ValueError as e:
#             return Response({
#                 "status": "error",
#                 "msg": "Invalid cs Number format.",
#                 "error": str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)

#         except BranchMaster.DoesNotExist:
#             return Response({
#                 "status": "error",
#                 "msg": "Branch not found or inactive."
#             }, status=status.HTTP_404_NOT_FOUND)            
        

#         try:
#             # Contra Entry Validation
#             if receipt_type == 3:  # If receipt_type is contra
#                 if lr_booking_ids or party_billing_ids:
#                     return Response({
#                         "msg": "For Contra entry, there is no need for any lr_booking or party_billing. Please remove all of these.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)
#                 else:
#                     if not data.get('to_branch') or not data.get('to_branch_amt'):
#                         return Response({
#                             "msg": "Fields 'to_branch' and 'to_branch_amt' are mandatory when receipt_type is contra .",
#                             "status": "error"
#                         }, status=status.HTTP_400_BAD_REQUEST)
#             else:  # If receipt_type is not contra
#                 if not lr_booking_ids and not party_billing_ids:
#                     return Response({
#                         "msg": "Your receipt_type is not contra, but no lr_booking or party_billing records were provided.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)

#             # Check if lr_booking or party_billing exists, then clear to_branch and to_branch_amt
#             if lr_booking_ids or party_billing_ids:               
#                 data['to_branch'] = None
#                 data['to_branch_amt'] = None  

#             # Validate `date` presence
#             if not data.get('date'):
#                 return Response({
#                     "msg": "The 'date' field is mandatory.",
#                     "status": "error"
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             date = data.get('date')              

#             # Validate each LR_Bokking in the requested list
#             for lr_no in lr_booking_ids:
#                 # Get the LR_Bokking object
#                 try:
#                     lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
#                 except LR_Bokking.DoesNotExist:
#                     return Response({
#                         "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)
                
#                 # Validation 1: Ensure lr_booking is not already associated with an active PartyBilling
#                 if VoucherReceiptBranch.objects.filter(
#                     lr_booking=lr_booking,
#                     is_active=True,
#                     flag=True
#                 ).exists():
#                     return Response({
#                         "msg": f"LR_Bokking with lr_no {lr_no} is already associated with an active Voucher Receipt Branch.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)
                
#                 # Validation 2: Check pay_type               
#                 if int(lr_booking.pay_type_id) != 1 and int(lr_booking.pay_type_id) != 2:
#                     return Response({
#                         "msg": f"LR_Bokking with lr_no {lr_no} has not pay_type 'Paid' or 'TOPAY'.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)
                            
#             # Validate each party_billing in the requested list
#             for party_bill in party_billing_ids:
#                 # Get the LR_Bokking object
#                 try:
#                     party_billing = PartyBilling.objects.get(id=party_bill)
#                 except PartyBilling.DoesNotExist:
#                     return Response({
#                         "message": f"party_billing with lr_no {party_bill} does not exist.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)                
                
#                 # Validation 1: Ensure party_billing is not already associated with an active PartyBilling                
#                 if VoucherReceiptBranch.objects.filter(
#                     party_billing=party_billing,
#                     is_active=True,
#                     flag=True
#                 ).exists():
#                     return Response({
#                         "msg": f"Party_billing with lr_no {party_bill} is already associated with an active Voucher Receipt Branch.",
#                         "status": "error"
#                     }, status=status.HTTP_400_BAD_REQUEST)

                
                
#             # If all validations pass, proceed with creation
#             with transaction.atomic():
#                 serializer = VoucherReceiptBranchSerializer(data=data)
#                 if serializer.is_valid():
#                     voucher_receipt = serializer.save()

#                     # Add LR_Bokking entries to the ManyToMany field
#                     lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
#                     if len(lr_bookings) != len(lr_booking_ids):
#                         raise ValueError("One or more LR_Booking IDs not found.")
#                     voucher_receipt.lr_booking.set(lr_bookings)

#                     # Add LR_Bokking entries to the ManyToMany field
#                     party_billings = PartyBilling.objects.filter(id__in=party_billing_ids)
#                     if len(party_billings) != len(party_billing_ids):
#                         raise ValueError("One or more party_billings IDs not found.")
#                     voucher_receipt.party_billing.set(party_billings)

#                     voucher_receipt.created_by = request.user

#                     # Process the LR_Booking records and update CustomerOutstanding
#                     for lr_no in lr_booking_ids:
#                         try:
#                             # Find the corresponding CustomerOutstanding record
#                             customer_outstanding = CustomerOutstanding.objects.filter(lr_booking__lr_no=lr_no)
#                             for outstanding in customer_outstanding:
#                                 # Remove the lr_booking from this CustomerOutstanding
#                                 outstanding.lr_booking.remove(lr_no)

#                                 # Update the last_credit_date
#                                 outstanding.last_credit_date = timezone.now().date()
#                                 outstanding.save()

#                                 # If no more lr_booking objects exist for this record, set last_credit_date to null
#                                 if not outstanding.lr_booking.exists():
#                                     outstanding.last_credit_date = None
#                                     outstanding.save()

#                         except CustomerOutstanding.DoesNotExist:
#                             pass  # Handle any case where the CustomerOutstanding record doesn't exist                        
                    
#                     # Determine branch_id and amount for credit_operation
#                     if (data.get('to_branch') != None):
#                         branch_id = data.get('to_branch')                     
#                         amount = Decimal(data.get('to_branch_amt'))                     
#                     else:                        
#                         branch_id =data.get('branch_name')                     
#                         amount = Decimal(data.get('totla_amt'))              

#                     # Perform credit operation
#                     cash_book = CashBook()
#                     cash_book.credit_operation(branch_id=branch_id, voucher_id=voucher_receipt.id, date=date, amount=amount)

#                     # Additional Logic: Create VoucherPaymentBranch if `to_branch` is present
#                     if (data.get('to_branch') != None):
#                         # Generate Voucher Number
#                         branch_name = data.get('branch_name')
#                         branch = BranchMaster.objects.get(id=branch_name, is_active=True, flag=True)
#                         branch_code = branch.branch_code
#                         prefix = f"{branch_code}"
#                         last_voucher = VoucherPaymentBranch.objects.filter(
#                             branch_name_id=branch_name,
#                             voucher_no__startswith=prefix
#                         ).exclude(voucher_no__isnull=True).exclude(voucher_no__exact='').order_by('-voucher_no').first()

#                         if last_voucher:
#                             last_sequence_number = int(last_voucher.voucher_no[len(prefix):])
#                             new_voucher_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
#                         else:
#                             new_voucher_no = f"{prefix}00001"

#                         # Create VoucherPaymentBranch Object
#                         remarks = f"Send Payment to {data['to_branch']} branch"
#                         voucher_payment_branch = VoucherPaymentBranch.objects.create(
#                             date=date,
#                             branch_name_id=branch_name,
#                             voucher_no=new_voucher_no,
#                             amount=Decimal(data.get('to_branch_amt')),
#                             created_by=request.user,
#                             remarks=remarks
#                         )

#                         # Perform Debit Operation
#                         cash_book.debit_operation(
#                             branch_id=branch_name,
#                             date=date,
#                             amount=Decimal(data.get('to_branch_amt')),
#                             payment_id=voucher_payment_branch.id
#                         )

#                     response_serializer = VoucherReceiptBranchSerializer(voucher_receipt)
#                     return Response({
#                         "message": "Voucher Receipt Branch created successfully!",
#                         "status": "success",
#                         "data": response_serializer.data
#                     }, status=status.HTTP_201_CREATED)

#                 return Response({
#                     "message": "Failed to create Voucher Receipt Branch",
#                     "status": "error",
#                     "errors": serializer.errors
#                 }, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             return Response({
#                 "message": "An error occurred while creating Voucher Receipt Branch",
#                 "status": "error",
#                 "details": str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)



# class VoucherReceiptBranchRetrieveView(APIView):
#     def post(self, request, *args, **kwargs):
#         # Expecting 'id' in the POST data
#         standard_rate_id = request.data.get('id')

#         # Check if 'id' is provided
#         if not standard_rate_id:
#             return Response({
#                 'message': 'Voucher Receipt Branch ID is required',
#                 'status': 'error'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Fetch the StandardRate instance
#             standard_rate = VoucherReceiptBranch.objects.get(id=standard_rate_id)
#         except VoucherReceiptBranch.DoesNotExist:
#             return Response({
#                 'message': 'Voucher Receipt Branch not found',
#                 'status': 'error'
#             }, status=status.HTTP_404_NOT_FOUND)

#         # Serialize the retrieved instance
#         serializer = VoucherReceiptBranchSerializer(standard_rate)

#         # Return the data with success status
#         return Response({
#             'message': 'Voucher Receipt Branch retrieved successfully',
#             'status': 'success',
#             'data': [serializer.data]
#         }, status=status.HTTP_200_OK)
    


# class VoucherReceiptBranchRetrieveAllView(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
#             branch_id = request.data.get("branch_id")
#             user_profile = UserProfile.objects.get(user=request.user)            
#             allowed_branches = user_profile.branches.all()

#             if not branch_id:
#                 return Response({
#                     "status": "error",
#                     "message": "Branch ID is required."
#                 }, status=status.HTTP_400_BAD_REQUEST)
            
#             # Retrieve all items from the database
#             items = VoucherReceiptBranch.objects.filter(
#                 flag=True
#                 ).filter(
#                 Q(branch_name__in=allowed_branches)
#                 ).filter(
#                 Q(branch_name_id=branch_id)
#                 ).order_by('-id')

#             # Serialize the items data
#             serializer = VoucherReceiptBranchSerializer(items, many=True)

#             # Return a success response with the items data
#             return Response({
#                 "status": "success",
#                 "message": "Items retrieved successfully.",
#                 "data": [serializer.data]
#             }, status=status.HTTP_200_OK)
        
#         except Exception as e:
#             # Handle unexpected exceptions
#             return Response({
#                 "status": "error",
#                 "message": "An unexpected error occurred.",
#                 "error": str(e)  # Include the error message for debugging
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# class VoucherReceiptBranchRetrieveActiveView(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
#             # Filter the queryset for active StandardRate instances
#             queryset = VoucherReceiptBranch.objects.filter(is_active=True,flag=True).order_by('-id')
#             serializer = VoucherReceiptBranchSerializer(queryset, many=True)

#             # Prepare the response data
#             response_data = {
#                 'msg': 'Voucher Receipt Branch retrieved successfully',
#                 'status': 'success',
#                 'data': [serializer.data]
#             }
#             return Response(response_data, status=status.HTTP_200_OK)
        
#         except Exception as e:
#             # Handle unexpected exceptions
#             return Response({
#                 'msg': 'An unexpected error occurred',
#                 'status': 'error',
#                 'error': str(e)  # Include the error message for debugging
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# class VoucherReceiptBranchFilterView(APIView): 
#     def post(self, request, *args, **kwargs):
#         try:
#             # Extract filters from the request body
#             filters = request.data.get("filters", {})
#             if not isinstance(filters, dict):
#                 raise ValidationError("Filters must be a dictionary.")

#             # Apply dynamic filters
#             queryset = apply_filters(VoucherReceiptBranch, filters)

#             # Serialize the filtered data
#             serializer = VoucherReceiptBranchSerializer(queryset, many=True)
#             return Response({"success": True, "data": serializer.data}, status=200)

#         except Exception as e:
#             return Response({"success": False, "error": str(e)}, status=400)


class UpdateVoucherReceiptBranchView(APIView):        
    def post(self, request, *args, **kwargs):
        data = request.data
        delivery_statement_id = data.get('id')  
        lr_booking_ids = data.pop('lr_booking', [])
        party_billing_ids = data.get('party_billing', [])
        receipt_type = data.get('receipt_type')

        if not delivery_statement_id:
            return Response({
                "message": "ID of the Voucher Receipt Branch record is required.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the PartyBilling instance
            try:
                voucher_receipt = VoucherReceiptBranch.objects.get(id=delivery_statement_id, is_active=True, flag=True)
            except VoucherReceiptBranch.DoesNotExist:
                return Response({
                    "message": f"Voucher Receipt Branch with id {delivery_statement_id} does not exist or is inactive.",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)

            # Contra Entry Validation
            if receipt_type == 3:  # If receipt_type is contra
                if lr_booking_ids or party_billing_ids:
                    return Response({
                        "msg": "For Contra entry, there is no need for any lr_booking or party_billing. Please remove all of these.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if not data.get('to_branch') or not data.get('to_branch_amt'):
                        return Response({
                            "msg": "Fields 'to_branch' and 'to_branch_amt' are mandatory when receipt_type is contra .",
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)
            else:  # If receipt_type is not contra
                if not lr_booking_ids and not party_billing_ids:
                    return Response({
                        "msg": "Your receipt_type is not contra, but no lr_booking or party_billing records were provided.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Check if lr_booking or party_billing exists, then clear to_branch and to_branch_amt
            if lr_booking_ids or party_billing_ids:               
                data['to_branch'] = None
                data['to_branch_amt'] = None     

            # Validate `date` presence
            if not data.get('date'):
                return Response({
                    "msg": "The 'date' field is mandatory.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)

            date = data.get('date')      

            # Validate each LR_Bokking in the requested list
            for lr_no in lr_booking_ids:
                # Get the LR_Bokking object
                try:
                    lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
                except LR_Bokking.DoesNotExist:
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validation 1: Ensure lr_booking is not already associated with another active VoucherReceiptBranch
                if VoucherReceiptBranch.objects.filter(
                    lr_booking=lr_booking,
                    is_active=True,
                    flag=True
                ).exclude(id=delivery_statement_id).exists():
                    return Response({
                        "msg": f"LR_Bokking with lr_no {lr_no} is already associated with another active VoucherReceiptBranch.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validation 2: Check pay_type               
                if int(lr_booking.pay_type_id) != 1 and int(lr_booking.pay_type_id) != 2:
                    return Response({
                        "msg": f"LR_Bokking with lr_no {lr_no} has not pay_type 'Paid' or 'TOPAY'.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
             # Validate each party_billing in the requested list
            for party_bill in party_billing_ids:
                # Get the LR_Bokking object
                try:
                    party_billing = PartyBilling.objects.get(id=party_bill)
                except PartyBilling.DoesNotExist:
                    return Response({
                        "message": f"party_billing with lr_no {party_bill} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)                
                
                # Validation 1: Ensure party_billing is not already associated with an active PartyBilling                
                if VoucherReceiptBranch.objects.filter(
                    party_billing=party_billing,
                    is_active=True,
                    flag=True
                ).exclude(id=delivery_statement_id).exists():
                    return Response({
                        "msg": f"Party_billing with lr_no {party_bill} is already associated with an active Voucher Receipt Branch.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)


            # If all validations pass, proceed with the update
            with transaction.atomic():
                # Determine branch_id and amount for credit_operation
                if (data.get('to_branch') != None):
                    branch_id = data.get('to_branch')                     
                    amount = Decimal(data.get('to_branch_amt'))                     
                else:                        
                    branch_id =data.get('branch_name')                     
                    amount = Decimal(data.get('totla_amt')) 

                # Validate `CashBook` Record
                cash_book = CashBook.objects.filter(branch_name_id=branch_id, date=date).first()
                if not cash_book:
                    # Check for last record by branch
                    cash_book = CashBook.objects.filter(branch_name_id=branch_id, date__lt=date).order_by('-date').first()
                    if not cash_book:
                        return Response({
                            "message": "Please check the provided date is Today's date, Beacause No CashBook record found for the branch with match or below the date, to avoid bad effect on cash book this update is restricated.",
                            "status": "error"
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Check for subsequent entries
                subsequent_entries = CashBook.objects.filter(branch_name_id=branch_id, date__gt=cash_book.date).exists()
                difference = 0
                if subsequent_entries:
                    # Handle `to_branch` validation
                    if (data.get('to_branch') != None):
                        if amount != voucher_receipt.to_branch_amt:
                            return Response({
                                "message": "You cannot update `to_branch_amt` Because this date closing balance is present inside next date opening balance.",
                                "status": "error"
                            }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # Handle `totla_amt` validation
                        if amount != voucher_receipt.totla_amt:
                            return Response({
                                "message": "You cannot update `totla_amt` Because this date closing balance is present inside next date opening balance.",
                                "status": "error"
                            }, status=status.HTTP_400_BAD_REQUEST)

                else:
                    # Adjust closing balance for last entry
                    if (data.get('to_branch') != None):
                        difference = amount - voucher_receipt.to_branch_amt
                    else:
                        difference = amount - voucher_receipt.totla_amt

                    cash_book.closing_balance += abs(difference)
                    cash_book.save()

                if (difference != 0):
                    if (data.get('to_branch') != None):
                        # Validate `CashBook` Record
                        cash_book_2 = CashBook.objects.filter(branch_name_id=data.get('branch_name'), date=cash_book.date).first()
                        if not cash_book_2:
                                raise ValueError(f"CashBook record not found for find debit record of sender branch.")
                        # Check for subsequent entries
                        subsequent_entries_2 = CashBook.objects.filter(branch_name_id=data.get('branch_name'), date__gt=cash_book_2.date).exists()
                        if subsequent_entries_2:
                            raise ValueError(f"We can not update this record because based on the Voucher payent debit entry there is next day cashbook present.")
                        print(voucher_receipt.to_branch_amt)
                        voucher_payment = cash_book_2.debit.filter(
                            amount=voucher_receipt.to_branch_amt,
                            remarks=f"Send Payment to {data['to_branch']} branch"
                        ).first()

                        # If no matching record is found, raise an error
                        if not voucher_payment:
                            raise ValueError(f"VoucherPaymentBranch record not found to debit amount.")
                    
                        # Update the `VoucherPaymentBranch` object with the new amount
                        voucher_payment.amount = amount
                        voucher_payment.save()

                        # Calculate the difference between the found `VoucherPaymentBranch` amount and the `amount`
                        difference_2 = voucher_receipt.to_branch_amt - voucher_payment.amount
                        cash_book_2.closing_balance += abs(difference_2)
                        cash_book_2.save()

                serializer = VoucherReceiptBranchSerializer(voucher_receipt, data=data, partial=True)
                if serializer.is_valid():
                    updated_voucher_receipt = serializer.save(updated_by=request.user)

                    # Update LR_Bokking entries in the ManyToMany field
                    if lr_booking_ids:
                        lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                        if len(lr_bookings) != len(lr_booking_ids):
                            raise ValueError("One or more LR_Booking IDs not found.")
                        updated_voucher_receipt.lr_booking.set(lr_bookings)
                    else:
                        # Clear all related LR_Bokking if list is empty
                        updated_voucher_receipt.lr_booking.clear()

                    # Add LR_Bokking entries to the ManyToMany field
                    if party_billing_ids:
                        party_billings = PartyBilling.objects.filter(id__in=party_billing_ids)
                        if len(party_billings) != len(party_billing_ids):
                            raise ValueError("One or more party_billings IDs not found.")
                        updated_voucher_receipt.party_billing.set(party_billings)
                    else:
                        # Clear all related PartyBilling if list is empty
                        updated_voucher_receipt.party_billing.clear()


                    response_serializer = VoucherReceiptBranchSerializer(updated_voucher_receipt)
                    return Response({
                        "message": "Voucher Receipt Branch updated successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_200_OK)

                return Response({
                    "message": "Failed to update Voucher Receipt Branch",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "message": "An error occurred while updating Voucher Receipt Branch",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# class VoucherReceiptBranchSoftDeleteAPIView(APIView):
#     def post(self, request, *args, **kwargs):
#         # Extract ID from request data
#         driver_master_id = request.data.get('id')
        
#         if not driver_master_id:
#             return Response({
#                 'msg': 'ID is required',
#                 'status': 'error',
#                 'data': {}
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             # Retrieve the StandardRate instance
#             instance = VoucherReceiptBranch.objects.get(pk=driver_master_id)
            
#             # Set is_active to False to soft delete
#             instance.flag = False
#             instance.save()
            
#             return Response({
#                 'msg': 'Voucher Receipt Branch deactivated (soft deleted) successfully',
#                 'status': 'success',
#                 'data': {}
#             }, status=status.HTTP_200_OK)
        
#         except VoucherReceiptBranch.DoesNotExist:
#             return Response({
#                 'msg': 'StandardRate not found',
#                 'status': 'error',
#                 'data': {}
#             }, status=status.HTTP_404_NOT_FOUND)
        
# class VoucherReceiptBranchPermanentDeleteAPIView(APIView):
#     def post(self, request, *args, **kwargs):
#         # Extract ID from request data
#         receipt_type_id = request.data.get('id')
        
#         if not receipt_type_id:
#             return Response({
#                 'msg': 'ID is required',
#                 'status': 'error',
#                 'data': {}
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             # Retrieve the StandardRate instance
#             instance = VoucherReceiptBranch.objects.get(pk=receipt_type_id)
            
#             # Permanently delete the instance
#             instance.delete()
            
#             return Response({
#                 'msg': 'Voucher Receipt Branch permanently deleted successfully',
#                 'status': 'success',
#                 'data': {}
#             }, status=status.HTTP_200_OK)
        
#         except VoucherReceiptBranch.DoesNotExist:
#             return Response({
#                 'msg': 'Voucher Receipt Branch not found',
#                 'status': 'error',
#                 'data': {}
#             }, status=status.HTTP_404_NOT_FOUND)


class GenerateMoneyReceiptPDF(APIView):
    def get(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(CashStatmentBill, id=delivery_no)
      
        parties = statement.party_billing.all()

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Generate barcode for the delivery_no
        barcode_base64 = generate_barcode(statement.csbl_no)
        print("mr no",statement.csbl_no)

        # Get the logged-in user's name
        user_profile = UserProfile.objects.get(user=statement.created_by)
        user_name = user_profile.first_name + " "+user_profile.last_name

        bill_total=statement.total_amt
        csbl_total_words = num2words(bill_total, lang='en').upper()
        # Render HTML to string
        html_string = render(request, 'money_rpt/money_rpt.html', {
            'company': company,
            'statement': statement,
            'parties':parties,
            'csbl_total_words':csbl_total_words,
            'barcode_base64': barcode_base64,
            'user_name': user_name,
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=money_rpt_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response




#////////////////////////////////////////////////////////////////////////////////
class GenerateMoneyReceiptNumberViews(APIView):   
    def post(self, request, *args, **kwargs):
        try:
            # Extract branch_id from request data
            branch_id = request.data.get('branch_id')

            if not branch_id:
                response_data = {
                    'msg': 'branch_id is required',
                    'status': 'error',
                    'data': None
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Retrieve and validate the active branch
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Combine the branch code as a prefix
            prefix = f"{branch_code}"

            # Get the last non-null and non-blank mr_no for this branch with matching prefix
            last_money_receipt = MoneyReceipt.objects.filter(
                branch_name_id=branch_id,
                mr_no__startswith=prefix
            ).exclude(mr_no__isnull=True).exclude(mr_no__exact='').order_by('-mr_no').first()

            if last_money_receipt:
                # Extract the numeric part of the last `mr_no` and increment
                last_sequence_number = int(last_money_receipt.mr_no[len(prefix):])
                new_mr_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
            else:
                # Start with the first sequence number if no `mr_no` exists
                new_mr_no = f"{prefix}00001"

            # Successful MR number generation
            response_data = {
                'msg': 'MR number generated successfully',
                'status': 'success',
                'data': {
                    'mr_no': new_mr_no
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            # Handle case where branch doesn't exist
            response_data = {
                'status': 'error',
                'message': 'The specified branch was not found.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            # Handle cases where sequence conversion fails
            response_data = {
                'status': 'error',
                'message': 'An error occurred during MR number generation due to invalid data.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle other unexpected exceptions
            response_data = {
                'status': 'error',
                'message': 'An error occurred while generating the MR number.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CreateMoneyReceiptView(APIView):    
    def post(self, request, *args, **kwargs):
        data = request.data
        lr_booking_ids = data.pop('lr_booking', [])
        party_billing_ids = data.get('party_billing', [])
        pay_type = data.get('pay_type', None)

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("mr_no")
        # Validate if branch_id and lr_number are provided
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and MR no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Convert lr_number to a string and ensure it has at least 5 digits
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid MR Number format.")

            # Extract the first 5 digits of lr_number
            lr_branch_code = memo_no[:5]

            # Fetch the branch using branch_id
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Validate that the first 5 digits of lr_number match the branch code
            if lr_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in MR Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)



        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid MR Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)            
        

        try:
            # Store unique PartyMaster objects
            party_masters = set()

            # Validate each LR_Bokking in the requested list
            for lr_no in lr_booking_ids:
                # Get the LR_Bokking object
                try:
                    lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
                except LR_Bokking.DoesNotExist:
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validation 1: Ensure lr_booking is not already associated with an active MoneyReceipt
                if MoneyReceipt.objects.filter(
                    lr_booking=lr_booking,
                    is_active=True,
                    flag=True
                ).exists():
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} is already associated with an active Money Receipt.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validation 2: Check pay_type               
                if int(lr_booking.pay_type_id) != 1 and int(lr_booking.pay_type_id) != 2:
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} has not pay_type 'Paid' or 'TOPAY'.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Add billing_party to the set
                if lr_booking.billing_party:
                    party_masters.add(lr_booking.billing_party)
                            
            # Validate each party_billing in the requested list
            for party_bill in party_billing_ids:
                # Get the LR_Bokking object
                try:
                    party_billing = PartyBilling.objects.get(id=party_bill)
                except PartyBilling.DoesNotExist:
                    return Response({
                        "message": f"party_billing with id {party_bill} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)                
                
                # Validation 1: Ensure party_billing is not already associated with an active MoneyReceipt                
                if MoneyReceipt.objects.filter(
                    party_billing=party_billing,
                    is_active=True,
                    flag=True
                ).exists():
                    return Response({
                        "message": f"Party_billing with lr_no {party_bill} is already associated with an active MoneyReceipt.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Add billing_party to the set
                if party_billing.billing_party:
                    party_masters.add(party_billing.billing_party)

            # Ensure all billing_party objects are the same
            if len(party_masters) > 1:
                return Response({
                    "message": "All lr_booking and party_billing entries must have the same billing_party.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)                

            # Validation for pay_type-specific fields and ensuring irrelevant fields are blank/null
            if pay_type == "UPI":
                if not data.get("utr_no"):
                    return Response({
                        "message": "For 'UPI' pay_type, 'utr_no' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Ensure unrelated fields are null/blank
                data["rtgs_no"] = None
                # data["bank_name"] = None
                data["check_no"] = None
                data["check_date"] = None

            elif pay_type == "RTGS/NFT":
                if not data.get("rtgs_no"):
                    return Response({
                        "message": "For 'RTGS/NFT' pay_type, 'rtgs_no' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Ensure unrelated fields are null/blank
                data["utr_no"] = None
                # data["bank_name"] = None
                data["check_no"] = None
                data["check_date"] = None

            elif pay_type == "CHECK":
                if not data.get("bank_name"):
                    return Response({
                        "message": "For 'CHECK' pay_type, 'bank_name' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not data.get("check_no"):
                    return Response({
                        "message": "For 'CHECK' pay_type, 'check_no' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not data.get("check_date"):
                    return Response({
                        "message": "For 'CHECK' pay_type, 'check_date' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Ensure unrelated fields are null/blank
                data["utr_no"] = None
                data["rtgs_no"] = None

            else:
                return Response({
                    "message": "Invalid pay_type provided.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)

            # If all validations pass, proceed with creation
            with transaction.atomic():

                # Process the LR_Booking records and update CustomerOutstanding
                for lr_no in lr_booking_ids:
                    try:
                        # Find the corresponding CustomerOutstanding record
                        customer_outstanding = CustomerOutstanding.objects.filter(lr_booking__lr_no=lr_no)
                        for outstanding in customer_outstanding:
                            # Remove the lr_booking from this CustomerOutstanding
                            outstanding.lr_booking.remove(lr_no)

                            # Update the last_credit_date
                            outstanding.last_credit_date = timezone.now().date()
                            outstanding.save()

                            # If no more lr_booking objects exist for this record, set last_credit_date to null
                            if not outstanding.lr_booking.exists():
                                outstanding.last_credit_date = None
                                outstanding.save()

                    except CustomerOutstanding.DoesNotExist:
                        pass  # Handle any case where the CustomerOutstanding record doesn't exist

                serializer = MoneyReceiptSerializer(data=data)
                if serializer.is_valid():
                    money_receipt = serializer.save()

                    # Add LR_Bokking entries to the ManyToMany field
                    lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                    if len(lr_bookings) != len(lr_booking_ids):
                        raise ValueError("One or more LR_Booking IDs not found.")
                    money_receipt.lr_booking.set(lr_bookings)

                    # Add LR_Bokking entries to the ManyToMany field
                    party_billings = PartyBilling.objects.filter(id__in=party_billing_ids)
                    if len(party_billings) != len(party_billing_ids):
                        raise ValueError("One or more party_billings IDs not found.")
                    money_receipt.party_billing.set(party_billings)
                    money_receipt.created_by = request.user

                    response_serializer = MoneyReceiptSerializer(money_receipt)
                    return Response({
                        "message": "Money Receipt created successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    "message": "Failed to create Money Receipt",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "message": "An error occurred while creating Money Receipt",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class MoneyReceiptRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        # Expecting 'id' in the POST data
        standard_rate_id = request.data.get('id')

        # Check if 'id' is provided
        if not standard_rate_id:
            return Response({
                'message': 'Money Receipt ID is required',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the StandardRate instance
            standard_rate = MoneyReceipt.objects.get(id=standard_rate_id)
        except MoneyReceipt.DoesNotExist:
            return Response({
                'message': 'Money Receipt not found',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the retrieved instance
        serializer = MoneyReceiptSerializer(standard_rate)

        # Return the data with success status
        return Response({
            'message': 'Money Receipt retrieved successfully',
            'status': 'success',
            'data': [serializer.data]
        }, status=status.HTTP_200_OK)
    
class MoneyReceiptRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get("branch_id")
            user_profile = UserProfile.objects.get(user=request.user)            
            allowed_branches = user_profile.branches.all()
            if not branch_id:
                return Response({
                    "status": "error",
                    "message": "Branch ID is required."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Retrieve all items from the database
            items = MoneyReceipt.objects.filter(
                flag=True
                ).filter(
                Q(branch_name__in=allowed_branches)
                ).filter(
                Q(branch_name_id=branch_id)
                ).order_by('-id')

            # Serialize the items data
            serializer = MoneyReceiptSerializer(items, many=True)

            # Return a success response with the items data
            return Response({
                "status": "success",
                "message": "Items retrieved successfully.",
                "data": [serializer.data]
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                "status": "error",
                "message": "An unexpected error occurred.",
                "error": str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class MoneyReceiptRetrieveActiveView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Filter the queryset for active StandardRate instances
            queryset = MoneyReceipt.objects.filter(is_active=True,flag=True).order_by('-id')
            serializer = MoneyReceiptSerializer(queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'MoneyReceipt retrieved successfully',
                'status': 'success',
                'data': [serializer.data]
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MoneyReceiptFilterView(APIView): 
    def post(self, request, *args, **kwargs):
        try:
            # Extract filters from the request body
            filters = request.data.get("filters", {})
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(MoneyReceipt, filters)

            # Serialize the filtered data
            serializer = MoneyReceiptSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data}, status=200)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)

class UpdateMoneyReceiptView(APIView):    
    def post(self, request, *args, **kwargs):
        data = request.data
        print("mr update",data)
        delivery_statement_id = data.get('id')  
        lr_booking_ids = data.pop('lr_booking', [])
        party_billing_ids = data.get('party_billing', [])
        pay_type = data.get('pay_type', None)

        if not delivery_statement_id:
            return Response({
                "message": "ID of the Money Receipt record is required.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the PartyBilling instance
            try:
                money_receipt = MoneyReceipt.objects.get(id=delivery_statement_id, is_active=True, flag=True)
            except MoneyReceipt.DoesNotExist:
                return Response({
                    "message": f"Money Receipt with id {delivery_statement_id} does not exist or is inactive.",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)

            # Store unique PartyMaster objects
            party_masters = set()    

            # Validate each LR_Bokking in the requested list
            for lr_no in lr_booking_ids:
                # Get the LR_Bokking object
                try:
                    lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
                except LR_Bokking.DoesNotExist:
                    return Response({
                        "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validation 1: Ensure lr_booking is not already associated with another active VoucherReceiptBranch
                if MoneyReceipt.objects.filter(
                    lr_booking=lr_booking,
                    is_active=True,
                    flag=True
                ).exclude(id=delivery_statement_id).exists():
                    return Response({
                        "msg": f"LR_Bokking with lr_no {lr_no} is already associated with another active MoneyReceipt.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validation 2: Check pay_type               
                if int(lr_booking.pay_type_id) != 1 and int(lr_booking.pay_type_id) != 2:
                    return Response({
                        "msg": f"LR_Bokking with lr_no {lr_no} has not pay_type 'Paid' or 'TOPAY'.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Add billing_party to the set
                if lr_booking.billing_party:
                    party_masters.add(lr_booking.billing_party)
            
             # Validate each party_billing in the requested list
            for party_bill in party_billing_ids:
                # Get the LR_Bokking object
                try:
                    party_billing = PartyBilling.objects.get(id=party_bill)
                except PartyBilling.DoesNotExist:
                    return Response({
                        "message": f"party_billing with lr_no {party_bill} does not exist.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)                
                
                # Validation 1: Ensure party_billing is not already associated with an active PartyBilling                
                if MoneyReceipt.objects.filter(
                    party_billing=party_billing,
                    is_active=True,
                    flag=True
                ).exclude(id=delivery_statement_id).exists():
                    return Response({
                        "msg": f"Party_billing with lr_no {party_bill} is already associated with an active Money Receipt.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Add billing_party to the set
                if party_billing.billing_party:
                    party_masters.add(party_billing.billing_party)

            # Ensure all billing_party objects are the same
            if len(party_masters) > 1:
                return Response({
                    "msg": "All lr_booking and party_billing entries must have the same billing_party.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)               

            # Validation for pay_type-specific fields and ensuring irrelevant fields are blank/null
            if pay_type == "UPI":
                if not data.get("utr_no"):
                    return Response({
                        "msg": "For 'UPI' pay_type, 'utr_no' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Ensure unrelated fields are null/blank
                data["rtgs_no"] = None
                 # data["bank_name"] = None
                data["check_no"] = None
                data["check_date"] = None

            elif pay_type == "RTGS/NFT":
                if not data.get("rtgs_no"):
                    return Response({
                        "msg": "For 'RTGS/NFT' pay_type, 'rtgs_no' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Ensure unrelated fields are null/blank
                data["utr_no"] = None
                 # data["bank_name"] = None
                data["check_no"] = None
                data["check_date"] = None

            elif pay_type == "CHECK":
                if not data.get("bank_name"):
                    return Response({
                        "msg": "For 'CHECK' pay_type, 'bank_name' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not data.get("check_no"):
                    return Response({
                        "msg": "For 'CHECK' pay_type, 'check_no' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not data.get("check_date"):
                    return Response({
                        "msg": "For 'CHECK' pay_type, 'check_date' is required.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Ensure unrelated fields are null/blank
                data["utr_no"] = None
                data["rtgs_no"] = None

            else:
                return Response({
                    "msg": "Invalid pay_type provided.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)

            # If all validations pass, proceed with the update
            with transaction.atomic():
                serializer = MoneyReceiptSerializer(money_receipt, data=data, partial=True)
                if serializer.is_valid():
                    updated_money_receipt = serializer.save(updated_by=request.user)

                    # Update LR_Bokking entries in the ManyToMany field
                    if lr_booking_ids:
                        lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                        if len(lr_bookings) != len(lr_booking_ids):
                            raise ValueError("One or more LR_Booking IDs not found.")
                        updated_money_receipt.lr_booking.set(lr_bookings)
                    else:
                        # Clear all related LR_Bokking if list is empty
                        updated_money_receipt.lr_booking.clear()

                    # Add LR_Bokking entries to the ManyToMany field
                    if party_billing_ids:
                        party_billings = PartyBilling.objects.filter(id__in=party_billing_ids)
                        if len(party_billings) != len(party_billing_ids):
                            raise ValueError("One or more party_billings IDs not found.")
                        updated_money_receipt.party_billing.set(party_billings)
                    else:
                        # Clear all related PartyBilling if list is empty
                        updated_money_receipt.party_billing.clear()

                    response_serializer = MoneyReceiptSerializer(updated_money_receipt)
                    return Response({
                        "message": "Voucher Receipt Branch updated successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_200_OK)

                return Response({
                    "message": "Failed to update Voucher Receipt Branch",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "message": "An error occurred while updating Voucher Receipt Branch",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class MoneyReceiptSoftDeleteAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract ID from request data
        driver_master_id = request.data.get('id')
        
        if not driver_master_id:
            return Response({
                'msg': 'ID is required',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Retrieve the StandardRate instance
            instance = MoneyReceipt.objects.get(pk=driver_master_id)
            
            # Set is_active to False to soft delete
            instance.flag = False
            instance.save()
            
            return Response({
                'msg': 'Money Receipt deactivated (soft deleted) successfully',
                'status': 'success',
                'data': {}
            }, status=status.HTTP_200_OK)
        
        except MoneyReceipt.DoesNotExist:
            return Response({
                'msg': 'Money Receipt not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)
        
class MoneyReceiptPermanentDeleteAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract ID from request data
        receipt_type_id = request.data.get('id')
        
        if not receipt_type_id:
            return Response({
                'msg': 'ID is required',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Retrieve the StandardRate instance
            instance = MoneyReceipt.objects.get(pk=receipt_type_id)
            
            # Permanently delete the instance
            instance.delete()
            
            return Response({
                'msg': 'Money Receipt permanently deleted successfully',
                'status': 'success',
                'data': {}
            }, status=status.HTTP_200_OK)
        
        except MoneyReceipt.DoesNotExist:
            return Response({
                'msg': 'Money Receipt not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)


class VoucherPaymentTypeCreateView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = VoucherPaymentTypeSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response({
                    'status': 'success',
                    'message': 'Voucher Payment Type created successfully.',
                    'data': [serializer.data]
                }, status=status.HTTP_201_CREATED)
            return Response({
                'status': 'error',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentTypeRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherPaymentType.objects.get(pk=gst_id)
            serializer = VoucherPaymentTypeSerializer(instance)
            return Response({'msg': 'Voucher Payment Type retrieved successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
        except VoucherPaymentType.DoesNotExist:
            return Response({'msg': 'Voucher Payment Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class VoucherPaymentTypeRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve all GSTMaster instances where `flag=True`, ordered by `id` in descending order
            instances = VoucherPaymentType.objects.filter(flag=True).order_by('-id')
            serializer = VoucherPaymentTypeSerializer(instances, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Voucher Payment Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving Voucher Payment Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentTypeRetrieveFilteredView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = VoucherPaymentType.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = VoucherPaymentTypeSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered Voucher Payment Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered Voucher Payment Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentTypeUpdateView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherPaymentType.objects.get(pk=gst_id)
            serializer = VoucherPaymentTypeSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response({'msg': 'Voucher Payment Type updated successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
            return Response({'msg': 'Validation failed', 'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except VoucherPaymentType.DoesNotExist:
            return Response({'msg': 'Voucher Payment Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class VoucherPaymentTypeDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherPaymentType.objects.get(pk=gst_id)
            instance.flag = False
            instance.save()
            return Response({'msg': 'Voucher Payment Type soft deleted successfully', 'status': 'success', 'data': {}}, status=status.HTTP_200_OK)
        except VoucherPaymentType.DoesNotExist:
            return Response({'msg': 'Voucher Payment Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)



class GenerateVoucherPaymentBranchPDF(APIView):
    def get(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(VoucherPaymentBranch, voucher_no=delivery_no)

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Generate barcode for the delivery_no
        barcode_base64 = generate_barcode(delivery_no)

        # Get the logged-in user's name
        user_profile = UserProfile.objects.get(user=statement.created_by)
        user_name = user_profile.first_name + " "+user_profile.last_name

        # Render HTML to string
        html_string = render(request, 'Vouch_pay_branch/Vouch_pay_branch.html', {
            'company': company,
            'statement': statement,       
            'barcode_base64': barcode_base64,
            'user_name': user_name,
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Vouch_pay_branch_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response

class GenerateVoucherPaymentBranchVoucherNumberrViews(APIView):   
    def post(self, request, *args, **kwargs):
        print(request.data)
        try:

            branch_id = request.data.get('branch_id')

            if not branch_id:
                response_data = {
                    'msg': 'branch_id are required',
                    'status': 'error',
                    'data': None
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


            # Retrieve and validate the active branch
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Combine the financial year prefix and branch code
            prefix = f"{branch_code}"

            # Get the last non-null and non-blank lr_number for this branch with matching financial year prefix
            last_booking_memo = VoucherPaymentBranch.objects.filter(
                branch_name_id=branch_id,
                voucher_no__startswith=prefix
            ).exclude(voucher_no__isnull=True).exclude(voucher_no__exact='').order_by('-voucher_no').first()

            if last_booking_memo:
                last_sequence_number = int(last_booking_memo.voucher_no[len(prefix):])
                new_delivery_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
            else:
                new_delivery_no = f"{prefix}00001"

            # On successful LR number generation
            response_data = {
                'msg': 'voucher_no number generated successfully',
                'status': 'success',
                'data': {
                    'voucher_no': new_delivery_no
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            # Handle case where FinancialYear or BranchMaster doesn't exist
            response_data = {
                'status': 'error',
                'message': 'The specified branch was not found.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            # Handle cases where lr_number conversion fails or other value-related errors occur
            response_data = {
                'status': 'error',
                'message': 'An error occurred during voucher_no generation due to invalid data.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any other unexpected exceptions
            response_data = {
                'status': 'error',
                'message': 'An error occurred while generating the voucher_no.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentBranchCreateView(APIView):    
    def post(self, request, *args, **kwargs):
        try:
            # Extract and validate required fields
            branch_name = request.data.get('branch_name')
            date = request.data.get('date')
            amount = request.data.get('amount')

            branch_id = request.data.get("branch_name")
            memo_no = request.data.get("voucher_no")
            # Validate if branch_id and lr_number are provided
            if not branch_id or not memo_no:
                return Response({
                    "status": "error",
                    "msg": "Both branch and voucher_no are required."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # Convert lr_number to a string and ensure it has at least 5 digits
                memo_no = str(memo_no).strip()
                if len(memo_no) < 5:
                    raise ValueError("Invalid voucher Number format.")

                # Extract the first 5 digits of lr_number
                lr_branch_code = memo_no[:5]

                # Fetch the branch using branch_id
                branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
                branch_code = branch.branch_code

                # Validate that the first 5 digits of lr_number match the branch code
                if lr_branch_code != branch_code:
                    return Response({
                        "status": "error",
                        "msg": "The branch code in voucher Number does not match the requested branch."
                    }, status=status.HTTP_400_BAD_REQUEST)

            except ValueError as e:
                return Response({
                    "status": "error",
                    "msg": "Invalid voucher Number format.",
                    "error": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

            except BranchMaster.DoesNotExist:
                return Response({
                    "status": "error",
                    "msg": "Branch not found or inactive."
                }, status=status.HTTP_404_NOT_FOUND)

            if not branch_name or not date or not amount:
                return Response({
                    'status': 'error',
                    'message': "Fields 'branch_name', 'date', and 'amount' are mandatory."
                }, status=status.HTTP_400_BAD_REQUEST)

            if Decimal(amount) == 0:
                return Response({
                    'status': 'error',
                    'message': "'amount' cannot be zero."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate the branch exists
            try:
                BranchMaster.objects.get(id=branch_name, is_active=True, flag=True)
            except BranchMaster.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': f"Branch with id {branch_name} does not exist or is inactive."
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = VoucherPaymentBranchSerializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    # Save the VoucherPaymentBranch object
                    voucher_payment_branch = serializer.save(created_by=request.user)

                    # Perform the debit operation using CashBook
                    cash_book = CashBook()
                    cash_book.debit_operation(
                        branch_id=branch_name,
                        date=date,
                        amount=Decimal(amount),
                        payment_id=voucher_payment_branch.id
                    )

                    # Return success response
                    return Response({
                        'status': 'success',
                        'message': 'Voucher Payment Branch created successfully.',
                        'data': [serializer.data]
                    }, status=status.HTTP_201_CREATED)

            return Response({
                'status': 'error',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentBranchRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherPaymentBranch.objects.get(pk=gst_id)
            serializer = VoucherPaymentBranchSerializer(instance)
            return Response({'msg': 'Voucher Payment Branch retrieved successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
        except VoucherPaymentBranch.DoesNotExist:
            return Response({'msg': 'Voucher Payment Branch not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class VoucherPaymentBranchRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get("branch_id")
            user_profile = UserProfile.objects.get(user=request.user)            
            allowed_branches = user_profile.branches.all()
            if not branch_id:
                return Response({
                    "status": "error",
                    "message": "Branch ID is required."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Retrieve all GSTMaster instances where `flag=True`, ordered by `id` in descending order
            instances = VoucherPaymentBranch.objects.filter(
                flag=True
                ).filter(
                Q(branch_name__in=allowed_branches)
                ).filter(
                Q(branch_name_id=branch_id)
                ).order_by('-id')
            serializer = VoucherPaymentBranchSerializer(instances, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Voucher Payment Branch records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving Voucher Payment Branch records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentBranchFilterView(APIView): 
    def post(self, request, *args, **kwargs):
        try:
            # Extract filters from the request body
            filters = request.data.get("filters", {})
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(VoucherPaymentBranch, filters)

            # Serialize the filtered data
            serializer = VoucherPaymentBranchSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data}, status=200)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)

class VoucherPaymentBranchRetrieveFilteredView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = VoucherPaymentBranch.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = VoucherPaymentBranchSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered Voucher Payment Branch records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered Voucher Payment Branch records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoucherPaymentBranchUpdateView(APIView):    
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        branch_name = request.data.get('branch_name')
        date = request.data.get('date')
        amount = request.data.get('amount')

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("voucher_no")
        # Validate if branch_id and lr_number are provided
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and voucher_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert lr_number to a string and ensure it has at least 5 digits
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid voucher Number format.")

            # Extract the first 5 digits of lr_number
            lr_branch_code = memo_no[:5]

            # Fetch the branch using branch_id
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            if lr_branch_code.startswith("24"): 
                lr_branch_code="25" + lr_branch_code[2:]

            # Validate that the first 5 digits of lr_number match the branch code
            if lr_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in voucher Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid voucher Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)
    
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        
        if not branch_name or not date or not amount:
            return Response({
                    'status': 'error',
                    'message': "Fields 'branch_name', 'date', and 'amount' are mandatory."
            }, status=status.HTTP_400_BAD_REQUEST)

        if Decimal(amount) == 0:
            return Response({
                    'status': 'error',
                    'message': "'amount' cannot be zero."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate the branch exists
        try:
            BranchMaster.objects.get(id=branch_name, is_active=True, flag=True)
        except BranchMaster.DoesNotExist:
            return Response({
                    'status': 'error',
                    'message': f"Branch with id {branch_name} does not exist or is inactive."
            }, status=status.HTTP_400_BAD_REQUEST)
                
        try:
            with transaction.atomic():
                instance = VoucherPaymentBranch.objects.get(pk=gst_id)
                if (Decimal(amount)!=instance.amount):
                    # Validate `CashBook` Record
                    cash_book = CashBook.objects.filter(branch_name_id=branch_name, date=date).first()
                    if not cash_book:
                        # Check for last record by branch
                        cash_book = CashBook.objects.filter(branch_name_id=branch_name, date__lt=date).order_by('-date').first()
                        if not cash_book:
                            raise ValueError(f"CashBook record not found for to update debit record.")
                    # Check for subsequent entries
                    subsequent_entries = CashBook.objects.filter(branch_name_id=branch_name, date__gt=cash_book.date).exists()
                    if subsequent_entries:
                        raise ValueError(f"You cannot update the amount because the next day cash book record is based on this VoucherPaymentBranch")
                    
                    difference = Decimal(amount) - instance.amount                  
                    cash_book.closing_balance += abs(difference)
                    cash_book.save()

                serializer = VoucherPaymentBranchSerializer(instance, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save(updated_by=request.user)
                    return Response({'msg': 'Voucher Payment Branch updated successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
                return Response({'msg': 'Validation failed', 'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except VoucherPaymentBranch.DoesNotExist:
            return Response({'msg': 'Voucher Payment Branch not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message": "An error occurred while updating Voucher Payment Branch",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class VoucherPaymentBranchDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = VoucherPaymentBranch.objects.get(pk=gst_id)
            instance.flag = False
            instance.save()
            return Response({'msg': 'Voucher Payment Branch soft deleted successfully', 'status': 'success', 'data': {}}, status=status.HTTP_200_OK)
        except VoucherPaymentBranch.DoesNotExist:
            return Response({'msg': 'Voucher Payment Branch not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)



class CreditOperationAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Extract parameters from the request
            branch_id = request.data.get('branch_id')
            voucher_id = request.data.get('voucher_id')
            date = request.data.get('date')
            amount = request.data.get('amount')

            # Validate input
            if not all([branch_id, voucher_id, date, amount]):
                return Response(
                    {"error": "All parameters (branch_id, voucher_id, date, amount) are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Perform credit operation
            cash_book = CashBook()
            cash_book = cash_book.credit_operation(branch_id, voucher_id, date, Decimal(amount))
            return Response(
                {
                    "message": "Credit operation completed successfully.",
                    "cash_book_id": cash_book.id,
                    "closing_balance": str(cash_book.closing_balance),
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DebitOperationAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Extract parameters from the request
            branch_id = request.data.get('branch_id')
            payment_id = request.data.get('payment_id')
            date = request.data.get('date')
            amount = request.data.get('amount')

            # Validate input
            if not all([branch_id, payment_id, date, amount]):
                return Response(
                    {"error": "All parameters (branch_id, payment_id, date, amount) are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Perform debit operation
            cash_book = CashBook()
            cash_book = cash_book.debit_operation(branch_id, payment_id, date, Decimal(amount))
            return Response(
                {
                    "message": "Debit operation completed successfully.",
                    "cash_book_id": cash_book.id,
                    "closing_balance": str(cash_book.closing_balance),
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateCashBookPDF(APIView):
    def post(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(CashBook, id=delivery_no)
        credits = statement.creditlr.all()
        debits = statement.debit.all()

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Merge credits and debits into a single list, sorted by date
        transactions = list(credits) + list(debits)
        transactions.sort(key=lambda x: x.date)  # Ensure chronological order

        # Calculate running balance
        running_balance = statement.opening_balance
        for txn in transactions:
            if hasattr(txn, 'total_amt'):  # Credit transaction
                running_balance += txn.total_amt
            elif hasattr(txn, 'amount'):  # Debit transaction
                running_balance -= txn.amount
            txn.balance = running_balance  # Attach balance to transaction

        print("transactions",transactions)
        # Generate barcode for the delivery_no
        denominations = request.data.get('denominations', [])
        print("denominations",denominations)
       
        total_cash_in_hand = sum(d['total'] for d in denominations)
      

        barcode_base64 = generate_barcode(delivery_no)

        # Get the logged-in user's name
        user_name = request.user.get_full_name() or request.user.username

        # Render HTML to string
        html_string = render(request, 'cashbook/cashbook.html', {
            'company': company,
            'statement': statement,
            'credits': credits,
            'debits': debits,
            'transactions': transactions,
            'barcode_base64': barcode_base64,
            'user_name': user_name,
            'denominations': denominations, 
            'total_cash_in_hand':total_cash_in_hand
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=cashbook_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response



class CashBookRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        print(request.data)
        try:
            # Extract branch_id and date from request
            branch_id = request.data.get('branch_id')
            date = request.data.get('date')

            # Validate required fields
            if not branch_id or not date:
                return Response({
                    'status': 'error',
                    'message': "Fields 'branch_id' and 'date' are mandatory."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Filter CashBook by branch and date
            cash_book = CashBook.objects.filter(branch_name_id=branch_id, date=date).first()

            if not cash_book:
                cash_book = CashBook.objects.filter(branch_name_id=branch_id, date__gt=date).order_by('date').first()
                if not cash_book:
                    # If no record found, retrieve the last record for the branch
                    cash_book = CashBook.objects.filter(branch_name_id=branch_id, date__lt=date).order_by('-date').first()

                    if not cash_book:
                        return Response({
                            'status': 'error',
                            'message': f"No records found for branch ID {branch_id} on or before {date}."
                        }, status=status.HTTP_404_NOT_FOUND)
                    return Response({
                        'status': 'success',
                        'message': 'CashBook record retrieved successfully.',
                        'data': {
                            "opening_balance": cash_book.closing_balance
                        }
                    }, status=status.HTTP_200_OK)

                # If no record found, retrieve the last record for the branch
                cash_book1 = CashBook.objects.filter(branch_name_id=branch_id, date__lt=date).order_by('-date').first()

                if not cash_book1:
                    return Response({
                        'status': 'error',
                        'message': f"No records found for branch ID {branch_id} on or before {date}."
                    }, status=status.HTTP_404_NOT_FOUND)
                return Response({
                    'status': 'success',
                    'message': 'CashBook record retrieved successfully.',
                    'data': {
                        "opening_balance": cash_book1.closing_balance,
                        "closing_balance": cash_book.opening_balance
                    }
                }, status=status.HTTP_200_OK)

            # Serialize CashBook object
            serializer = CashBookSerializer(cash_book)

            return Response({
                'status': 'success',
                'message': 'CashBook record retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred.',
                'error': str(e)  # Include error for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashBookRetrieveFilterView(APIView):
    def post(self, request, *args, **kwargs):
        print(request.data)
        try:
            # Extract branch_id and date from request
            # branch_id = request.data.get('branch_id')
            date = request.data.get('date')

            filters = request.data.get("filters", {})
            print("filters",filters)
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(CashBook, filters)

            from django.forms.models import model_to_dict


            print("len of q",len(queryset))
            for obj in queryset:
            # queryset_list = [model_to_dict(obj) for obj in queryset]
                print("Queryset dcs:", obj)



            # Validate required fields
            # if  not date:
            #     return Response({
            #         'status': 'error',
            #         'message': "Fields  and 'date' are mandatory."
            #     }, status=status.HTTP_400_BAD_REQUEST)

            # Filter CashBook by branch and date
            # cash_book = CashBook.objects.filter(branch_name_id=branch_id, date=date).first()
            cash_book = queryset.filter(date=date).first()
            

            if not cash_book:
                cash_book = queryset.filter(date__gt=date).order_by('date').first()
                if not cash_book:
                    # If no record found, retrieve the last record for the branch
                    cash_book = queryset.filter(date__lt=date).order_by('-date').first()

                    if not cash_book:
                        return Response({
                            'status': 'error',
                            'message': f"No records found for on or before {date}."
                        }, status=status.HTTP_404_NOT_FOUND)
                    return Response({
                        'status': 'success',
                        'message': 'CashBook record retrieved successfully.',
                        'data': {
                            "opening_balance": cash_book.closing_balance
                        }
                    }, status=status.HTTP_200_OK)

                # If no record found, retrieve the last record for the branch
                cash_book1 = queryset.filter( date__lt=date).order_by('-date').first()

                if not cash_book1:
                    return Response({
                        'status': 'error',
                        'message': f"No records found for branch  on or before {date}."
                    }, status=status.HTTP_404_NOT_FOUND)
                return Response({
                    'status': 'success',
                    'message': 'CashBook record retrieved successfully.',
                    'data': {
                        "opening_balance": cash_book1.closing_balance,
                        "closing_balance": cash_book.opening_balance
                    }
                }, status=status.HTTP_200_OK)

            # Serialize CashBook object
            serializer = CashBookSerializer(cash_book)

            return Response({
                'status': 'success',
                'message': 'CashBook record retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An unexpected error occurred.',
                'error': str(e)  # Include error for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateBillingSubmissionPDF(APIView):
    def get(self, request, delivery_no):
        # Fetch the statement details based on delivery_no
        statement = get_object_or_404(BillingSubmission, sub_no=delivery_no)        


        party = statement.bill_no

        # Fetch company details
        company = get_object_or_404(CompanyMaster, flag=True, is_active=True)

        # Generate barcode for the delivery_no
        barcode_base64 = generate_barcode(delivery_no)

        # Get the logged-in user's name
        user_profile = UserProfile.objects.get(user=statement.created_by)
        user_name = user_profile.first_name + " "+user_profile.last_name

        # Render HTML to string
        html_string = render(request, 'billing_submission/billing_submission.html', {
            'company': company,
            'statement': statement,             
            'barcode_base64': barcode_base64,
            'user_name': user_name,
            'party':party
        }).content.decode('utf-8')

        # Define CSS
        css = CSS(string=''' 
            @page {
                size: A4;
                margin: 5mm;
            }
        ''')

        # Generate PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=[css])

        # Return PDF response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Vouch_pay_branch_{delivery_no}.pdf'

        # Handle branch manager print status
        if request.user.userprofile.role == 'branch_manager':
            if statement.printed_by_branch_manager:
                return Response({"msg": "This statement has already been printed by a branch manager.", 'status': 'error'}, status=400)
            statement.printed_by_branch_manager = True
            statement.save()

        return response

class GenerateBillingSubmissionSubmissionNumberrViews(APIView):   
    def post(self, request, *args, **kwargs):
        print(request.data)
        try:

            branch_id = request.data.get('branch_id')

            if not branch_id:
                response_data = {
                    'msg': 'branch_id are required',
                    'status': 'error',
                    'data': None
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Retrieve and validate the active branch
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Combine the financial year prefix and branch code
            prefix = f"{branch_code}"

            # Get the last non-null and non-blank lr_number for this branch with matching financial year prefix
            last_booking_memo = BillingSubmission.objects.filter(
                branch_name_id=branch_id,
                sub_no__startswith=prefix
            ).exclude(sub_no__isnull=True).exclude(sub_no__exact='').order_by('-sub_no').first()

            if last_booking_memo:
                last_sequence_number = int(last_booking_memo.sub_no[len(prefix):])
                new_delivery_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
            else:
                new_delivery_no = f"{prefix}00001"

            # On successful LR number generation
            response_data = {
                'msg': 'Billing Submission number generated successfully',
                'status': 'success',
                'data': {
                    'sub_no': new_delivery_no
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            # Handle case where FinancialYear or BranchMaster doesn't exist
            response_data = {
                'status': 'error',
                'message': 'The specified branch was not found.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            # Handle cases where lr_number conversion fails or other value-related errors occur
            response_data = {
                'status': 'error',
                'message': 'An error occurred during Billing Submission Number generation due to invalid data.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any other unexpected exceptions
            response_data = {
                'status': 'error',
                'message': 'An error occurred while generating the Billing Submission No.',
                'error': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillingSubmissionCreateView(APIView):    
    def post(self, request, *args, **kwargs):

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("sub_no")
        # Validate if branch_id and lr_number are provided
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and sub_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)


        try:
            # Convert lr_number to a string and ensure it has at least 5 digits
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid submission Number format.")

            # Extract the first 5 digits of lr_number
            lr_branch_code = memo_no[:5]

            # Fetch the branch using branch_id
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            # Validate that the first 5 digits of lr_number match the branch code
            if lr_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in submission Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)



        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid submission Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)            
        
        try:
            # Extract the bill_no from the request data
            bill_no_id = request.data.get('bill_no')

            # Check if a record with the same bill_no, is_active=True, and flag=True exists
            if BillingSubmission.objects.filter(
                bill_no_id=bill_no_id, is_active=True, flag=True
            ).exists():
                # Fetch the existing record to include sub_no in the error message
                existing_submission = BillingSubmission.objects.filter(
                    bill_no_id=bill_no_id, is_active=True, flag=True
                ).first()
                return Response({
                    'status': 'error',
                    'message': f"For {existing_submission.sub_no}, there is already one active bill submitted with the requst bill_no."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Proceed with creation if no conflict is found
            serializer = BillingSubmissionSerializer(data=request.data)
            if serializer.is_valid():
                billing_submission = serializer.save(created_by=request.user)

                try :
                    # Process contact_no fields for consignor and consignee
                    contact_no_list = [
                        billing_submission.bill_no.billing_party.contact_no.strip(),
                        billing_submission.bill_no.billing_party.contact_no.strip()
                    ]
                    
                    standardized_contact_list = []

                    for number in contact_no_list:
                        # Remove any '+' at the beginning
                        if number.startswith('+'):
                            number = number[1:]

                        # If 12 digits, remove the first 2 digits (assume country code)
                        if len(number) == 12:
                            number = number[2:]

                        # Remove "+91" if present
                        if number.startswith("91") and len(number) == 12:
                            number = number[2:]

                        # Ensure the number is now a valid 10-digit number
                        if len(number) == 10 and number.isdigit():
                            standardized_contact_list.append(number)
                        else:
                            print("Invalid phone number: {number}")

                    # Log or process the standardized_contact_list as needed
                    print("Valid phone numbers:", standardized_contact_list)

                    # Example: Send SMS to the validated numbers                
                    send_sms(
                            message=f"Your Bill submitted successfully, with submission number as {billing_submission.sub_no}.",
                            recipient_numbers=standardized_contact_list
                        )
                except Exception as e:                
                    print(f"Failed to send sms: {str(e)}")

                try:
                    # Try to generate PDF and send email
                    pdf_sent = True
                    recipient_list = []
                    email_addresses = [
                        billing_submission.bill_no.billing_party.email_id.strip()
                    ]            
                    for email in email_addresses:
                        try:
                            validate_email(email)  
                            recipient_list.append(email)  
                        except ValidationError:                    
                            continue

                    # Generate PDF
                    lr_no = billing_submission.sub_no
                    pdf_response = GenerateBillingSubmissionPDF().get(request, lr_no)
                    pdf_path = f"/tmp/invoice_{lr_no}.pdf"
                    with open(pdf_path, 'wb') as pdf_file:
                        pdf_file.write(pdf_response.content)

                    # Send email with PDF attachment
                    subject = "Bill Submission Done."
                    message = "Your Bill Submission done successfully. Please find the attached invoice."
                    if recipient_list:
                        send_email_with_attachment(subject, message, recipient_list, pdf_path)

                    # Remove temporary PDF file
                    os.remove(pdf_path)
                except Exception as email_error:
                    pdf_sent = False
                    # Log or handle the error if needed
                    print(f"Failed to send email or generate PDF: {str(email_error)}")

                if pdf_sent:
                    return Response({
                        'status': 'success',
                        'message': 'Billing Submission created successfully.',
                        'data': [serializer.data]
                    }, status=status.HTTP_201_CREATED)
                else :
                    return Response({
                        'status': 'success',
                        'message': 'Billing Submission created successfully, but failed to send email.',
                        'data': [serializer.data]
                    }, status=status.HTTP_201_CREATED)

            # Return validation errors
            return Response({
                'status': 'error',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class BillingSubmissionRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = BillingSubmission.objects.get(pk=gst_id)
            serializer = BillingSubmissionSerializer(instance)
            return Response({'msg': 'Billing Submission retrieved successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
        except BillingSubmission.DoesNotExist:
            return Response({'msg': 'Billing Submission not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class BillingSubmissionRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get("branch_id")
            user_profile = UserProfile.objects.get(user=request.user)            
            allowed_branches = user_profile.branches.all()

            if not branch_id:
                return Response({
                    "status": "error",
                    "message": "Branch ID is required."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Retrieve all GSTMaster instances where `flag=True`, ordered by `id` in descending order
            instances = BillingSubmission.objects.filter(
                flag=True
                ).filter(
                Q(branch_name__in=allowed_branches) 
                ).filter(
                Q(branch_name_id=branch_id)
                ).order_by('-id')
            serializer = BillingSubmissionSerializer(instances, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Billing Submission records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving Billing Submission records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BillingSubmissionRetrieveFilteredView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = BillingSubmission.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = BillingSubmissionSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered Billing Submission records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered Billing Submission records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BillingSubmissionFilterView(APIView): 
    def post(self, request, *args, **kwargs):
        try:
            # Extract filters from the request body
            filters = request.data.get("filters", {})
            print("filters",filters)
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            # Apply dynamic filters
            queryset = apply_filters(BillingSubmission, filters)

            # Serialize the filtered data
            serializer = BillingSubmissionSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data}, status=200)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)

class BillingSubmissionUpdateView(APIView):    
    def post(self, request, *args, **kwargs):

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("sub_no")
        # Validate if branch_id and lr_number are provided
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and sub_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Convert lr_number to a string and ensure it has at least 5 digits
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid submission Number format.")

            # Extract the first 5 digits of lr_number
            lr_branch_code = memo_no[:5]

            # Fetch the branch using branch_id
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code

            if lr_branch_code.startswith("24"): 
                lr_branch_code="25" + lr_branch_code[2:]
            # Validate that the first 5 digits of lr_number match the branch code
            if lr_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in submission Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid submission Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)
        
        gst_id = request.data.get('id')
        if not gst_id:
            return Response(
                {'msg': 'ID is required', 'status': 'error', 'data': {}},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            instance = BillingSubmission.objects.get(pk=gst_id)

            # Extract bill_no from the request data
            bill_no_id = request.data.get('bill_no')
            
            # Check for existing active BillingSubmission records with the same bill_no
            # Ensure the check excludes the current instance being updated
            if bill_no_id and BillingSubmission.objects.filter(
                bill_no_id=bill_no_id, is_active=True, flag=True
            ).exclude(pk=instance.pk).exists():
                existing_submission = BillingSubmission.objects.filter(
                    bill_no_id=bill_no_id, is_active=True, flag=True
                ).exclude(pk=instance.pk).first()
                return Response({
                    'msg': f"For {existing_submission.sub_no}, there is already one active bill submitted.",
                    'status': 'error',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)

            # Proceed with updating the instance
            serializer = BillingSubmissionSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response({
                    'msg': 'Billing Submission updated successfully',
                    'status': 'success',
                    'data': [serializer.data]
                }, status=status.HTTP_200_OK)
            
            # Return validation errors
            return Response({
                'msg': 'Validation failed',
                'status': 'error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except BillingSubmission.DoesNotExist:
            # Handle case where the instance does not exist
            return Response({
                'msg': 'Billing Submission not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)
        
class BillingSubmissionDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = BillingSubmission.objects.get(pk=gst_id)
            instance.flag = False
            instance.save()
            return Response({'msg': 'Billing Submission soft deleted successfully', 'status': 'success', 'data': {}}, status=status.HTTP_200_OK)
        except GSTMaster.DoesNotExist:
            return Response({'msg': 'Billing Submission not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)



class DeductionReasonTypeCreateView(APIView):    
    def post(self, request, *args, **kwargs):
        try:
            serializer = DeductionReasonTypeSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response({
                    'status': 'success',
                    'message': 'Deduction Reason Type created successfully.',
                    'data': [serializer.data]
                }, status=status.HTTP_201_CREATED)
            return Response({
                'status': 'error',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeductionReasonTypeRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = DeductionReasonType.objects.get(pk=gst_id)
            serializer = DeductionReasonTypeSerializer(instance)
            return Response({'msg': 'Deduction Reason Type retrieved successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
        except DeductionReasonType.DoesNotExist:
            return Response({'msg': 'Deduction Reason Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class DeductionReasonTypeRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve all GSTMaster instances where `flag=True`, ordered by `id` in descending order
            instances = DeductionReasonType.objects.filter(flag=True).order_by('-id')
            serializer = DeductionReasonTypeSerializer(instances, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Deduction Reason Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving Deduction Reason Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeductionReasonTypeRetrieveFilteredView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Retrieve active GSTMaster records where `is_active=True` and `flag=True`, ordered by `id` in descending order
            queryset = DeductionReasonType.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = DeductionReasonTypeSerializer(queryset, many=True)

            # Custom response structure
            response_data = {
                'msg': 'Filtered Deduction Reason Type records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': 'An error occurred while retrieving filtered Deduction Reason Type records.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeductionReasonTypeUpdateView(APIView):
    def post(self, request, *args, **kwargs):        
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = DeductionReasonType.objects.get(pk=gst_id)
            serializer = DeductionReasonTypeSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response({'msg': 'Deduction Reason Type updated successfully', 'status': 'success', 'data': [serializer.data]}, status=status.HTTP_200_OK)
            return Response({'msg': 'Validation failed', 'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except DeductionReasonType.DoesNotExist:
            return Response({'msg': 'Deduction Reason Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

class DeductionReasonTypeDeleteView(APIView):
    def post(self, request, *args, **kwargs):
        gst_id = request.data.get('id')
        if not gst_id:
            return Response({'msg': 'ID is required', 'status': 'error', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instance = DeductionReasonType.objects.get(pk=gst_id)
            instance.flag = False
            instance.save()
            return Response({'msg': 'Deduction Reason Type soft deleted successfully', 'status': 'success', 'data': {}}, status=status.HTTP_200_OK)
        except DeductionReasonType.DoesNotExist:
            return Response({'msg': 'Deductio Reason Type not found', 'status': 'error', 'data': {}}, status=status.HTTP_404_NOT_FOUND)


class DeductionView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract fields from the request data
        lr_booking_id = request.data.get("lr_booking")
        party_billing_id = request.data.get("party_billing")
        deduct_amt = Decimal(str(request.data.get("deduct_amt", "0.00")))
        reason_id = request.data.get("reason")
        remarks = request.data.get("remarks", "")
        created_by_id = request.user
        
        
        # Validate the request input
        if not lr_booking_id and not party_billing_id:
            return Response(
                {"msg": "Either 'lr_booking' or 'party_billing' must be provided.", "status": "error", "data": None},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure only one of lr_booking or party_billing is provided
        if lr_booking_id and party_billing_id:
            return Response(
                {"msg": "Only one of 'lr_booking' or 'party_billing' can be provided.", "status": "error", "data": None},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if lr_booking_id:
                # Check if lr_booking is valid
                if str(lr_booking_id).strip() in ["0", "None", "undefined"]:
                    return Response(
                        {"msg": "'lr_booking' is invalid.", "status": "error", "data": None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for existing record
                lr_booking = LR_Bokking.objects.get(lr_no=lr_booking_id)
                deduction = Deduction.objects.filter(lr_booking_id=lr_booking_id).first()
                if deduction:
                    prev_deduct_amt = deduction.deduct_amt or Decimal(0.00)
                    diff = deduct_amt - prev_deduct_amt
                    # if diff > 0:
                    #     lr_booking.grand_total -= diff
                    # else:
                    #     lr_booking.grand_total += abs(diff)

                    # Update existing record
                    deduction.deduct_amt = deduct_amt
                    deduction.reason_id = reason_id
                    deduction.remarks = remarks
                    deduction.updated_by = created_by_id
                    deduction.save()
                    # lr_booking.save()
                    msg = "Deduction updated successfully."
                else:
                    # lr_booking.grand_total = lr_booking.grand_total - deduct_amt
                    # Create a new record
                    deduction = Deduction.objects.create(
                        lr_booking_id=lr_booking_id,
                        deduct_amt=deduct_amt,
                        reason_id=reason_id,
                        remarks=remarks,
                        created_by=created_by_id,
                    )
                    # lr_booking.save()
                    msg = "Deduction created successfully."

            elif party_billing_id:
                # Check if party_billing is valid
                if str(party_billing_id).strip() in ["0", "None", "undefined"]:
                    return Response(
                        {"msg": "'party_billing' is invalid.", "status": "error", "data": None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for existing record
                party_billing = PartyBilling.objects.get(id=party_billing_id)
                deduction = Deduction.objects.filter(party_billing_id=party_billing_id).first()
                if deduction:
                    prev_deduct_amt = deduction.deduct_amt or Decimal(0.00)
                    diff = deduct_amt - prev_deduct_amt
                    # if diff > 0:
                    #     party_billing.totla_amt -= diff
                    # else:
                    #     party_billing.totla_amt += abs(diff)
                    # Update existing record
                    deduction.deduct_amt = deduct_amt
                    deduction.reason_id = reason_id
                    deduction.remarks = remarks
                    deduction.updated_by = created_by_id
                    deduction.save()
                    # party_billing.save()
                    msg = "Deduction updated successfully."
                else:
                    # party_billing.totla_amt -= deduct_amt
                    # Create a new record
                    deduction = Deduction.objects.create(
                        party_billing_id=party_billing_id,
                        deduct_amt=deduct_amt,
                        reason_id=reason_id,
                        remarks=remarks,
                        created_by=created_by_id,
                    )
                    # party_billing.save()
                    msg = "Deduction created successfully."

            # Serialize the deduction object
            serializer = DeductionSerializer(deduction)
            return Response({"msg": msg, "status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"msg": "An error occurred.", "status": "error", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# class DeductionRetrieveView(APIView):
#     def post(self, request, *args, **kwargs):
#         # Extract fields from the request data
#         lr_booking_id = request.data.get("lr_booking")
#         party_billing_id = request.data.get("party_billing")
        
#         # Validate the request input
#         if not lr_booking_id and not party_billing_id:
#             return Response(
#                 {"msg": "Either 'lr_booking' or 'party_billing' must be provided.", "status": "error", "data": None},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Ensure only one of lr_booking or party_billing is provided
#         if lr_booking_id and party_billing_id:
#             return Response(
#                 {"msg": "Only one of 'lr_booking' or 'party_billing' can be provided.", "status": "error", "data": None},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             if lr_booking_id:
#                 # Validate the lr_booking input
#                 if str(lr_booking_id).strip() in ["0", "None", "undefined"]:
#                     return Response(
#                         {"msg": "'lr_booking' is invalid.", "status": "error", "data": None},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
                
#                 # Retrieve record based on lr_booking
#                 deduction = Deduction.objects.filter(lr_booking_id=lr_booking_id).first()
#                 if not deduction:
#                     return Response(
#                         {"msg": "No record found for the provided 'lr_booking'.", "status": "error", "data": None},
#                         status=status.HTTP_404_NOT_FOUND
#                     )
            
#             elif party_billing_id:
#                 # Validate the party_billing input
#                 if str(party_billing_id).strip() in ["0", "None", "undefined"]:
#                     return Response(
#                         {"msg": "'party_billing' is invalid.", "status": "error", "data": None},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
                
#                 # Retrieve record based on party_billing
#                 deduction = Deduction.objects.filter(party_billing_id=party_billing_id).first()
#                 if not deduction:
#                     return Response(
#                         {"msg": "No record found for the provided 'party_billing'.", "status": "error", "data": None},
#                         status=status.HTTP_404_NOT_FOUND
#                     )

#             # Serialize the deduction object
#             serializer = DeductionSerializer(deduction)
#             return Response({"msg": "Deduction retrieved successfully.", "status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response(
#                 {"msg": "An error occurred.", "status": "error", "data": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


class DeductionRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract fields from the request data
        lr_booking_id = request.data.get("lr_booking")
        party_billing_id = request.data.get("party_billing")
        
        # Validate the request input
        if not lr_booking_id and not party_billing_id:
            return Response(
                {"msg": "Either 'lr_booking' or 'party_billing' must be provided.", "status": "error", "data": None},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure only one of lr_booking or party_billing is provided
        if lr_booking_id and party_billing_id:
            return Response(
                {"msg": "Only one of 'lr_booking' or 'party_billing' can be provided.", "status": "error", "data": None},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if lr_booking_id:
                # Validate the lr_booking input
                if str(lr_booking_id).strip() in ["0", "None", "undefined"]:
                    return Response(
                        {"msg": "'lr_booking' is invalid.", "status": "error", "data": None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Retrieve record based on lr_booking
                deduction = Deduction.objects.filter(lr_booking_id=lr_booking_id).first()
                if not deduction:
                    return Response(
                        {"msg": "No record found for the provided 'lr_booking'.", "status": "error", "data": None},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            elif party_billing_id:
                # Validate the party_billing input
                if str(party_billing_id).strip() in ["0", "None", "undefined"]:
                    return Response(
                        {"msg": "'party_billing' is invalid.", "status": "error", "data": None},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Retrieve record based on party_billing
                deduction = Deduction.objects.filter(party_billing_id=party_billing_id).first()
                if not deduction:
                    return Response(
                        {"msg": "No record found for the provided 'party_billing'.", "status": "error", "data": None},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Serialize the deduction object
            serializer = DeductionLRetrieveSerializer(deduction)
            return Response({"msg": "Deduction retrieved successfully.", "status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"msg": "An error occurred.", "status": "error", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






#///////////////////////////////////////////////////////////////////////////////////// 

class CashStatmentLRCreateView(APIView):    
    def post(self, request, *args, **kwargs):
        data = request.data.copy()  
        print("data",data)
        lr_booking_ids = data.pop('lr_booking', [])

        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("cslr_no")
        
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and cslr_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid CS Number format.")
            
            lr_branch_code = memo_no[:5]
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code
            
            if lr_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in CS Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid CS Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
             # **Check if any LR_Bokking is already linked to a CashStatmentLR**
            existing_cs = CashStatmentLR.objects.filter(lr_booking__lr_no__in=lr_booking_ids, is_active=True).exists()
            if existing_cs:
                return Response({
                    "status": "error",
                    "msg": "Cash Statement LR is already created for one or more of the selected LR Bookings."
                }, status=status.HTTP_400_BAD_REQUEST)

            # ///////////////////////
            if not data.get('date'):
                return Response({
                    "msg": "The 'date' field is mandatory.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            date = data.get('date')   
            invalid_lr_numbers = []
            lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
            for lr_booking in lr_bookings:
                if lr_booking.pay_type_id not in [1, 2]:  # Only 'Paid' (1) or 'TOPAY' (2) are allowed
                    invalid_lr_numbers.append(lr_booking.lr_no)

            if invalid_lr_numbers:
                return Response({
                    "status": "error",
                    "msg": f"LR_Bokking(s) with lr_no {', '.join(invalid_lr_numbers)} do not have pay_type 'Paid' or 'TOPAY'."
                }, status=status.HTTP_400_BAD_REQUEST)
            

            with transaction.atomic():
                serializer = CashStatmentLRSerializer(data=data)
                if serializer.is_valid():
                    cash_statement = serializer.save()
                    
                    lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                    if len(lr_bookings) != len(lr_booking_ids):
                        raise ValueError("One or more LR_Booking IDs not found.")
                    cash_statement.lr_booking.set(lr_bookings)
                    
                    cash_statement.created_by = request.user
                    cash_statement.save()

                    for lr_no in lr_booking_ids:
                        try:
                            # Find the corresponding CustomerOutstanding record
                            customer_outstanding = CustomerOutstanding.objects.filter(lr_booking__lr_no=lr_no)
                            for outstanding in customer_outstanding:
                                # Remove the lr_booking from this CustomerOutstanding
                                outstanding.lr_booking.remove(lr_no)

                                # Update the last_credit_date
                                outstanding.last_credit_date = timezone.now().date()
                                outstanding.save()

                                # If no more lr_booking objects exist for this record, set last_credit_date to null
                                if not outstanding.lr_booking.exists():
                                    outstanding.last_credit_date = None
                                    outstanding.save()

                        except CustomerOutstanding.DoesNotExist:
                            pass  # Handle any case where the CustomerOutstanding record doesn't exist   


                    # cashbook entry

                    # Determine branch_id and amount for credit_operation
                                          
                    branch_id =data.get('branch_name')                     
                    amount = Decimal(data.get('total_amt'))     
                     # Perform credit operation
                    cash_book = CashBook()
                    cash_book.credit_operation(branch_id=branch_id, voucher_id=cash_statement.id, date=date, amount=amount)


                    response_serializer = CashStatmentLRSerializer(cash_statement)
                    return Response({
                        "message": "Cash Statement LR created successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    "message": "Failed to create Cash Statement LR",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": "An error occurred while creating Cash Statement LR",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



#////////////////////////////////////////////////////////////////////////////////// 
from datetime import datetime
from decimal import Decimal
class UpdateCashStatementLRView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data.copy()  # Make a mutable copy

        cash_statement_id = data.get('id') 
         
        lr_booking_ids = data.pop('lr_booking', [])


        branch_id = request.data.get("branch_name")
        memo_no = request.data.get("cslr_no")
        
        if not branch_id or not memo_no:
            return Response({
                "status": "error",
                "msg": "Both branch and cslr_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            memo_no = str(memo_no).strip()
            if len(memo_no) < 5:
                raise ValueError("Invalid CS Number format.")
            
            lr_branch_code = memo_no[:5]
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code
            if lr_branch_code.startswith("24"): 
                lr_branch_code="25" + lr_branch_code[2:]
            if lr_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in CS Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid CS Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)
        


        if not cash_statement_id:
            return Response({
                "message": "ID of the Cash Statement LR record is required.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            cash_statement = CashStatmentLR.objects.get(id=cash_statement_id, is_active=True, flag=True)
        except CashStatmentLR.DoesNotExist:
            return Response({
                "message": f"Cash Statement LR with id {cash_statement_id} does not exist or is inactive.",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)

       
        # Validate `date` presence
        if not data.get('date'):
            return Response({
                "message": "The 'date' field is mandatory.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
        date = data.get('date')
        branch_id =data.get('branch_name')                     
        amount = Decimal(data.get('total_amt'))

        # Ensure 'date' is a datetime.date object
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").date()  # Adjust format if necessary

        # Ensure 'branch_id' is an integer
        if isinstance(branch_id, str):
            branch_id = int(branch_id)

        print("date amount branch",cash_statement.date,date,cash_statement.total_amt,amount,cash_statement.branch_name_id,branch_id)
        if (cash_statement.date != date or cash_statement.total_amt != amount or cash_statement.branch_name_id != branch_id):
            print("Date Mismatch:", cash_statement.date, date, type(cash_statement.date), type(date))
            print("Amount Mismatch:", cash_statement.total_amt, amount, type(cash_statement.total_amt), type(amount))
            print("Branch Mismatch:", cash_statement.branch_name_id, branch_id, type(cash_statement.branch_name_id), type(branch_id))

            return Response({
                    "message": "DCS Entry is exist So can not change amount or date or branch of cs.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)

        # Validate each LR_Bokking in the requested list
        for lr_no in lr_booking_ids:
            try:
                lr_booking = LR_Bokking.objects.get(lr_no=lr_no)
            except LR_Bokking.DoesNotExist:
                return Response({
                    "message": f"LR_Bokking with lr_no {lr_no} does not exist.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
        invalid_lr_numbers = []
        lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
        for lr_booking in lr_bookings:
            if lr_booking.pay_type_id not in [1, 2]:  # Only 'Paid' (1) or 'TOPAY' (2) are allowed
                invalid_lr_numbers.append(lr_booking.lr_no)
        if invalid_lr_numbers:
            return Response({
                "status": "error",
                "msg": f"LR_Bokking(s) with lr_no {', '.join(invalid_lr_numbers)} do not have pay_type 'Paid' or 'TOPAY'."
            }, status=status.HTTP_400_BAD_REQUEST)

       

        # ✅ Move `try:` to cover the transaction block
        try:
            with transaction.atomic():
                serializer = CashStatmentLRSerializer(cash_statement, data=data, partial=True)
                if serializer.is_valid():
                    updated_cash_statement = serializer.save(updated_by=request.user)

                    # Update LR_Bokking entries in the ManyToMany field
                    if lr_booking_ids:
                        lr_bookings = LR_Bokking.objects.filter(lr_no__in=lr_booking_ids)
                        updated_cash_statement.lr_booking.set(lr_bookings)
                    else:
                        updated_cash_statement.lr_booking.clear()

                    response_serializer = CashStatmentLRSerializer(updated_cash_statement)
                    for lr_no in lr_booking_ids:
                        try:
                            # Find the corresponding CustomerOutstanding record
                            customer_outstanding = CustomerOutstanding.objects.filter(lr_booking__lr_no=lr_no)
                            for outstanding in customer_outstanding:
                                # Remove the lr_booking from this CustomerOutstanding
                                outstanding.lr_booking.remove(lr_no)

                                # Update the last_credit_date
                                outstanding.last_credit_date = timezone.now().date()
                                outstanding.save()

                                # If no more lr_booking objects exist for this record, set last_credit_date to null
                                if not outstanding.lr_booking.exists():
                                    outstanding.last_credit_date = None
                                    outstanding.save()

                        except CustomerOutstanding.DoesNotExist:
                            pass  # Handle any case where the CustomerOutstanding record doesn't exist   
                    
                    # branch_id =data.get('branch_name')                     
                    # amount = Decimal(data.get('total_amt'))  
                    # cash_book = CashBook.objects.filter(branch_name_id=branch_id, date__lt=date).order_by('-date').first()
                    # if not cash_book:
                    #     return Response({
                    #         "message": "Please check the provided date is Today's date, Beacause No CashBook record found for the branch with match or below the date, to avoid bad effect on cash book this update is restricated.",
                    #         "status": "error"
                    #     }, status=status.HTTP_400_BAD_REQUEST)


                    # subsequent_entries = CashBook.objects.filter(branch_name_id=branch_id, date__gt=cash_book.date).exists()
                    # difference = 0
                    # if subsequent_entries:
                    #     if amount != cash_statement.total_amt:
                    #         return Response({
                    #             "message": "You cannot update `total_amt` Because this date closing balance is present inside next date opening balance.",
                    #             "status": "error"
                    #         }, status=status.HTTP_400_BAD_REQUEST)

                    #  # Perform credit operation
                    # cash_book = CashBook()
                    # cash_book.credit_operation(branch_id=branch_id, voucher_id=cash_statement.id, date=date, amount=amount)



                    return Response({
                        "message": "Cash Statement LR updated successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_200_OK)

                return Response({
                    "message": "Failed to update Cash Statement LR",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:  # ✅ Now correctly placed
            return Response({
                "message": "An error occurred while updating Cash Statement LR",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



#///////////////////////////////////////////////////////////////////////////////////////////////////


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CashStatmentLR
from .serializers import CashStatmentLRSerializer

class CashStatmentLRRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        # Expecting 'id' in the POST data
        cash_statement_id = request.data.get('id')

        # Check if 'id' is provided 
        if not cash_statement_id:
            return Response({
                'message': 'Cash Statement LR ID is required',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the CashStatmentLR instance
            cash_statement = CashStatmentLR.objects.get(id=cash_statement_id, is_active=True, flag=True)
        except CashStatmentLR.DoesNotExist:
            return Response({
                'message': 'Cash Statement LR not found or is inactive',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the retrieved instance
        
        instance = CashStatmentLR.objects.get(pk=cash_statement_id)
        serializer = CashStatmentLRSerializer(instance, context={'request': request})

        # Return the data with success status
        return Response({
            'message': 'Cash Statement LR retrieved successfully',
            'status': 'success',
            'data': [serializer.data]
        }, status=status.HTTP_200_OK)


#//////////////////////////////////////////////////////////////////////////////////////////

class CashStatmentLRRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get("branch_id")
            user_profile = UserProfile.objects.get(user=request.user)            
            allowed_branches = user_profile.branches.all()

            if not branch_id:
                return Response({
                    "status": "error",
                    "message": "Branch ID is required."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Retrieve all CashStatmentLR records for the given branch
            items = CashStatmentLR.objects.filter(
                flag=True, 
                is_active=True
            ).filter(
                Q(branch_name__in=allowed_branches)
            ).filter(
                Q(branch_name_id=branch_id)
            ).order_by('-id')

            # Serialize the items data
            serializer = CashStatmentLRSerializer(items, many=True)

            # Return a success response with the items data
            return Response({
                "status": "success",
                "message": "Cash Statement against LR records retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                "status": "error",
                "message": "An unexpected error occurred.",
                "error": str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# /////////////////////////////////////////////////////////////////////////////////////////////////


class CashStatmentLRRetrieveActiveView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Filter the queryset for active CashStatmentLR instances
            queryset = CashStatmentLR.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = CashStatmentLRSerializer(queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Active Cash Statement LR records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



#////////////////////////////////////////////////////////////////////////////////////////////// 


class CashStatmentLRSoftDeleteAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract ID from request data
        cash_statement_id = request.data.get('id')

        if not cash_statement_id:
            return Response({
                'msg': 'ID is required',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the CashStatmentLR instance
            instance = CashStatmentLR.objects.get(pk=cash_statement_id)

            # Set flag to False for soft delete
            instance.flag = False
            instance.save()

            return Response({
                'msg': 'Cash Statement LR deactivated (soft deleted) successfully',
                'status': 'success',
                'data': {}
            }, status=status.HTTP_200_OK)

        except CashStatmentLR.DoesNotExist:
            return Response({
                'msg': 'Cash Statement LR not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)
        

#/////////////////////////////////////////////////////////////////////////////////////////////////


class GenerateCashStatementLRNumberView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get('branch_id')

            if not branch_id:
                return Response({
                    'msg': 'branch_id is required',
                    'status': 'error',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code
            prefix = f"{branch_code}"

            last_cslr = CashStatmentLR.objects.filter(
                branch_name_id=branch_id,
                cslr_no__startswith=prefix
            ).exclude(cslr_no__isnull=True).exclude(cslr_no__exact='').order_by('-cslr_no').first()

            if last_cslr:
                last_sequence_number = int(last_cslr.cslr_no[len(prefix):])
                new_cslr_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
            else:
                new_cslr_no = f"{prefix}00001"

            return Response({
                'msg': 'CSLR number generated successfully',
                'status': 'success',
                'data': {'cslr_no': new_cslr_no}
            }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response({
                'status': 'error',
                'message': 'The specified branch was not found.',
                'error': 'Branch not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError:
            return Response({
                'status': 'error',
                'message': 'An error occurred during CSLR number generation due to invalid data.',
                'error': 'Invalid data format'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred while generating the CSLR number.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#///////////////////////////////////////////////////////////////////////////////////////


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from .models import CashStatmentBill, BranchMaster

class GenerateCashStatementBillNumberView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get('branch_id')

            if not branch_id:
                return Response({
                    'msg': 'branch_id is required',
                    'status': 'error',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            # Fetch branch
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code
            prefix = f"{branch_code}"

            # Get the last CSBL number for the branch
            last_csbl = CashStatmentBill.objects.filter(
                branch_name_id=branch_id,
                csbl_no__startswith=prefix
            ).exclude(csbl_no__isnull=True).exclude(csbl_no__exact='').order_by('-csbl_no').first()

            # Generate new CSBL number
            if last_csbl:
                last_sequence_number = int(last_csbl.csbl_no[len(prefix):])
                new_csbl_no = f"{prefix}{str(last_sequence_number + 1).zfill(5)}"
            else:
                new_csbl_no = f"{prefix}00001"

            return Response({
                'msg': 'CSBL number generated successfully',
                'status': 'success',
                'data': {'csbl_no': new_csbl_no}
            }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response({
                'status': 'error',
                'message': 'The specified branch was not found.',
                'error': 'Branch not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError:
            return Response({
                'status': 'error',
                'message': 'An error occurred during CSBL number generation due to invalid data.',
                'error': 'Invalid data format'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'An error occurred while generating the CSBL number.',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#/////////////////////////////////////////////////////////////////////////////////////////////////////////////

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from .models import CashStatmentBill, BranchMaster, PartyBilling
from .serializers import CashStatmentBillSerializer  # Create a serializer for CashStatmentBill

class CashStatmentBillCreateView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data.copy()  
        print("Received Data:", data)

        party_billing_ids = data.pop('party_billing', [])

        branch_id = request.data.get("branch_name")
        csbl_no = request.data.get("csbl_no")
        
        if not branch_id or not csbl_no:
            return Response({
                "status": "error",
                "msg": "Both branch and csbl_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            csbl_no = str(csbl_no).strip()
            if len(csbl_no) < 5:
                raise ValueError("Invalid CSBL Number format.")
            
            csbl_branch_code = csbl_no[:5]
            branch = BranchMaster.objects.get(id=branch_id, is_active=True, flag=True)
            branch_code = branch.branch_code
            
            if csbl_branch_code != branch_code:
                return Response({
                    "status": "error",
                    "msg": "The branch code in CSBL Number does not match the requested branch."
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({
                "status": "error",
                "msg": "Invalid CSBL Number format.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except BranchMaster.DoesNotExist:
            return Response({
                "status": "error",
                "msg": "Branch not found or inactive."
            }, status=status.HTTP_404_NOT_FOUND)
        
        pending_billing_ids = []
        flattened_ids = []

        for group in party_billing_ids:
            flattened_ids.extend(group.split(','))

        try:
            for billing_id in flattened_ids:
                print("Processing Party Billing ID:", billing_id)
                exists = BillingSubmission.objects.filter(bill_no_id=billing_id, is_active=True).exists()
                if not exists:
                    pending_billing_ids.append(billing_id)

            #  check for cs done 
            cs_exists = CashStatmentBill.objects.filter(
            party_billing__id=billing_id,
            is_active=True,
            flag=True
            ).exists()
            if cs_exists:
                return Response({
                    "msg": f"Cash Statement already done for party billing ID: {billing_id}",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST) 
            
            if pending_billing_ids:
                return Response({
                    "msg": "BillingSubmission is pending for the following party billing IDs.",
                    "status": "error",
                    "pending_ids": pending_billing_ids
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": "An error occurred while creating Cash Statement Bill",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            if not data.get('date'):
                return Response({
                    "msg": "The 'date' field is mandatory.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                serializer = CashStatmentBillSerializer(data=data)
                if serializer.is_valid():
                    cash_statement_bill = serializer.save()
                    
                    party_billings = PartyBilling.objects.filter(id__in=flattened_ids)
                    print("fff",len(party_billings))
                    print( "kkk", len(flattened_ids))
                    if len(party_billings) != len(flattened_ids):
                        raise ValueError("One or more PartyBilling IDs not found.")
                    
                    

                    
                    cash_statement_bill.party_billing.set(party_billings)
                    cash_statement_bill.created_by = request.user
                    cash_statement_bill.save()
                    
                    response_serializer = CashStatmentBillSerializer(cash_statement_bill)
                    return Response({
                        "message": "Cash Statement Bill created successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    "message": "Failed to create Cash Statement Bill",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": "An error occurred while creating Cash Statement Bill",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# //////////////////////////////////////////////////////////////////////////////////////////
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CashStatmentBill
from .serializers import CashStatmentBillSerializer  # Ensure you have a serializer for CashStatmentBill

class CashStatmentBillRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        # Expecting 'id' in the POST data
        cash_statement_id = request.data.get('id')

        # Check if 'id' is provided 
        if not cash_statement_id:
            return Response({
                'message': 'Cash Statement Bill ID is required',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the CashStatmentBill instance
            cash_statement = CashStatmentBill.objects.get(id=cash_statement_id, is_active=True, flag=True)
        except CashStatmentBill.DoesNotExist:
            return Response({
                'message': 'Cash Statement Bill not found or is inactive',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the retrieved instance
        serializer = CashStatmentBillSerializer(cash_statement,context={'request': request})

        # Return the data with success status
        return Response({
            'message': 'Cash Statement Bill retrieved successfully',
            'status': 'success',
            'data': [serializer.data]
        }, status=status.HTTP_200_OK)

# ////////////////////////////////////////////////////////////////////////////////////////////////////


class CashStatmentBillRetrieveAllView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            branch_id = request.data.get("branch_id")
            user_profile = UserProfile.objects.get(user=request.user)
            allowed_branches = user_profile.branches.all()

            if not branch_id:
                return Response({
                    "status": "error",
                    "message": "Branch ID is required."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Retrieve all CashStatmentBill records for the given branch
            items = CashStatmentBill.objects.filter(
                flag=True, 
                is_active=True
            ).filter(
                Q(branch_name__in=allowed_branches)
            ).filter(
                Q(branch_name_id=branch_id)
            ).order_by('-id')

            # Serialize the items data
            serializer = CashStatmentBillSerializer(items, many=True)

            # Return a success response with the items data
            return Response({
                "status": "success",
                "message": "Cash Statement Bill records retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                "status": "error",
                "message": "An unexpected error occurred.",
                "error": str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# /////////////////////////////////////////////////////////////////////////////////////////////////////////


class CashStatmentBillRetrieveActiveView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Fetch active CashStatmentBill instances
            queryset = CashStatmentBill.objects.filter(is_active=True, flag=True).order_by('-id')
            serializer = CashStatmentBillSerializer(queryset, many=True)

            # Prepare the response data
            response_data = {
                'msg': 'Active Cash Statement Bill records retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle unexpected exceptions
            return Response({
                'msg': 'An unexpected error occurred',
                'status': 'error',
                'error': str(e)  # Include the error message for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ////////////////////////////////////////////////////////////////////////////////////////////////////////////


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import CashStatmentBill, PartyBilling
from .serializers import CashStatmentBillSerializer  # Ensure you have this serializer

class UpdateCashStatementBillView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data.copy()  # ✅ Creates a mutable copy of QueryDict
        flattened_ids = []
        cash_statement_id = data.get('id')  
        party_billing_ids = data.pop('party_billing', [])

        if not cash_statement_id:
            return Response({
                "message": "ID of the Cash Statement Bill record is required.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            cash_statement = CashStatmentBill.objects.get(id=cash_statement_id, is_active=True, flag=True)
        except CashStatmentBill.DoesNotExist:
            return Response({
                "message": f"Cash Statement Bill with id {cash_statement_id} does not exist or is inactive.",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)

        # Validate `date` presence
        if not data.get('date'):
            return Response({
                "message": "The 'date' field is mandatory.",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)


        for group in party_billing_ids:
            flattened_ids.extend(group.split(','))
        # Validate each PartyBilling in the requested list
        for pb_id in flattened_ids:
            try:
                PartyBilling.objects.get(id=pb_id)
            except PartyBilling.DoesNotExist:
                return Response({
                    "message": f"PartyBilling with id {pb_id} does not exist.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)


        pending_billing_ids = []
       

        


        try:
            for billing_id in flattened_ids:
                print("Processing Party Billing ID:", billing_id)
                exists = BillingSubmission.objects.filter(bill_no_id=billing_id, is_active=True).exists()
                if not exists:
                    pending_billing_ids.append(billing_id)

            #  check for cs done 
            cs_exists = CashStatmentBill.objects.filter(
            party_billing__id=billing_id,
            is_active=True,
            flag=True
            ).exclude(id=cash_statement_id).exists()
            if cs_exists:
                return Response({
                    "msg": f"Cash Statement already done for party billing ID: {billing_id}",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST) 
            
            if pending_billing_ids:
                return Response({
                    "msg": "BillingSubmission is pending for the following party billing IDs.",
                    "status": "error",
                    "pending_ids": pending_billing_ids
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": "An error occurred while creating Cash Statement Bill",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


        # ✅ Wrap the update process inside a transaction block
        try:
            with transaction.atomic():
                serializer = CashStatmentBillSerializer(cash_statement, data=data, partial=True)
                if serializer.is_valid():
                    updated_cash_statement = serializer.save(updated_by=request.user)

                    # Update PartyBilling entries in the ManyToMany field
                    if flattened_ids:
                        party_billings = PartyBilling.objects.filter(id__in=flattened_ids)
                        updated_cash_statement.party_billing.set(party_billings)
                    else:
                        updated_cash_statement.party_billing.clear()

                    response_serializer = CashStatmentBillSerializer(updated_cash_statement)
                    return Response({
                        "message": "Cash Statement Bill updated successfully!",
                        "status": "success",
                        "data": response_serializer.data
                    }, status=status.HTTP_200_OK)

                return Response({
                    "message": "Failed to update Cash Statement Bill",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:  # ✅ Now correctly placed
            return Response({
                "message": "An error occurred while updating Cash Statement Bill",
                "status": "error",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ///////////////////////////////////////////////////////////////////////////////////////


class CashStatmentBillSoftDeleteAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract ID from request data
        cash_statement_id = request.data.get('id')

        if not cash_statement_id:
            return Response({
                'msg': 'ID is required',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the CashStatmentBill instance
            instance = CashStatmentBill.objects.get(pk=cash_statement_id)

            # Set flag to False for soft delete
            instance.flag = False
            instance.save()

            return Response({
                'msg': 'Cash Statement Bill deactivated (soft deleted) successfully',
                'status': 'success',
                'data': {}
            }, status=status.HTTP_200_OK)

        except CashStatmentBill.DoesNotExist:
            return Response({
                'msg': 'Cash Statement Bill not found',
                'status': 'error',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)


# //////////////////////////////////////////////////////////////

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import DeductionLR, ChargeHead, LR_Bokking, DeductionReasonType
from .serializers import DeductionLRSerializer, ChargeHeadSerializer
from django.contrib.auth.models import User

# class DeductionLRCreateView(APIView):

#     def post(self, request, *args, **kwargs):
#         try:
#             data = request.data
#             lr_booking_id = data.get("lr_booking")
#             charge_heads_data = data.get("charge_heads", [])

#             # Validate lr_booking existence
#             try:
#                 lr_booking = LR_Bokking.objects.get(lr_no=lr_booking_id)
#             except LR_Bokking.DoesNotExist:
#                 return Response({"error": "Invalid lr_booking ID"}, status=status.HTTP_400_BAD_REQUEST)

#             # Create charge heads and store them in a list
#             charge_heads_instances = []
#             for charge_head in charge_heads_data:
#                 deduction_reason_id = charge_head.get("deduction_reason")

#                 # Validate deduction_reason existence
#                 deduction_reason = None
#                 if deduction_reason_id:
#                     try:
#                         deduction_reason = DeductionReasonType.objects.get(id=deduction_reason_id)
#                     except DeductionReasonType.DoesNotExist:
#                         return Response({"error": f"Invalid deduction_reason ID {deduction_reason_id}"}, 
#                                         status=status.HTTP_400_BAD_REQUEST)

#                 charge_head_instance = ChargeHead.objects.create(
#                     charge_head=charge_head["charge_head"],
#                     amount=charge_head["amount"],
#                     deduction_amount=charge_head["deduction_amount"],
#                     deduction_remark=charge_head.get("deduction_remark", ""),
#                     deduction_reason=deduction_reason,
#                     created_by=User.objects.get(id=1)  # Default user (Modify as needed)
#                 )
#                 charge_heads_instances.append(charge_head_instance)

#             # Create DeductionLR entry
#             deduction_lr = DeductionLR.objects.create(
#                 lr_booking=lr_booking,
#                 # created_by=User.objects.get(id=1)  # Default user (Modify as needed)
#             )
            
#             # Associate ChargeHeads with DeductionLR
#             deduction_lr.charge_heads.set(charge_heads_instances)

#             # Serialize response
#             serializer = DeductionLRSerializer(deduction_lr)
#             serializer.save(created_by=request.user)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ///////////////////////////////////////////////////////////////////////

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import DeductionLR, ChargeHead, LR_Bokking, DeductionReasonType
from .serializers import DeductionLRSerializer, ChargeHeadSerializer
from django.contrib.auth.models import User

class DeductionLRCreateView(APIView):

    def post(self, request, *args, **kwargs):
        """Create a new DeductionLR entry"""
        try:
            data = request.data
            lr_booking_id = data.get("lr_booking")
            print("lr_booking",lr_booking_id)
            charge_heads_data = data.get("charge_heads", [])

            # Validate lr_booking existence
            try:
                lr_booking = LR_Bokking.objects.get(lr_no=lr_booking_id)
                print("lr_booking ddd",lr_booking)
            except LR_Bokking.DoesNotExist:
                return Response({"error": "Invalid lr_booking ID"}, status=status.HTTP_400_BAD_REQUEST)

            print("lr_booking",lr_booking)


            # Create charge heads using serializer
            charge_heads_instances = []
            for charge_head in charge_heads_data:
                charge_head_serializer = ChargeHeadSerializer(data=charge_head)
                if charge_head_serializer.is_valid():
                    charge_head_instance = charge_head_serializer.save(created_by=request.user)
                    charge_heads_instances.append(charge_head_instance)
                else:
                    return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Create DeductionLR entry using serializer
            deduction_lr_serializer = DeductionLRSerializer(data={"lr_booking": lr_booking.lr_no})
            
            if deduction_lr_serializer.is_valid():
                deduction_lr = deduction_lr_serializer.save(created_by=request.user)
                deduction_lr.charge_heads.set(charge_heads_instances)  # Associate ChargeHeads
                return Response(DeductionLRSerializer(deduction_lr).data, status=status.HTTP_201_CREATED)
            else:
                return Response(deduction_lr_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error in lr deduct": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ///////////////////////////////////////////////////////////

# class DeductionLRCreateOrUpdateView(APIView):
#     def post(self, request, *args, **kwargs):
#         """Create or update a DeductionLR entry"""
#         try:
#             data = request.data
#             lr_booking_id = data.get("lr_booking")
#             charge_heads_data = data.get("charge_heads", [])
#             charge_heads_instances = []
#             # Validate lr_booking existence
#             try:
#                 lr_booking = LR_Bokking.objects.get(lr_no=lr_booking_id)
#             except LR_Bokking.DoesNotExist:
#                 return Response({"error": "Invalid lr_booking ID"}, status=status.HTTP_400_BAD_REQUEST)

#             # Check if DeductionLR already exists for the given lr_booking
#             deduction_lr, created = DeductionLR.objects.get_or_create(
#                 lr_booking=lr_booking, defaults={"created_by": request.user}
#             )

            
#             for charge_head in charge_heads_data:
#                 charge_head_id = charge_head.get("id", 0)
#                 deduction_reason_id = charge_head.get("deduction_reason")
#                 deduction_reason = None

#                 if deduction_reason_id:
#                     try:
#                         deduction_reason = DeductionReasonType.objects.get(id=deduction_reason_id)
#                     except DeductionReasonType.DoesNotExist:
#                         return Response({"error": f"Invalid deduction_reason ID {deduction_reason_id}"}, 
#                                         status=status.HTTP_400_BAD_REQUEST)

#                 if charge_head_id and charge_head_id != 0:
#                     # Update existing ChargeHead
#                     try:
#                         charge_head_instance = ChargeHead.objects.get(id=charge_head_id)
#                     except ChargeHead.DoesNotExist:
#                         return Response({"error": f"ChargeHead ID {charge_head_id} not found"},
#                                         status=status.HTTP_400_BAD_REQUEST)
#                     charge_head_serializer = ChargeHeadSerializer(charge_head_instance, data=charge_head, partial=True)
#                 else:
#                     # Create new ChargeHead
#                     charge_head_serializer = ChargeHeadSerializer(data=charge_head)

#                 if charge_head_serializer.is_valid():
#                     charge_head_instance = charge_head_serializer.save(
#                         created_by=request.user if created else charge_head_instance.created_by,
#                         updated_by=request.user if not created else None,
#                         deduction_reason=deduction_reason
#                     )
#                     charge_heads_instances.append(charge_head_instance)
#                 else:
#                     return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#             # Associate ChargeHeads with DeductionLR
#             deduction_lr.charge_heads.set(charge_heads_instances)
#             if not created:
#                 deduction_lr.updated_by = request.user
#             deduction_lr.save()

#             return Response(DeductionLRSerializer(deduction_lr).data, 
#                             status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeductionLRCreateOrUpdateView(APIView):
    def post(self, request, *args, **kwargs):
        """Create or update a DeductionLR entry"""
        try:
            data = request.data
            lr_booking_id = data.get("lr_booking")
            charge_heads_data = data.get("charge_heads", [])

            # Validate lr_booking existence
            try:
                lr_booking = LR_Bokking.objects.get(lr_no=lr_booking_id)
            except LR_Bokking.DoesNotExist:
                return Response({"error": "Invalid lr_booking ID"}, status=status.HTTP_400_BAD_REQUEST)

            # Check if DeductionLR already exists for the given lr_booking
            deduction_lr, created = DeductionLR.objects.get_or_create(
                lr_booking=lr_booking, defaults={"created_by": request.user}
            )

            charge_heads_instances = []
            for charge_head in charge_heads_data:
                charge_head_id = charge_head.get("id", 0)
                deduction_reason_id = charge_head.get("deduction_reason")
                deduction_reason = None
                charge_head_instance = None  # Initialize to avoid reference error

                if deduction_reason_id:
                    try:
                        deduction_reason = DeductionReasonType.objects.get(id=deduction_reason_id)
                    except DeductionReasonType.DoesNotExist:
                        return Response({"error": f"Invalid deduction_reason ID {deduction_reason_id}"}, 
                                        status=status.HTTP_400_BAD_REQUEST)

                if charge_head_id and charge_head_id != 0:
                    # Update existing ChargeHead
                    try:
                        charge_head_instance = ChargeHead.objects.get(id=charge_head_id)
                    except ChargeHead.DoesNotExist:
                        return Response({"error": f"ChargeHead ID {charge_head_id} not found"},
                                        status=status.HTTP_400_BAD_REQUEST)
                    charge_head_serializer = ChargeHeadSerializer(charge_head_instance, data=charge_head, partial=True)
                else:
                    # Create new ChargeHead
                    charge_head_serializer = ChargeHeadSerializer(data=charge_head)

                if charge_head_serializer.is_valid():
                    charge_head_instance = charge_head_serializer.save(
                        created_by=request.user if created or charge_head_id == 0 else charge_head_instance.created_by,
                        updated_by=request.user if not created and charge_head_id != 0 else None,
                        deduction_reason=deduction_reason
                    )
                    charge_heads_instances.append(charge_head_instance)
                else:
                    return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Associate ChargeHeads with DeductionLR
            deduction_lr.charge_heads.set(charge_heads_instances)
            if not created:
                deduction_lr.updated_by = request.user
            deduction_lr.save()

            return Response(DeductionLRSerializer(deduction_lr).data, 
                            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class DeductionLRUpdateView(APIView):

#     def post(self, request, *args, **kwargs):
#         """Update an existing DeductionLR entry"""
#         try:
#             data = request.data
#             deduction_lr_id = data.get("id")
#             charge_heads_data = data.get("charge_heads", [])

#             # Validate DeductionLR existence
#             try:
#                 deduction_lr = DeductionLR.objects.get(id=deduction_lr_id)
#             except DeductionLR.DoesNotExist:
#                 return Response({"error": "DeductionLR not found"}, status=status.HTTP_404_NOT_FOUND)

#             # Clear old ChargeHeads
#             deduction_lr.charge_heads.clear()

#             # Create new ChargeHeads using serializer
#             charge_heads_instances = []
#             for charge_head in charge_heads_data:
#                 charge_head_serializer = ChargeHeadSerializer(data=charge_head)
#                 if charge_head_serializer.is_valid():
#                     charge_head_instance = charge_head_serializer.save(created_by=request.user)
#                     charge_heads_instances.append(charge_head_instance)
#                 else:
#                     return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#             # Update DeductionLR
#             deduction_lr.charge_heads.set(charge_heads_instances)
#             deduction_lr.save()

#             return Response(DeductionLRSerializer(deduction_lr).data, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# //////////////////////////////////////////////////////////


# class DeductionLRUpdateView(APIView):

#     def post(self, request, *args, **kwargs):
#         """Update an existing DeductionLR entry"""
#         try:
#             data = request.data
#             deduction_lr_id = data.get("id")  # Use 'id' instead of 'deduction_lr_id'
#             charge_heads_data = data.get("charge_heads", [])

#             # Validate DeductionLR existence
#             try:
#                 deduction_lr = DeductionLR.objects.get(id=deduction_lr_id)
#             except DeductionLR.DoesNotExist:
#                 return Response({"error": "DeductionLR not found"}, status=status.HTTP_404_NOT_FOUND)

#             # Process ChargeHeads (Update existing & create new)
#             charge_heads_instances = []
#             for charge_head in charge_heads_data:
#                 charge_head_id = charge_head.get("id", 0)

#                 if charge_head_id and charge_head_id != 0:
#                     # Update existing ChargeHead
#                     try:
#                         charge_head_instance = ChargeHead.objects.get(id=charge_head_id)
#                         for key, value in charge_head.items():
#                             if hasattr(charge_head_instance, key):
#                                 setattr(charge_head_instance, key, value)
#                         # charge_head_instance.updated_by = request.user
#                         # charge_head_instance.save()
#                     except ChargeHead.DoesNotExist:
#                         return Response({"error": f"ChargeHead ID {charge_head_id} not found"},
#                                         status=status.HTTP_400_BAD_REQUEST)
#                      # Validate data using serializer before updating
#                     charge_head_serializer = ChargeHeadSerializer(charge_head_instance, data=charge_head, partial=True)
#                     if charge_head_serializer.is_valid():
#                         charge_head_instance = charge_head_serializer.save(updated_by=request.user,
#                                                                            deduction_reason=deduction_reason)
#                 else:
#                     # Create new ChargeHead if id=0
#                     charge_head_serializer = ChargeHeadSerializer(data=charge_head)
#                     if charge_head_serializer.is_valid():
#                         charge_head_instance = charge_head_serializer.save(created_by=request.user)
#                     else:
#                         return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#                 charge_heads_instances.append(charge_head_instance)

#             # Associate updated/new ChargeHeads with DeductionLR
#             deduction_lr.charge_heads.set(charge_heads_instances)
#             deduction_lr.updated_by = request.user
#             deduction_lr.save()

#             return Response(DeductionLRSerializer(deduction_lr).data, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error in update DeductionLR": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeductionLRUpdateView(APIView):
    def post(self, request, *args, **kwargs):
        """Update an existing DeductionLR entry"""
        try:
            data = request.data
            deduction_lr_id = data.get("id")  # DeductionLR ID
            charge_heads_data = data.get("charge_heads", [])

            # Validate DeductionLR existence
            try:
                deduction_lr = DeductionLR.objects.get(id=deduction_lr_id)
            except DeductionLR.DoesNotExist:
                return Response({"error": "DeductionLR not found"}, status=status.HTTP_404_NOT_FOUND)

            # Process ChargeHeads (Update existing & create new)
            charge_heads_instances = []
            for charge_head in charge_heads_data:
                charge_head_id = charge_head.get("id", 0)

                # Fetch DeductionReasonType if provided
                deduction_reason_id = charge_head.get("deduction_reason")
                deduction_reason = None
                if deduction_reason_id:
                    try:
                        deduction_reason = DeductionReasonType.objects.get(id=deduction_reason_id)
                    except DeductionReasonType.DoesNotExist:
                        return Response({"error": f"Invalid deduction_reason ID {deduction_reason_id}"}, 
                                        status=status.HTTP_400_BAD_REQUEST)

                if charge_head_id and charge_head_id != 0:
                    # Update existing ChargeHead
                    try:
                        charge_head_instance = ChargeHead.objects.get(id=charge_head_id)
                    except ChargeHead.DoesNotExist:
                        return Response({"error": f"ChargeHead ID {charge_head_id} not found"},
                                        status=status.HTTP_400_BAD_REQUEST)

                    # Validate data using serializer before updating
                    charge_head_serializer = ChargeHeadSerializer(charge_head_instance, data=charge_head, partial=True)
                    if charge_head_serializer.is_valid():
                        charge_head_instance = charge_head_serializer.save(updated_by=request.user,
                                                                           deduction_reason=deduction_reason)
                    else:
                        return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                else:
                    # Create new ChargeHead if id=0
                    charge_head_serializer = ChargeHeadSerializer(data=charge_head)
                    if charge_head_serializer.is_valid():
                        charge_head_instance = charge_head_serializer.save(
                            created_by=request.user, deduction_reason=deduction_reason
                        )
                    else:
                        return Response(charge_head_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                charge_heads_instances.append(charge_head_instance)

            # Associate updated/new ChargeHeads with DeductionLR
            deduction_lr.charge_heads.set(charge_heads_instances)
            deduction_lr.updated_by = request.user
            deduction_lr.save()

            return Response(DeductionLRSerializer(deduction_lr).data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ///////////////////////////////////////////////////////////////////////

# class DeductionLRRetrieveView(APIView):
#     def post(self, request, *args, **kwargs):
#         """Retrieve DeductionLR by lr_booking using POST method"""
#         try:
#             data = request.data
#             lr_booking_id = data.get("lr_booking")

#             if not lr_booking_id:
#                 return Response({"error": "lr_booking is required"}, status=status.HTTP_400_BAD_REQUEST)

#             # Fetch DeductionLR record with related charge_heads
#             deduction_lr = DeductionLR.objects.prefetch_related('charge_heads').filter(lr_booking__lr_no=lr_booking_id).first()

#             if not deduction_lr:
#                 return Response({"error": "No DeductionLR found for the given lr_booking"}, status=status.HTTP_404_NOT_FOUND)

#             # Serialize response
#             serializer = DeductionLRSerializer(deduction_lr)
#             return Response(serializer.data, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class DeductionLRRetrieveView(APIView):
    def post(self, request, *args, **kwargs):
        """Retrieve DeductionLR by lr_booking using POST method"""
        try:
            data = request.data
            lr_booking_id = data.get("lr_booking")

            if not lr_booking_id:
                return Response({"msg": "lr_booking is required", "status": "error", "data": None}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch DeductionLR record with related charge_heads
            deduction_lr = DeductionLR.objects.prefetch_related('charge_heads').filter(lr_booking__lr_no=lr_booking_id).first()

            if not deduction_lr:
                return Response({"msg": "No DeductionLR found for the given lr_booking", "status": "error", "data": None}, status=status.HTTP_404_NOT_FOUND)

            # Serialize response
            serializer = DeductionLRetrieveSerializer(deduction_lr)
            return Response({"msg": "DeductionLR retrieved successfully", "status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"msg": "An error occurred", "status": "error", "data": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
