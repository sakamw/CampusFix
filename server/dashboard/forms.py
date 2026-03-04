from django import forms

from issues.models import IssueProgressLog


class StaffProgressUpdateForm(forms.ModelForm):
    """Form for staff to post structured progress updates on an assigned issue."""

    class Meta:
        model = IssueProgressLog
        fields = ["log_type", "description", "photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit log types to non-terminal progress updates
        allowed_types = {
            IssueProgressLog.LOG_TYPE_ON_SITE,
            IssueProgressLog.LOG_TYPE_DIAGNOSIS,
            IssueProgressLog.LOG_TYPE_IN_PROGRESS,
        }
        self.fields["log_type"].choices = [
            (value, label)
            for value, label in IssueProgressLog.LOG_TYPE_CHOICES
            if value in allowed_types
        ]
        self.fields["description"].widget = forms.Textarea(attrs={"rows": 3})


class StaffBlockerForm(forms.Form):
    """Form for staff to flag a blocker on an issue."""

    blocker_note = forms.CharField(
        label="Blocker description",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Explain what is preventing you from progressing this issue.",
    )


class StaffResolutionForm(forms.Form):
    """Form for staff to submit a resolution for admin verification."""

    resolution_summary = forms.CharField(
        label="Resolution summary",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="What was the root cause and what was done to fix it?",
    )
    follow_up_recommendations = forms.CharField(
        label="Follow-up recommendations",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="Optional notes, e.g. future maintenance or replacements to plan.",
    )
    final_photo = forms.ImageField(
        label="Final photo",
        required=False,
        help_text="Optional photo showing the completed work.",
    )

