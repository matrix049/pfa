#!/usr/bin/env python
"""
Debug script to test approve/reject functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

def test_approve_reject_flow():
    """Test the complete approve/reject flow"""
    print("=== Testing Approve/Reject Flow ===\n")
    
    # Create test user
    test_user, created = User.objects.get_or_create(
        username='test_applicant_debug',
        defaults={
            'email': 'applicant_debug@example.com',
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
        business_name='Test Business Debug',
        business_address='123 Test Street',
        business_phone='+1234567890',
        description='Test application for debugging',
        status='pending'
    )
    
    print(f"✅ Created test application: {application}")
    print(f"   - Status: {application.status}")
    print(f"   - User role: {test_user.userprofile.role}")
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='test_admin_debug',
        defaults={
            'email': 'admin_debug@example.com',
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
    
    # Test approve view
    print(f"\n--- Testing Approve View ---")
    approve_url = reverse('approve_host_application', args=[application.id])
    print(f"Approve URL: {approve_url}")
    
    response = client.post(approve_url)
    print(f"Response status: {response.status_code}")
    print(f"Response URL: {response.url}")
    
    if response.status_code == 302:  # Redirect expected
        print("✅ Approve view redirected successfully")
        
        # Check if application was approved
        application.refresh_from_db()
        print(f"Application status after approve: {application.status}")
        
        # Check if user role was updated
        test_user.userprofile.refresh_from_db()
        print(f"User role after approve: {test_user.userprofile.role}")
        
        if application.status == 'approved' and test_user.userprofile.role == 'host':
            print("✅ Approve functionality working correctly!")
        else:
            print("❌ Approve functionality failed!")
            return False
    else:
        print(f"❌ Approve view failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Test reject view (create new application)
    print(f"\n--- Testing Reject View ---")
    
    # Create another test application
    application2 = HostApplication.objects.create(
        user=test_user,
        business_name='Test Business Debug 2',
        business_address='456 Test Street',
        business_phone='+1234567890',
        description='Test application for rejection',
        status='pending'
    )
    
    # Set user back to pending_host
    test_user.userprofile.role = 'pending_host'
    test_user.userprofile.save()
    
    print(f"Created second test application: {application2}")
    print(f"User role set to: {test_user.userprofile.role}")
    
    reject_url = reverse('reject_host_application', args=[application2.id])
    print(f"Reject URL: {reject_url}")
    
    response = client.post(reject_url)
    print(f"Response status: {response.status_code}")
    print(f"Response URL: {response.url}")
    
    if response.status_code == 302:  # Redirect expected
        print("✅ Reject view redirected successfully")
        
        # Check if application was rejected
        application2.refresh_from_db()
        print(f"Application status after reject: {application2.status}")
        
        # Check if user role was updated
        test_user.userprofile.refresh_from_db()
        print(f"User role after reject: {test_user.userprofile.role}")
        
        if application2.status == 'rejected' and test_user.userprofile.role == 'user':
            print("✅ Reject functionality working correctly!")
        else:
            print("❌ Reject functionality failed!")
            return False
    else:
        print(f"❌ Reject view failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Clean up
    application.delete()
    application2.delete()
    if test_user.username == 'test_applicant_debug':
        test_user.delete()
    if admin_user.username == 'test_admin_debug':
        admin_user.delete()
    
    print(f"\n✅ All tests passed! Approve/Reject functionality is working correctly.")
    return True

if __name__ == '__main__':
    try:
        success = test_approve_reject_flow()
        if success:
            print("\n🎉 SUCCESS: The approve/reject functionality is working correctly!")
            print("\nIf buttons still don't work in the browser, the issue might be:")
            print("1. JavaScript errors preventing form submission")
            print("2. CSRF token issues")
            print("3. Network connectivity problems")
            print("4. Browser cache issues")
        else:
            print("\n❌ FAILED: There are issues with the approve/reject functionality.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc() 