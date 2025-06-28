#!/usr/bin/env python
"""
Hands-on test to simulate admin user testing the dashboard approve/reject functionality
"""
import os
import sys
import django
import json
import requests
from urllib.parse import urljoin

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

def test_dashboard_as_admin():
    """Test the dashboard approve/reject functionality as an admin user"""
    print("=== HANDS-ON TEST: Dashboard Approve/Reject as Admin ===\n")
    
    # Create test user (applicant)
    test_user, created = User.objects.get_or_create(
        username='test_applicant_hands_on',
        defaults={
            'email': 'applicant_hands_on@example.com',
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
        business_name='Test Business Hands On',
        business_address='123 Test Street',
        business_phone='+1234567890',
        description='Test application for hands-on testing',
        status='pending'
    )
    
    print(f"✅ Created test application: {application}")
    print(f"   - Status: {application.status}")
    print(f"   - User role: {test_user.userprofile.role}")
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='test_admin_hands_on',
        defaults={
            'email': 'admin_hands_on@example.com',
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
    
    # Set admin password for login
    admin_user.set_password('testpass123')
    admin_user.save()
    
    print(f"\n✅ Created admin user: {admin_user.username}")
    print(f"   - Password: testpass123")
    print(f"   - Role: {admin_user.userprofile.role}")
    
    # Create test client
    client = Client()
    
    # Test 1: Login as admin
    print(f"\n--- Test 1: Login as Admin ---")
    login_url = reverse('login')
    print(f"Login URL: {login_url}")
    
    response = client.post(login_url, {
        'username': 'test_admin_hands_on',
        'password': 'testpass123'
    })
    print(f"Login response status: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ Admin login successful")
    else:
        print(f"❌ Admin login failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Test 2: Access dashboard
    print(f"\n--- Test 2: Access Dashboard ---")
    dashboard_url = reverse('dashboard')
    print(f"Dashboard URL: {dashboard_url}")
    
    response = client.get(dashboard_url)
    print(f"Dashboard response status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Dashboard loads successfully")
        
        # Check if pending applications are in the response
        if hasattr(response, 'context') and response.context and 'pending_applications' in response.context:
            pending_apps = response.context['pending_applications']
            print(f"Found {len(pending_apps)} pending applications in dashboard context")
            
            if len(pending_apps) > 0:
                print("✅ Dashboard shows pending applications")
                for app in pending_apps:
                    print(f"   - {app.user.username}: {app.business_name} (Status: {app.status})")
            else:
                print("❌ Dashboard shows no pending applications")
                return False
        else:
            print("❌ Dashboard context missing 'pending_applications'")
            return False
    else:
        print(f"❌ Dashboard failed to load: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Test 3: Test approve from dashboard (AJAX)
    print(f"\n--- Test 3: Approve from Dashboard (AJAX) ---")
    approve_url = reverse('approve_host_application', args=[application.id])
    print(f"Approve URL: {approve_url}")
    
    # Get CSRF token from the dashboard page
    csrf_token = None
    if hasattr(response, 'context') and response.context:
        csrf_token = response.context.get('csrf_token')
    
    print(f"CSRF Token: {csrf_token}")
    
    # Make AJAX request
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    if csrf_token:
        headers['X-CSRFToken'] = str(csrf_token)
    
    response = client.post(approve_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **headers)
    print(f"Approve response status: {response.status_code}")
    print(f"Approve response headers: {dict(response.headers)}")
    print(f"Approve response content: {response.content}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ Dashboard approve (AJAX) returned success")
                
                # Check if application was approved
                application.refresh_from_db()
                print(f"Application status after approve: {application.status}")
                
                # Check if user role was updated
                test_user.userprofile.refresh_from_db()
                print(f"User role after approve: {test_user.userprofile.role}")
                
                if application.status == 'approved' and test_user.userprofile.role == 'host':
                    print("✅ Dashboard approve functionality working correctly!")
                else:
                    print("❌ Dashboard approve functionality failed!")
                    return False
            else:
                print(f"❌ Dashboard approve returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response.content}")
            return False
    else:
        print(f"❌ Dashboard approve failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Test 4: Test reject from dashboard (AJAX) - create new application
    print(f"\n--- Test 4: Reject from Dashboard (AJAX) ---")
    
    # Create another test application
    application2 = HostApplication.objects.create(
        user=test_user,
        business_name='Test Business Hands On 2',
        business_address='456 Test Street',
        business_phone='+1234567890',
        description='Test application for dashboard rejection',
        status='pending'
    )
    
    # Set user back to pending_host
    test_user.userprofile.role = 'pending_host'
    test_user.userprofile.save()
    
    print(f"Created second test application: {application2}")
    print(f"User role set to: {test_user.userprofile.role}")
    
    reject_url = reverse('reject_host_application', args=[application2.id])
    print(f"Reject URL: {reject_url}")
    
    response = client.post(reject_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **headers)
    print(f"Reject response status: {response.status_code}")
    print(f"Reject response content: {response.content}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ Dashboard reject (AJAX) returned success")
                
                # Check if application was rejected
                application2.refresh_from_db()
                print(f"Application status after reject: {application2.status}")
                
                # Check if user role was updated
                test_user.userprofile.refresh_from_db()
                print(f"User role after reject: {test_user.userprofile.role}")
                
                if application2.status == 'rejected' and test_user.userprofile.role == 'user':
                    print("✅ Dashboard reject functionality working correctly!")
                else:
                    print("❌ Dashboard reject functionality failed!")
                    return False
            else:
                print(f"❌ Dashboard reject returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response.content}")
            return False
    else:
        print(f"❌ Dashboard reject failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Test 5: Test regular form submission (non-AJAX)
    print(f"\n--- Test 5: Regular Form Submission (Non-AJAX) ---")
    
    # Create third test application
    application3 = HostApplication.objects.create(
        user=test_user,
        business_name='Test Business Hands On 3',
        business_address='789 Test Street',
        business_phone='+1234567890',
        description='Test application for regular form submission',
        status='pending'
    )
    
    # Set user back to user
    test_user.userprofile.role = 'user'
    test_user.userprofile.save()
    
    print(f"Created third test application: {application3}")
    print(f"User role set to: {test_user.userprofile.role}")
    
    approve_url2 = reverse('approve_host_application', args=[application3.id])
    print(f"Approve URL (non-AJAX): {approve_url2}")
    
    response = client.post(approve_url2)  # No AJAX header
    print(f"Regular form response status: {response.status_code}")
    print(f"Regular form response URL: {response.url if hasattr(response, 'url') else 'No redirect'}")
    
    if response.status_code == 302:  # Redirect expected
        print("✅ Regular form submission redirected successfully")
        
        # Check if application was approved
        application3.refresh_from_db()
        print(f"Application status after approve: {application3.status}")
        
        # Check if user role was updated
        test_user.userprofile.refresh_from_db()
        print(f"User role after approve: {test_user.userprofile.role}")
        
        if application3.status == 'approved' and test_user.userprofile.role == 'host':
            print("✅ Regular form submission functionality working correctly!")
        else:
            print("❌ Regular form submission functionality failed!")
            return False
    else:
        print(f"❌ Regular form submission failed: {response.status_code}")
        print(f"Response content: {response.content}")
        return False
    
    # Clean up
    application.delete()
    application2.delete()
    application3.delete()
    if test_user.username == 'test_applicant_hands_on':
        test_user.delete()
    if admin_user.username == 'test_admin_hands_on':
        admin_user.delete()
    
    print(f"\n✅ All hands-on tests passed! Dashboard functionality is working correctly.")
    return True

if __name__ == '__main__':
    try:
        success = test_dashboard_as_admin()
        if success:
            print("\n🎉 SUCCESS: The dashboard approve/reject functionality is working correctly!")
            print("\nIf you're still seeing issues in the browser:")
            print("1. Clear browser cache and cookies")
            print("2. Check browser console for JavaScript errors")
            print("3. Check Network tab for request/response details")
            print("4. Make sure you're logged in as an admin user")
            print("5. Verify the CSRF token is being sent correctly")
        else:
            print("\n❌ FAILED: There are issues with the dashboard functionality.")
            print("\nPlease check the error messages above and fix the issues.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc() 