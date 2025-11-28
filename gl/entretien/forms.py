from django import forms
from .models import Entretien
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class EntretienForm(forms.ModelForm):
    class Meta:
        model = Entretien
        fields = ['postulation', 'date_entretien', 'lien_meet', 'commentaire', 'statut']
        widgets = {
            'postulation': forms.HiddenInput(),
            'date_entretien': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'lien_meet': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://meet.google.com/...',
                'pattern': 'https?://.+',
                'maxlength': '500'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes ou commentaires...',
                'maxlength': '1000'
            }),
            'statut': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
        }
    
    def clean_date_entretien(self):
        date_entretien = self.cleaned_data.get('date_entretien')
        if date_entretien:
            if date_entretien < timezone.now():
                raise forms.ValidationError("La date de l'entretien ne peut pas être dans le passé.")
        return date_entretien
    
    def clean_lien_meet(self):
        lien_meet = self.cleaned_data.get('lien_meet')
        if lien_meet:
            validator = URLValidator()
            try:
                validator(lien_meet)
            except ValidationError:
                raise forms.ValidationError("Veuillez entrer une URL valide (commençant par http:// ou https://).")
        return lien_meet

