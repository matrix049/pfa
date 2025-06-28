#!/usr/bin/env python
"""
Quick test to check dashboard view and identify issues
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

def quick_dashboard_test():
    """Quick test to check dashboard functionality"""
    print("=== Quick Dashboard Test ===\n")
    
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
    
    # Login as admin
    response = client.post(reverse('login'), {
        'username': 'admin',
        'password': 'adminpass123'
    })
    
    if response.status_code == 302:
        print("✅ Admin login successful")
    else:
        print(f"❌ Admin login failed: {response.status_code}")
        return False
    
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
        
    else:
        print(f"❌ Dashboard failed to load: {response.status_code}")
        return False
    
    # Test approve URL directly
    approve_url = reverse('approve_host_application', args=[application.id])
    print(f"\nTesting approve URL: {approve_url}")
    
    response = client.post(approve_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    print(f"Approve response status: {response.status_code}")
    print(f"Approve response content: {response.content}")
    
    if response.status_code == 200:
        print("✅ Approve endpoint works")
    else:
        print(f"❌ Approve endpoint failed: {response.status_code}")
    
    return True

if __name__ == '__main__':
    quick_dashboard_test() 