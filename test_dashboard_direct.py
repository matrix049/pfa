#!/usr/bin/env python
"""
Direct test of dashboard functionality without login issues
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

def test_dashboard_direct():
    """Test dashboard functionality directly"""
    print("=== Direct Dashboard Test ===\n")
    
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
    
    # Force login as admin (bypass authentication)
    client.force_login(admin_user)
    print("✅ Force logged in as admin")
    
    # Test dashboard
    response = client.get(reverse('dashboard'))
    print(f"Dashboard response status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Dashboard loads successfully")
        
        # Check if the application is mentioned in the HTML
        content = response.content.decode('utf-8')
        if 'Test Business' in content:
            print("✅ Dashboard shows the test application")
        else:
            print("❌ Dashboard does not show the test application")
            print("This might be because the application is not in the context")
        
        # Check for approve/reject buttons
        if 'approve_host_application' in content:
            print("✅ Dashboard has approve buttons")
        else:
            print("❌ Dashboard missing approve buttons")
        
        if 'reject_host_application' in content:
            print("✅ Dashboard has reject buttons")
        else:
            print("❌ Dashboard missing reject buttons")
        
        # Check for CSRF token
        if 'csrfmiddlewaretoken' in content:
            print("✅ Dashboard has CSRF token")
        else:
            print("❌ Dashboard missing CSRF token")
        
        # Check for JavaScript
        if 'getCookie' in content:
            print("✅ Dashboard has CSRF JavaScript function")
        else:
            print("❌ Dashboard missing CSRF JavaScript function")
        
        if 'X-CSRFToken' in content:
            print("✅ Dashboard has CSRF header setup")
        else:
            print("❌ Dashboard missing CSRF header setup")
        
        # Check for the specific application in the HTML
        if str(application.id) in content:
            print("✅ Dashboard shows the specific application ID")
        else:
            print("❌ Dashboard does not show the specific application ID")
        
        # Check for the Host Applications tab
        if 'Host Applications' in content or 'Demandes d\'Hôte' in content:
            print("✅ Dashboard has Host Applications tab")
        else:
            print("❌ Dashboard missing Host Applications tab")
        
    else:
        print(f"❌ Dashboard failed to load: {response.status_code}")
        return False
    
    # Test approve URL directly
    approve_url = reverse('approve_host_application', args=[application.id])
    print(f"\nTesting approve URL: {approve_url}")
    
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
    print(f"Approve response content: {response.content}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            print(f"Response data: {data}")
            
            if data.get('success'):
                print("✅ Approve endpoint works correctly")
                
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
    
    return True

if __name__ == '__main__':
    test_dashboard_direct() 