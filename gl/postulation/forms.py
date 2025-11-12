from django import forms
from .models import Postulation
import re

class PostulationForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com',
            'pattern': '[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$',
            'title': 'Veuillez entrer une adresse email valide'
        }),
        error_messages={
            'required': 'L\'adresse email est obligatoire.',
            'invalid': 'Veuillez entrer une adresse email valide.'
        }
    )
    
    lettre_motivation = forms.CharField(
        required=True,
        min_length=50,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Write your motivation letter here...',
            'minlength': '50'
        }),
        error_messages={
            'required': 'La lettre de motivation est obligatoire.',
            'min_length': 'La lettre de motivation doit contenir au moins 50 caractères.'
        }
    )
    
    cv = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx',
            'onchange': 'validateCV(this)'
        }),
        help_text='Formats acceptés: PDF, DOC, DOCX (optionnel)'
    )
    
    class Meta:
        model = Postulation
        fields = ['offre', 'email', 'cv', 'lettre_motivation']
        widgets = {
            'offre': forms.HiddenInput(),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            # Validation du format email
            email_pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
            if not re.match(email_pattern, email):
                raise forms.ValidationError("Veuillez entrer une adresse email valide.")
        else:
            raise forms.ValidationError("L'adresse email est obligatoire.")
        return email
    
    def clean_lettre_motivation(self):
        lettre_motivation = self.cleaned_data.get('lettre_motivation')
        if lettre_motivation:
            lettre_motivation = lettre_motivation.strip()
            if len(lettre_motivation) < 50:
                raise forms.ValidationError("La lettre de motivation doit contenir au moins 50 caractères.")
            # Vérifier qu'il y a au moins quelques lettres (pas seulement des espaces ou caractères spéciaux)
            if not re.search(r'[a-zA-ZÀ-ÿ]{10,}', lettre_motivation):
                raise forms.ValidationError("La lettre de motivation doit contenir du texte significatif.")
        else:
            raise forms.ValidationError("La lettre de motivation est obligatoire.")
        return lettre_motivation
    
    def clean_cv(self):
        cv = self.cleaned_data.get('cv')
        if cv:
            # Vérifier l'extension du fichier
            allowed_extensions = ['.pdf', '.doc', '.docx']
            file_name = cv.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError("Le fichier CV doit être au format PDF, DOC ou DOCX.")
            # Vérifier la taille du fichier (max 10MB)
            if cv.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Le fichier CV ne peut pas dépasser 10 MB.")
        return cv

