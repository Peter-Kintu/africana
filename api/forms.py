from django import forms
import json
from .models import Question, Teacher, User

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
            options_list = json.loads(self.instance.options) if self.instance.options else []
            self.initial['option_a'] = options_list[0] if len(options_list) > 0 else ''
            self.initial['option_b'] = options_list[1] if len(options_list) > 1 else ''
            self.initial['option_c'] = options_list[2] if len(options_list) > 2 else ''
            self.initial['option_d'] = options_list[3] if len(options_list) > 3 else ''

    def clean(self):
        cleaned_data = super().clean()
        options = [
            cleaned_data.get('option_a'),
            cleaned_data.get('option_b'),
            cleaned_data.get('option_c'),
            cleaned_data.get('option_d'),
        ]
        # Filter out empty strings/None values and save as a JSON string
        cleaned_options = [opt for opt in options if opt]
        # Re-assign the cleaned options to the 'options' field of the model instance
        self.instance.options = json.dumps(cleaned_options)
        return cleaned_data

class TeacherAdminForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Explicitly set the queryset for the 'user' field
        self.fields['user'].queryset = User.objects.all()