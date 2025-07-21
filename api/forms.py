# learnflow_ai/django_backend/api/forms.py

from django import forms
import json
from .models import Question

class QuestionAdminForm(forms.ModelForm):
    # Define individual CharFields for each MCQ option
    option_a = forms.CharField(max_length=255, required=False, label="Option A")
    option_b = forms.CharField(max_length=255, required=False, label="Option B")
    option_c = forms.CharField(max_length=255, required=False, label="Option C")
    option_d = forms.CharField(max_length=255, required=False, label="Option D")

    class Meta:
        model = Question
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.options:
            # Ensure options_list is a list, even if self.instance.options is None
            options_list = self.instance.options or []
            if len(options_list) > 0:
                self.initial['option_a'] = options_list[0]
            if len(options_list) > 1:
                self.initial['option_b'] = options_list[1]
            if len(options_list) > 2:
                self.initial['option_c'] = options_list[2]
            if len(options_list) > 3:
                self.initial['option_d'] = options_list[3]

        if 'options' in self.fields:
            self.fields['options'].widget = forms.HiddenInput()
            self.fields['options'].required = False

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')

        # Removed DEBUG PRINT
        # print(f"DEBUG: In clean() method. Question type: {question_type}")

        if question_type == 'MCQ':
            options = []
            if cleaned_data.get('option_a'):
                options.append(cleaned_data['option_a'])
            if cleaned_data.get('option_b'):
                options.append(cleaned_data['option_b'])
            if cleaned_data.get('option_c'):
                options.append(cleaned_data['option_c'])
            if cleaned_data.get('option_d'):
                options.append(cleaned_data['option_d'])

            # Removed DEBUG PRINT
            # print(f"DEBUG: Collected options (before validation): {options}")

            if len(options) < 2:
                self.add_error(None, "MCQ questions must have at least two options (Option A, B, C, or D).")
                # Removed DEBUG PRINT
                # print("DEBUG: Validation error: Less than 2 options for MCQ.")

            cleaned_data['options'] = options
            # Removed DEBUG PRINT
            # print(f"DEBUG: Final cleaned_data['options'] for MCQ: {cleaned_data['options']}")
        else:
            cleaned_data['options'] = []
            # Removed DEBUG PRINT
            # print(f"DEBUG: Question type is not MCQ. Setting options to empty list: {cleaned_data['options']}")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Assign the combined options list to the model's JSONField
        # This is the crucial step that writes the collected options to the model instance
        instance.options = self.cleaned_data.get('options', [])

        if commit:
            instance.save()
        return instance
