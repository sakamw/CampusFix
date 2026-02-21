from django import forms
from .models import AdminWorkLog, ProgressUpdate


class AdminWorkLogForm(forms.ModelForm):
    """Form for creating and editing admin work logs"""
    
    class Meta:
        model = AdminWorkLog
        fields = ['work_type', 'hours_spent', 'description', 'materials_used', 'outcome', 'next_steps']
        widgets = {
            'work_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'hours_spent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.25',
                'min': '0.25',
                'max': '24',
                'placeholder': '0.0',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Describe the work performed...',
            }),
            'materials_used': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'List any materials or resources used...',
            }),
            'outcome': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'What was the result or outcome of this work?',
            }),
            'next_steps': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'What are the planned next steps?',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['work_type'].label = 'Work Type *'
        self.fields['hours_spent'].label = 'Hours Spent *'
        self.fields['description'].label = 'Description *'
        self.fields['materials_used'].label = 'Materials Used (Optional)'
        self.fields['outcome'].label = 'Outcome *'
        self.fields['next_steps'].label = 'Next Steps (Optional)'
    
    def clean_hours_spent(self):
        hours = self.cleaned_data.get('hours_spent')
        if hours <= 0:
            raise forms.ValidationError('Hours spent must be greater than 0.')
        if hours > 24:
            raise forms.ValidationError('Hours spent cannot exceed 24.')
        return hours
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or not description.strip():
            raise forms.ValidationError('Description is required.')
        return description.strip()
    
    def clean_outcome(self):
        outcome = self.cleaned_data.get('outcome')
        if not outcome or not outcome.strip():
            raise forms.ValidationError('Outcome is required.')
        return outcome.strip()


class ProgressUpdateForm(forms.ModelForm):
    """Form for creating and editing progress updates"""
    
    class Meta:
        model = ProgressUpdate
        fields = ['update_type', 'progress_percentage', 'title', 'description', 'next_steps', 'estimated_completion', 'is_major_update']
        widgets = {
            'update_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'progress_percentage': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '0',
                'max': '100',
                'placeholder': '0-100',
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Brief title of this update',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Detailed description of progress update',
            }),
            'next_steps': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Next steps or planned actions',
            }),
            'estimated_completion': forms.DateTimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'datetime-local',
            }),
            'is_major_update': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['update_type'].label = 'Update Type'
        self.fields['progress_percentage'].label = 'Progress Percentage (%)'
        self.fields['title'].label = 'Title *'
        self.fields['description'].label = 'Description *'
        self.fields['next_steps'].label = 'Next Steps (Optional)'
        self.fields['estimated_completion'].label = 'Estimated Completion'
        self.fields['is_major_update'].label = 'Mark as Major Update'
    
    def clean_progress_percentage(self):
        percentage = self.cleaned_data.get('progress_percentage')
        if percentage < 0 or percentage > 100:
            raise forms.ValidationError('Progress percentage must be between 0 and 100.')
        return percentage
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise forms.ValidationError('Title is required.')
        return title.strip()
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or not description.strip():
            raise forms.ValidationError('Description is required.')
        return description.strip()
