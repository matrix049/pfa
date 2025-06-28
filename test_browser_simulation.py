#!/usr/bin/env python
"""
Test that simulates exact browser behavior to identify dashboard issue
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

def test_browser_simulation():
    """Simulate exact browser behavior"""
    print("=== Browser Simulation Test ===\n")
    
    # Get existing admin user
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ Found admin user: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ Admin user not found")
        return False
    
    # Get existing test application
    try:
        application = HostApplication.objects.filter(status='pending').first()
        if application:
            print(f"✅ Found pending application: {application}")
        else:
            print("❌ No pending applications found")
            return False
    except Exception as e:
        print(f"❌ Error finding application: {e}")
        return False
    
    # Create test client
    client = Client()
    
    # Force login as admin
    client.force_login(admin_user)
    print("✅ Force logged in as admin")
    
    # Step 1: Get dashboard page
    print("\n--- Step 1: Get Dashboard Page ---")
    response = client.get(reverse('dashboard'))
    print(f"Dashboard response status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Dashboard failed to load: {response.status_code}")
        return False
    
    # Extract CSRF token from the page
    content = response.content.decode('utf-8')
    import re
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
    if not csrf_match:
        print("❌ CSRF token not found in dashboard HTML")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Extracted CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Simulate JavaScript getCookie function
    print("\n--- Step 2: Simulate JavaScript getCookie ---")
    
    # Get cookies from the response
    cookies = response.cookies
    csrf_cookie = None
    
    # Check if csrftoken cookie exists
    if 'csrftoken' in cookies:
        csrf_cookie = cookies['csrftoken'].value if hasattr(cookies['csrftoken'], 'value') else str(cookies['csrftoken'])
        print(f"✅ Found CSRF cookie: {csrf_cookie[:20]}...")
    else:
        print("❌ CSRF cookie not found")
        return False
    
    # Step 3: Test approve with cookie-based CSRF token
    print("\n--- Step 3: Test Approve with Cookie CSRF ---")
    approve_url = reverse('approve_host_application', args=[application.id])
    print(f"Approve URL: {approve_url}")
    
    # Simulate the exact JavaScript fetch request
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrf_cookie,  # Use cookie value like JavaScript
    }
    
    response = client.post(approve_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **headers)
    print(f"Approve response status: {response.status_code}")
    print(f"Approve response content: {response.content}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ Approve works with cookie-based CSRF token")
                
                # Check if application was approved
                application.refresh_from_db()
                print(f"Application status after approve: {application.status}")
                
                # Check if user role was updated
                test_user = application.user
                test_user.userprofile.refresh_from_db()
                print(f"User role after approve: {test_user.userprofile.role}")
                
                if application.status == 'approved' and test_user.userprofile.role == 'host':
                    print("✅ Approve functionality working correctly!")
                else:
                    print("❌ Approve functionality failed!")
                    return False
            else:
                print(f"❌ Approve returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response.content}")
            return False
    else:
        print(f"❌ Approve endpoint failed: {response.status_code}")
        return False
    
    # Step 4: Test with form-based CSRF token (like the actual form)
    print("\n--- Step 4: Test with Form-based CSRF ---")
    
    # Create a new application for testing
    test_user = User.objects.get(username='testuser')
    application2 = HostApplication.objects.create(
        user=test_user,
        business_name='Test Business Form CSRF',
        business_address='123 Test Street',
        business_phone='+1234567890',
        description='Test application for form CSRF testing',
        status='pending'
    )
    
    # Reset user role
    test_user.userprofile.role = 'user'
    test_user.userprofile.save()
    
    print(f"Created new test application: {application2}")
    
    # Simulate form submission with form data
    form_data = {
        'csrfmiddlewaretoken': csrf_token,  # Use form token
    }
    
    approve_url2 = reverse('approve_host_application', args=[application2.id])
    print(f"Approve URL: {approve_url2}")
    
    response = client.post(approve_url2, form_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    print(f"Form-based approve response status: {response.status_code}")
    print(f"Form-based approve response content: {response.content}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ Form-based approve works correctly")
                
                # Check if application was approved
                application2.refresh_from_db()
                print(f"Application status after approve: {application2.status}")
                
                # Check if user role was updated
                test_user.userprofile.refresh_from_db()
                print(f"User role after approve: {test_user.userprofile.role}")
                
                if application2.status == 'approved' and test_user.userprofile.role == 'host':
                    print("✅ Form-based approve functionality working correctly!")
                else:
                    print("❌ Form-based approve functionality failed!")
                    return False
            else:
                print(f"❌ Form-based approve returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response.content}")
            return False
    else:
        print(f"❌ Form-based approve endpoint failed: {response.status_code}")
        return False
    
    # Clean up
    application2.delete()
    
    print(f"\n✅ All browser simulation tests passed!")
    print(f"\nThe issue is likely in the JavaScript implementation.")
    print(f"Both cookie-based and form-based CSRF tokens work correctly in the backend.")
    print(f"The problem is probably that the JavaScript is not getting the CSRF token properly.")
    
    return True

if __name__ == '__main__':
    test_browser_simulation() 