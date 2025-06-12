from django.urls import path
from . import views

urlpatterns = [
    path('gst/create/', views.GSTMasterCreateView.as_view()),
    path('gst/retrieve/', views.GSTMasterRetrieveView.as_view()),
    path('gst/retrieve_all/', views.GSTMasterRetrieveAllView.as_view()),
    path('gst/retrieve_active/', views.GSTMasterRetrieveFilteredView.as_view()),  
    path('gst/update/', views.GSTMasterUpdateView.as_view()),
    path('gst/soft-delete/', views.GSTMasterDeleteView.as_view()),

    path('party_billing/generateBillNumber/', views.GeneratePartyBillingBillNumberViews.as_view(), name='generate_party_billing_number'),
    path('party_billing/create/', views.CreatePartyBillingView.as_view()),
    path('party_billing/retrieve/', views.PartyBillingRetrieveView.as_view()),
    path('party_billing/retrieve_by_bill_no/', views.PartyBillingRetrieveViewBybill_no.as_view()),
    path('party_billing/retrieve_all/', views.PartyBillingRetrieveAllView.as_view()),
    path('party_billing/retrieve_active/', views.PartyBillingRetrieveActiveView.as_view()),
    path('party_billing/retrieve_Vouch_rpt_branch/', views.PartyBillingRetrieveVoucherReceiptView.as_view()),
    path('party_billing/retrieve_Money_rpt/', views.PartyBillingRetrieveMoneyReceiptView.as_view()),
    path('party_billing/retrieve_bill_submission/', views.PartyBillingRetrieveBillingSubmissionView.as_view()),
    path('party_billing/retrieve_CSbill/', views.PartyBillingRetrieveCSBillView.as_view()),
    
    path('party_billing/filter/', views.PartyBillingFilterView.as_view(),name='party_billing-retrieve-filter'),
    path('party_billing/update/', views.UpdatePartyBillingView.as_view()),
    path('party_billing/soft-delete/', views.PartyBillingSoftDeleteAPIView.as_view()),
    path('party_billing/permanent-delete/', views.PartyBillingPermanentDeleteAPIView.as_view()),
    path('party_billing/pending_billing_submission/', views.PartyBillingPendingForBillingSubmission.as_view()),
    path('party_billing/pending_cs/', views.PartyBillingPendingForcs.as_view()),
   
    
    path('Vouch_rpt_Type/create/', views.VoucherReceiptTypeCreateView.as_view()),
    path('Vouch_rpt_Type/retrieve/', views.VoucherReceiptTypeRetrieveView.as_view()),
    path('Vouch_rpt_Type/retrieve_all/', views.VoucherReceiptTypeRetrieveAllView.as_view()),
    path('Vouch_rpt_Type/retrieve_active/', views.VoucherReceiptTypeRetrieveFilteredView.as_view()),
    path('Vouch_rpt_Type/retrieve_money_receipt/', views.VoucherReceiptTypeRetrieveMoneyReceiptView.as_view()),   
    path('Vouch_rpt_Type/update/', views.VoucherReceiptTypeUpdateView.as_view()),
    path('Vouch_rpt_Type/soft-delete/', views.VoucherReceiptTypeDeleteView.as_view()),

    path('money_rpt/generateMRNumber/', views.GenerateMoneyReceiptNumberViews.as_view(), name='generate_mr_number'),
    path('money_rpt/create/', views.CreateMoneyReceiptView.as_view()),
    path('money_rpt/retrieve/', views.MoneyReceiptRetrieveView.as_view()),
    path('money_rpt/retrieve_all/', views.MoneyReceiptRetrieveAllView.as_view()),
    path('money_rpt/retrieve_active/', views.MoneyReceiptRetrieveActiveView.as_view()),
    path('money_rpt/filter/', views.MoneyReceiptFilterView.as_view(), name='Money_rpt_Type-retrieve-filter-lrs'),
    path('money_rpt/update/', views.UpdateMoneyReceiptView.as_view()),
    path('money_rpt/soft-delete/', views.MoneyReceiptSoftDeleteAPIView.as_view()),
    path('money_rpt/permanent-delete/', views.MoneyReceiptPermanentDeleteAPIView.as_view()),   

    path('Vouch_pay_Type/create/', views.VoucherPaymentTypeCreateView.as_view()),
    path('Vouch_pay_Type/retrieve/', views.VoucherPaymentTypeRetrieveView.as_view()),
    path('Vouch_pay_Type/retrieve_all/', views.VoucherPaymentTypeRetrieveAllView.as_view()),
    path('Vouch_pay_Type/retrieve_active/', views.VoucherPaymentTypeRetrieveFilteredView.as_view()),    
    path('Vouch_pay_Type/update/', views.VoucherPaymentTypeUpdateView.as_view()),
    path('Vouch_pay_Type/soft-delete/', views.VoucherPaymentTypeDeleteView.as_view()), 

    path('Vouch_pay_branch/generateVoucherNumber/', views.GenerateVoucherPaymentBranchVoucherNumberrViews.as_view()),
    path('Vouch_pay_branch/create/', views.VoucherPaymentBranchCreateView.as_view()),
    path('Vouch_pay_branch/retrieve/', views.VoucherPaymentBranchRetrieveView.as_view()),
    path('Vouch_pay_branch/retrieve_all/', views.VoucherPaymentBranchRetrieveAllView.as_view()),
    path('Vouch_pay_branch/filter/', views.VoucherPaymentBranchFilterView.as_view(), name='Vouch_pay_branch-retrieve-filter-lrs'),
    path('Vouch_pay_branch/retrieve_active/', views.VoucherPaymentBranchRetrieveFilteredView.as_view()),    
    path('Vouch_pay_branch/update/', views.VoucherPaymentBranchUpdateView.as_view()),
    path('Vouch_pay_branch/soft-delete/', views.VoucherPaymentBranchDeleteView.as_view()), 

    path('cashbook/credit/', views.CreditOperationAPIView.as_view(), name='cashbook-credit'),
    path('cashbook/debit/', views.DebitOperationAPIView.as_view(), name='cashbook-debit'),
    path('cashbook/retrieve/', views.CashBookRetrieveView.as_view()),
    path('cashbook/retrieve/filter', views.CashBookRetrieveFilterView.as_view()),

    path('billing_sub/generateSubNo/', views.GenerateBillingSubmissionSubmissionNumberrViews.as_view()),
    path('billing_sub/create/', views.BillingSubmissionCreateView.as_view()),
    path('billing_sub/retrieve/', views.BillingSubmissionRetrieveView.as_view()),
    path('billing_sub/retrieve_all/', views.BillingSubmissionRetrieveAllView.as_view()),
    path('billing_sub/retrieve_active/', views.BillingSubmissionRetrieveFilteredView.as_view()),
    path('billing_sub/filter/', views.BillingSubmissionFilterView.as_view(), name='party_billing-retrieve-filter-lrs'),
    path('billing_sub/update/', views.BillingSubmissionUpdateView.as_view()),
    path('billing_sub/soft-delete/', views.BillingSubmissionDeleteView.as_view()),


    path('Vouch_rpt_branch/<str:delivery_no>/', views.GenerateCashStatementLRPDF.as_view()),
    path('money_rpt/<str:delivery_no>/', views.GenerateMoneyReceiptPDF.as_view()),
    path('Vouch_pay_branch/<str:delivery_no>/', views.GenerateVoucherPaymentBranchPDF.as_view()),
    path('cashbook/<str:delivery_no>/', views.GenerateCashBookPDF.as_view()),
    path('party_billing/<str:delivery_no>/', views.GeneratePartyBillingPDF.as_view()),
    path('billing_sub/<str:delivery_no>/', views.GenerateBillingSubmissionPDF.as_view()),\
    

    path('deduction_res_Type/create/', views.DeductionReasonTypeCreateView.as_view()),
    path('deduction_res_Type/retrieve/', views.DeductionReasonTypeRetrieveView.as_view()),
    path('deduction_res_Type/retrieve_all/', views.DeductionReasonTypeRetrieveAllView.as_view()),
    path('deduction_res_Type/retrieve_active/', views.DeductionReasonTypeRetrieveFilteredView.as_view()),   
    path('deduction_res_Type/update/', views.DeductionReasonTypeUpdateView.as_view()),
    path('deduction_res_Type/soft-delete/', views.DeductionReasonTypeDeleteView.as_view()),

    path('deduction/save/', views.DeductionView.as_view()),
    path('deduction/retrieve/', views.DeductionRetrieveView.as_view()),


    path('CashStatmentLR/generateCSLRNumber/', views.GenerateCashStatementLRNumberView.as_view(), name='generate_cslr_number'),
    path('CashStatmentLR/create/', views.CashStatmentLRCreateView.as_view()),
    path('CashStatmentLR/retrieve/', views.CashStatmentLRRetrieveView.as_view()),
    path('CashStatmentLR/retrieve_all/', views.CashStatmentLRRetrieveAllView.as_view()),
    path('CashStatmentLR/retrieve_active/', views.CashStatmentLRRetrieveActiveView.as_view()),
    path('CashStatmentLR/update/', views.UpdateCashStatementLRView.as_view()),
    path('CashStatmentLR/soft-delete/', views.CashStatmentLRSoftDeleteAPIView.as_view()),


    path('CashStatmentbill/generateCSblNumber/', views.GenerateCashStatementBillNumberView.as_view(), name='generate_csbl_number'),
    path('CashStatmentbill/create/', views.CashStatmentBillCreateView.as_view()),
    path('CashStatmentbill/retrieve/', views.CashStatmentBillRetrieveView.as_view()),
    path('CashStatmentbill/retrieve_all/', views.CashStatmentBillRetrieveAllView.as_view()),
    path('CashStatmentbill/retrieve_active/', views.CashStatmentBillRetrieveActiveView.as_view()),
    path('CashStatmentbill/update/', views.UpdateCashStatementBillView.as_view()),
    path('CashStatmentbill/soft-delete/', views.CashStatmentBillSoftDeleteAPIView.as_view()),

    path('DeductionLR/create/', views.DeductionLRCreateView.as_view()),
    path('DeductionLR/save/', views.DeductionLRCreateOrUpdateView.as_view()),
    path('DeductionLR/update/', views.DeductionLRUpdateView.as_view()),
    path('DeductionLR/retrive_by_lr_booking/', views.DeductionLRRetrieveView.as_view()),
    

    

]