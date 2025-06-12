
from django.urls import path

from .views import ItemDetailsMasterCreateView, ItemDetailsMasterPermanentDeleteAPIView, ItemDetailsMasterSoftDeleteAPIView, ItemDetailsMasterUpdateAPIView,QuotationTypesCreateView, QuotationTypesSoftDeleteAPIView, QuotationTypesUpdateAPIView
from .views import ItemDetailsMasterRetrieveView
from .views import ItemDetailsMasterRetrieveAllView
from .views import ItemDetailsMasterRetrieveActiveView
from .views import QuotationTypesRetrieveView
from .views import QuotationTypesRetrieveAllView
from .views import  QuotationTypesRetrieveActiveView
from .views import QuotationTypesPermanentDeleteAPIView,ItemDetailsMasterFilterView
from .views import SubItemDetailsMasterCreateView,SubItemDetailsMasterRetrieveView,SubItemDetailsMasterRetrieveAllView,SubItemDetailsMasterRetrieveActiveView,SubItemDetailsMasterUpdateAPIView,SubItemDetailsMasterFilterView,SubItemDetailsMasterSoftDeleteAPIView,SubItemDetailsMasterPermanentDeleteAPIView

urlpatterns = [

      # URL for listing and creating ItemDetailsMaster
     path('item/create/', ItemDetailsMasterCreateView.as_view(), name='item-details-create'),
     path('retrieve/', ItemDetailsMasterRetrieveView.as_view(), name='item-details-retrieve'),
     path('retrieve_all/', ItemDetailsMasterRetrieveAllView.as_view(), name='item-details-retrieve-all'),
     path('items/retrieve_active/', ItemDetailsMasterRetrieveActiveView.as_view(), name='item-details-retrieve-active'),
     path('items/update/', ItemDetailsMasterUpdateAPIView.as_view(), name='item-details-update'),
     path('items/filter/', ItemDetailsMasterFilterView.as_view(), name='item-details-filter'),
     path('items/soft-delete/', ItemDetailsMasterSoftDeleteAPIView.as_view(), name='item-details-soft-delete'),
     path('items/permanent-delete/', ItemDetailsMasterPermanentDeleteAPIView.as_view(), name='item-details-permanent-delete'),

     # URL for listing and creating SubItemDetailsMaster
     path('sub_item/create/', SubItemDetailsMasterCreateView.as_view(), name='sub_item-details-create'),
     path('sub_retrieve/', SubItemDetailsMasterRetrieveView.as_view(), name='sub_item-details-retrieve'),
     path('sub_retrieve_all/', SubItemDetailsMasterRetrieveAllView.as_view(), name='sub_item-details-retrieve-all'),
     path('sub_items/retrieve_active/', SubItemDetailsMasterRetrieveActiveView.as_view(), name='sub_item-details-retrieve-active'),
     path('sub_items/update/', SubItemDetailsMasterUpdateAPIView.as_view(), name='sub_item-details-update'),
     path('sub_items/filter/', SubItemDetailsMasterFilterView.as_view(), name='sub_item-details-filter'),
     path('sub_items/soft-delete/', SubItemDetailsMasterSoftDeleteAPIView.as_view(), name='sub_item-details-soft-delete'),
     path('sub_items/permanent-delete/', SubItemDetailsMasterPermanentDeleteAPIView.as_view(), name='sub_item-details-permanent-delete'),


      # URL for listing and creating QuotationTypes
     path('quotation-types/create/', QuotationTypesCreateView.as_view(), name='quotation-types-create'),
     path('quotation-types/retrieve/', QuotationTypesRetrieveView.as_view(), name='quotation-types-retrieve'),
     path('quotation-types/retrieve_all/', QuotationTypesRetrieveAllView.as_view(), name='quotation-types-retrieve-all'),
     path('quotation-types/retrieve_active/', QuotationTypesRetrieveActiveView.as_view(), name='quotation-types-retrieve-active'),
     path('quotation-types/update/', QuotationTypesUpdateAPIView.as_view(), name='quotation-types-update'),
     path('quotation-types/soft-delete/', QuotationTypesSoftDeleteAPIView.as_view(), name='quotation-types-soft-delete'),
     path('quotation-types/permanent-delete/', QuotationTypesPermanentDeleteAPIView.as_view(), name='quotation-types-permanent-delete'),

]  
           
    
    