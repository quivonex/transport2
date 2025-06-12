from rest_framework import serializers
from django.contrib.auth import get_user_model
from collection.models import TripMode,TripBokkingMemos,TripMemo
from account.models import PartyBilling,CashStatmentLR,VoucherPaymentBranch
from delivery.models import TruckUnloadingReportStatus,TruckUnloadingReportDetails,DeliveryStatement,TruckUnloadingReport,LocalMemoDelivery
from lr_booking.models import StandardRate, LR_Bokking, LR_Bokking_Description,LR_Other_Charges  
from branches.models import BranchMaster
from vehicals.models import VehicalMaster
from parties.models import PartyMaster
from items.models import QuotationTypes
from transactions.models import CollectionTypes
from transactions.models import DeliveryTypes
from destinations.models import DestinationMaster
from transactions.models import LoadTypes
from transactions.models import PayTypes
from transactions.models import PaidTypes
from items.models import ItemDetailsMaster
from items.serializers import ItemDetailsMasterSerializer
from collection.models import Collection,BookingMemo,BookingMemoLRs

User = get_user_model()

class LR_BokkingDescriptionSerializer(serializers.ModelSerializer):
    # description = ItemDetailsMasterSerializer()
    description=serializers.StringRelatedField()
    sub_description=serializers.StringRelatedField()
    actual_weight = serializers.FloatField()
    charged_weight = serializers.FloatField()
    rate = serializers.FloatField()
    unit_type=serializers.StringRelatedField()

    class Meta:
        model = LR_Bokking_Description
        fields = [
            'id', 'description', 'sub_description','quantity', 'actual_weight', 'charged_weight',
            'unit_type', 'rate', 'challan_no', 'inv_value', 'e_way_bill_no'
        ]


class LRBokkingSerializer(serializers.ModelSerializer):
    descriptions = LR_BokkingDescriptionSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    branch=serializers.StringRelatedField()
    coll_vehicle=serializers.StringRelatedField()
    tran_vehicle=serializers.StringRelatedField()
    from_branch=serializers.StringRelatedField()
    to_branch=serializers.StringRelatedField()
    consignor=serializers.StringRelatedField()
    consignee=serializers.StringRelatedField()
    pay_type=serializers.StringRelatedField()
    billing_party=serializers.StringRelatedField()
    load_type=serializers.StringRelatedField()
    type=serializers.StringRelatedField()
    coll_type=serializers.StringRelatedField()
    del_type=serializers.StringRelatedField()
    coll_at=serializers.StringRelatedField()
    del_at=serializers.StringRelatedField()

    class Meta:
        model = LR_Bokking
        fields = [
            'lr_no', 'branch','lr_number', 'date', 'shedule_date', 'coll_vehicle', 'tran_vehicle', 'del_vehicle', 
            'remark', 'from_branch', 'to_branch', 'consignor', 'consignee', 'pay_type', 
            'billing_party', 'load_type', 'type', 'coll_type', 'del_type', 'coll_at', 
            'del_at','coll_km','del_km', 'descriptions', 'freight', 'e_way_bill_charges', 'collection', 
            'door_delivery', 'toll_escort_total', 'bilty_charges', 'hamali', 
            'godown_charges', 'insurance_charges', 'total', 'other_charge_1','other_charge_1_val',
            'other_charge_2','other_charge_2_val', 'fuel_surcharge', 
            'grand_total','tchargedwt','tpackage','okpackage', 'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active'
        ]
# Serializer for LR_Other_Charges
class LR_Other_ChargesSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = LR_Other_Charges
        fields = [
            'id', 'charges_name', 'created_by', 'created_at', 
            'updated_by', 'updated_at', 'is_active', 'flag'
        ]



class CollectionSerializer(serializers.ModelSerializer):
    branch_name=serializers.StringRelatedField()
    vehical_no=serializers.StringRelatedField()
    driver_name=serializers.StringRelatedField()
    vehical_type=serializers.StringRelatedField()
    from_branch=serializers.StringRelatedField()
    to_branch=serializers.StringRelatedField()
    created_by=serializers.StringRelatedField()
    updated_by=serializers.StringRelatedField()

    class Meta:
        model = Collection
        fields = '__all__'


class BookingMemoLRsSerializer(serializers.ModelSerializer):
    lr_booking = LRBokkingSerializer(read_only=True)
    coll_point=serializers.StringRelatedField()
    del_point=serializers.StringRelatedField()
    created_by=serializers.StringRelatedField()
    updated_by=serializers.StringRelatedField()
    class Meta:
        model = BookingMemoLRs
        fields = [
            'id', 'lr_booking', 'coll_point', 'del_point', 'lr_remarks', 
            'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active'
        ]

class BookingMemoSerializer(serializers.ModelSerializer):
    lr_list = BookingMemoLRsSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    branch_name= serializers.StringRelatedField()
    vehicle_trip_route= serializers.StringRelatedField()
    vehical_no= serializers.StringRelatedField()
    driver_name= serializers.StringRelatedField()
    owner_name= serializers.StringRelatedField()
    from_branch= serializers.StringRelatedField()
    to_branch= serializers.StringRelatedField()
    vehical_type= serializers.StringRelatedField()
    
    class Meta:
        model = BookingMemo
        fields = [
            'id', 'branch_name', 'memo_no', 'date', 'trip_no', 'vehicle_trip_route',
            'vehical_no','vehicle_capacity', 'driver_name', 'contact_no', 'owner_name', 'from_branch',
            'to_branch', 'memo_status', 
            'vehical_type','km', 'memo_remarks', 'lr_list', 'lr_qty', 'total_weight',
            'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active'
        ]


class TripModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripMode
        fields = [
            'id', 'mode_name',
            'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active'
        ]


class TripBokkingMemosSerializer(serializers.ModelSerializer):
    booking_memo = BookingMemoSerializer(read_only=True)
    class Meta:
        model = TripBokkingMemos
        fields = [
            'id', 'booking_memo', 'remark', 
            'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active'
        ]



class TripMemoSerializer(serializers.ModelSerializer):
    booking_memos = TripBokkingMemosSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    branch= serializers.StringRelatedField()
    from_branch= serializers.StringRelatedField()
    to_branch= serializers.StringRelatedField()
    driver_name= serializers.StringRelatedField()
    vehicle_no= serializers.StringRelatedField()
    class Meta:
        model = TripMemo
        fields = [
            'id', 'branch', 'trip_no', 'trip_mode', 'date', 'vehicle_no',
            'driver_name', 'contact_no',
            'from_branch', 'to_branch', 'trip_memo_status', 'remark', 
            'booking_memos', 'km','total_qty','basic_lorry_frights','total_lorry_frights','balance_lorry_frights','total_weight','toll_escort','hamali','other_charger','actual_vehicle_hire','vehicle_hire','waiting','less_advance','less_diesel_amt','less_topay_amt','total_vehicle_hire','balance_vehicle_hire',
            'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active'
        ]






class TruckUnloadingReportStatusSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = TruckUnloadingReportStatus
        fields = '__all__'


class TruckUnloadingReportDetailsSerializer(serializers.ModelSerializer):
    lr_booking = LRBokkingSerializer(read_only=True)
    status = TruckUnloadingReportStatusSerializer(read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = TruckUnloadingReportDetails
        fields = '__all__'


class TruckUnloadingReportSerializer(serializers.ModelSerializer):
    tur_details = TruckUnloadingReportDetailsSerializer(many=True,read_only=True)
    memo_no = BookingMemoSerializer(read_only=True)
    branch_name= serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    class Meta:
        model = TruckUnloadingReport
        fields = '__all__'
   
# //////////////////////////////////////////////////////////////////////////////


class LocalMemoDeliverySerializer(serializers.ModelSerializer):
    lr_booking = LRBokkingSerializer(many=True, read_only=True)
    branch_name= serializers.StringRelatedField()
    vehical_no= serializers.StringRelatedField()
    driver_name= serializers.StringRelatedField()
    to_branch= serializers.StringRelatedField()
    from_branch= serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = LocalMemoDelivery
        fields = '__all__'




class DeliveryStatementSerializer(serializers.ModelSerializer):
    lr_booking = LRBokkingSerializer(many=True, read_only=True)
    branch_name = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    class Meta:
        model = DeliveryStatement
        fields = '__all__'





class PartyBillingSerializer(serializers.ModelSerializer):
    lr_booking = LRBokkingSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    branch_name=serializers.StringRelatedField()
    billing_party=serializers.StringRelatedField()
    class Meta:
        model = PartyBilling
        fields = '__all__'



class CashStatmentLRSerializer(serializers.ModelSerializer):
    lr_booking = LRBokkingSerializer(many=True, read_only=True)
    branch_name= serializers.StringRelatedField()
    party_name= serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

   

    class Meta:
        model = CashStatmentLR
        fields = '__all__'




class VoucherPaymentBranchSerializer(serializers.ModelSerializer):
    # Define fields dynamically for retrieval
    vehical_no = serializers.StringRelatedField()
    lr_no = serializers.StringRelatedField()
    employee = serializers.StringRelatedField()
    party = serializers.StringRelatedField()
    lcm_no = serializers.StringRelatedField()
    booking_memo = serializers.StringRelatedField()
    driver = serializers.StringRelatedField()
    ldm_no = serializers.StringRelatedField()
    trip_no = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = VoucherPaymentBranch
        fields = '__all__'

    



# //////////////////////////////////////////////////////////////////////////////



class StandardRateSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = StandardRate
        fields = [
            'id', 'quotation_date', 'diesel_rate', 'approve_date', 'expiry_date', 'party',
            'from_branch', 'to_branch', 'bilty_charges', 'measurement_type', 'up', 'to', 'rate', 
            'coll_charges', 'del_charges', 'hamali_charges', 'godown_charges', 
            'insurance_charges', 'eway_bill_charges', 'created_by', 'created_at', 
            'updated_by', 'updated_at', 'is_active'
        ]


