#!/usr/bin/env python
"""
Test script to verify AJAX approve/reject functionality
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

def test_ajax_approve_reject():
    """Test the AJAX approve/reject functionality"""
    print("=== Testing AJAX Approve/Reject Functionality ===\n")
    
    # Create test user
    test_user, created = User.objects.get_or_create(
        username='test_applicant_ajax',
        defaults={
            'email': 'applicant_ajax@example.com',
            'first_name': 'Test',
            'last_name': 'Applicant'
        }
    )
    
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(
        user=test_user,
        defaults={'role': 'user'}
    )
    
    # Create test application
    application = HostApplication.objects.create(
        user=test_user,
        business_name='Test Business AJAX',
        business_address='123 Test Street',
        business_phone='+1234567890',
        description='Test application for AJAX testing',
        status='pending'
    )
    
    print(f"✅ Created test application: {application}")
    print(f"   - Status: {application.status}")
    print(f"   - User role: {test_user.userprofile.role}")
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='test_admin_ajax',
        defaults={
            'email': 'admin_ajax@example.com',
            'first_name': 'Test',
            'last_name': 'Admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    # Ensure admin has profile
    admin_profile, created = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={'role': 'admin'}
    )
    admin_profile.role = 'admin'
    admin_profile.save()
    
    # Create test client
    client = Client()
    
    # Login as admin
    client.force_login(admin_user)
    
    print(f"\n✅ Logged in as admin: {admin_user.username}")
    
    # Test AJAX approve view
    print(f"\n--- Testing AJAX Approve View ---")
    approve_url = reverse('approve_host_application', args=[application.id])
    print(f"Approve URL: {approve_url}")
    
    response = client.post(approve_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ AJAX approve view returned success")
                
                # Check if application was approved
                application.refresh_from_db()
                print(f"Application status after approve: {application.status}")
                
                # Check if user role was updated
                test_user.userprofile.refresh_from_db()
                print(f"User role after approve: {test_user.userprofile.role}")
                
                if application.status == 'approved' and test_user.userprofile.role == 'host':
                    print("✅ AJAX approve functionality working correctly!")
                else:
                    print("❌ AJAX approve functionality failed!")
                    return False
            else:
                print(f"❌ AJAX approve returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response.content}")
            return False
    else:
        print(f"❌ AJAX approve view failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Test AJAX reject view (create new application)
    print(f"\n--- Testing AJAX Reject View ---")
    
    # Create another test application
    application2 = HostApplication.objects.create(
        user=test_user,
        business_name='Test Business AJAX 2',
        business_address='456 Test Street',
        business_phone='+1234567890',
        description='Test application for AJAX rejection',
        status='pending'
    )
    
    # Set user back to pending_host
    test_user.userprofile.role = 'pending_host'
    test_user.userprofile.save()
    
    print(f"Created second test application: {application2}")
    print(f"User role set to: {test_user.userprofile.role}")
    
    reject_url = reverse('reject_host_application', args=[application2.id])
    print(f"Reject URL: {reject_url}")
    
    response = client.post(reject_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ AJAX reject view returned success")
                
                # Check if application was rejected
                application2.refresh_from_db()
                print(f"Application status after reject: {application2.status}")
                
                # Check if user role was updated
                test_user.userprofile.refresh_from_db()
                print(f"User role after reject: {test_user.userprofile.role}")
                
                if application2.status == 'rejected' and test_user.userprofile.role == 'user':
                    print("✅ AJAX reject functionality working correctly!")
                else:
                    print("❌ AJAX reject functionality failed!")
                    return False
            else:
                print(f"❌ AJAX reject returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response.content}")
            return False
    else:
        print(f"❌ AJAX reject view failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Clean up
    application.delete()
    application2.delete()
    if test_user.username == 'test_applicant_ajax':
        test_user.delete()
    if admin_user.username == 'test_admin_ajax':
        admin_user.delete()
    
    print(f"\n✅ All AJAX tests passed! Approve/Reject functionality is working correctly.")
    return True

if __name__ == '__main__':
    try:
        success = test_ajax_approve_reject()
        if success:
            print("\n🎉 SUCCESS: The AJAX approve/reject functionality is working correctly!")
            print("\nThe buttons should now:")
            print("1. Show loading state when clicked")
            print("2. Send AJAX request to the server")
            print("3. Update the application status in the database")
            print("4. Show success/error messages")
            print("5. Remove the row from the table on success")
            print("6. Update user roles appropriately")
        else:
            print("\n❌ FAILED: There are issues with the AJAX approve/reject functionality.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc() 