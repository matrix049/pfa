from django import forms
from .models import HostApplication, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class HostApplicationForm(forms.ModelForm):
    class Meta:
        model = HostApplication
        fields = ['business_name', 'business_address', 'business_phone', 'identity_document', 'description']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'business_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'identity_document': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'business_name': 'Business Name',
            'business_address': 'Business Address',
            'business_phone': 'Business Phone',
            'identity_document': 'Identity Document (PDF, Image)',
            'description': 'Tell us about your hosting experience'
        }
        help_texts = {
            'identity_document': 'Please upload a valid ID document (passport, driver\'s license, etc.)',
            'description': 'Include information about your properties and hosting experience'
        }

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'phone_number', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Tell us a bit about yourself'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Save user info
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            profile.save()
        return profile 

class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'avatar', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                profile = user.userprofile
                profile.avatar = avatar
                profile.save()
        return user 