from django import forms
from .models import OffreStage, CVData
import re
import json

class OffreStageForm(forms.ModelForm):
    titre = forms.CharField(
        required=True,
        max_length=100,
        min_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Titre de l\'offre',
            'maxlength': '100',
            'minlength': '5',
            'pattern': '.*[a-zA-ZÀ-ÿ].*',
            'title': 'Le titre doit contenir au moins une lettre'
        }),
        error_messages={
            'required': 'Le titre est obligatoire.',
            'min_length': 'Le titre doit contenir au moins 5 caractères.',
            'max_length': 'Le titre ne peut pas dépasser 100 caractères.'
        }
    )
    
    description = forms.CharField(
        required=True,
        min_length=20,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 4, 
            'placeholder': 'Description détaillée de l\'offre',
            'minlength': '20'
        }),
        error_messages={
            'required': 'La description est obligatoire.',
            'min_length': 'La description doit contenir au moins 20 caractères.'
        }
    )
    
    domaine = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ex: Informatique, Marketing, Design...',
            'maxlength': '100'
        }),
        error_messages={
            'required': 'Le domaine est obligatoire.',
            'max_length': 'Le domaine ne peut pas dépasser 100 caractères.'
        }
    )
    
    lieu = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ex: Tunis, Remote, Sfax...',
            'maxlength': '100',
            'pattern': '.*[a-zA-ZÀ-ÿ].*',
            'title': 'Le lieu doit contenir au moins une lettre'
        }),
        error_messages={
            'required': 'Le lieu est obligatoire.',
            'max_length': 'Le lieu ne peut pas dépasser 100 caractères.'
        }
    )
    
    remuneration = forms.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }),
        error_messages={
            'required': 'La rémunération est obligatoire.',
            'min_value': 'La rémunération doit être positive (en DT).',
            'invalid': 'Veuillez entrer un nombre valide.'
        }
    )
    
    etat = forms.CharField(
        required=True,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ex: disponible, indisponible...',
            'maxlength': '50'
        }),
        error_messages={
            'required': 'L\'état est obligatoire.',
            'max_length': 'L\'état ne peut pas dépasser 50 caractères.'
        },
        initial='disponible'
    )
    
    duree = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=104,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Durée en semaines',
            'min': '1',
            'max': '104'
        }),
        error_messages={
            'required': 'La durée est obligatoire.',
            'min_value': 'La durée doit être d\'au moins 1 semaine.',
            'max_value': 'La durée ne peut pas dépasser 104 semaines (2 ans).',
            'invalid': 'Veuillez entrer un nombre entier valide.'
        }
    )
    
    date_publication = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        }),
        error_messages={
            'required': 'La date de publication est obligatoire.',
            'invalid': 'Veuillez entrer une date valide.'
        }
    )
    
    image = forms.ImageField(
        required=False,  # Sera géré dans clean_image pour permettre l'édition
        widget=forms.FileInput(attrs={
            'class': 'form-control', 
            'accept': 'image/jpeg,image/jpg,image/png,image/webp',
            'onchange': 'validateImage(this)'
        }),
        error_messages={
            'invalid': 'Veuillez sélectionner un fichier image valide.'
        }
    )
    
    class Meta:
        model = OffreStage
        fields = ['titre', 'description', 'domaine', 'lieu', 'remuneration', 'etat', 'duree', 'visibilite', 'image', 'date_publication']
        widgets = {
            'visibilite': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_titre(self):
        titre = self.cleaned_data.get('titre')
        if titre:
            titre = titre.strip()
            if len(titre) < 5:
                raise forms.ValidationError("Le titre doit contenir au moins 5 caractères.")
            # Vérifier qu'il y a au moins une lettre (pas seulement des chiffres)
            if not re.search(r'[a-zA-ZÀ-ÿ]', titre):
                raise forms.ValidationError("Le titre doit contenir au moins une lettre (pas uniquement des chiffres).")
            # Vérifier qu'il ne commence pas par un chiffre uniquement
            if re.match(r'^\d+$', titre):
                raise forms.ValidationError("Le titre ne peut pas être uniquement composé de chiffres.")
        return titre
    
    def clean_lieu(self):
        lieu = self.cleaned_data.get('lieu')
        if lieu:
            lieu = lieu.strip()
            if len(lieu) < 2:
                raise forms.ValidationError("Le lieu doit contenir au moins 2 caractères.")
            # Vérifier qu'il y a au moins une lettre
            if not re.search(r'[a-zA-ZÀ-ÿ]', lieu):
                raise forms.ValidationError("Le lieu doit contenir au moins une lettre (pas uniquement des chiffres).")
        return lieu
    
    
    def clean_remuneration(self):
        remuneration = self.cleaned_data.get('remuneration')
        if remuneration is not None:
            if remuneration < 0:
                raise forms.ValidationError("La rémunération doit être positive (en DT - Dinars Tunisiens).")
            if remuneration == 0:
                raise forms.ValidationError("La rémunération doit être supérieure à 0 DT.")
        else:
            raise forms.ValidationError("La rémunération est obligatoire.")
        return remuneration
    
    def clean_duree(self):
        duree = self.cleaned_data.get('duree')
        if duree is not None:
            if duree < 1:
                raise forms.ValidationError("La durée doit être d'au moins 1 semaine.")
            if duree > 104:
                raise forms.ValidationError("La durée ne peut pas dépasser 104 semaines (2 ans).")
        else:
            raise forms.ValidationError("La durée est obligatoire.")
        return duree
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            description = description.strip()
            if len(description) < 20:
                raise forms.ValidationError("La description doit contenir au moins 20 caractères.")
        else:
            raise forms.ValidationError("La description est obligatoire.")
        return description
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        # Si c'est une nouvelle offre (pas d'instance ou instance sans pk), l'image est obligatoire
        if not self.instance or not self.instance.pk:
            if not image:
                raise forms.ValidationError("L'image est obligatoire pour une nouvelle offre.")
        # Si on modifie une offre existante sans image et qu'aucune nouvelle image n'est fournie
        elif self.instance.pk and not self.instance.image and not image:
            raise forms.ValidationError("L'image est obligatoire.")
        return image


class CVForm(forms.ModelForm):
    """Formulaire pour remplir les données CV"""
    
    full_name = forms.CharField(
        required=True,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: John Doe'
        })
    )
    
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: +216 12 345 678'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    
    address = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Tunis, Tunisia'
        })
    )
    
    linkedin = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://linkedin.com/in/yourprofile'
        })
    )
    
    github = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://github.com/yourusername'
        })
    )
    
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://yourwebsite.com'
        })
    )
    
    professional_summary = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Write a brief professional summary about yourself...'
        })
    )
    
    # Les champs JSON seront gérés via JavaScript dans le template
    skills = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    education = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    experience = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    projects = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    languages = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    certifications = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = CVData
        fields = [
            'full_name', 'phone', 'email', 'address', 'linkedin', 'github', 'website',
            'professional_summary', 'skills', 'education', 'experience',
            'projects', 'languages', 'certifications'
        ]
    
    def clean_skills(self):
        skills_str = self.cleaned_data.get('skills', '[]')
        try:
            return json.loads(skills_str) if skills_str else []
        except json.JSONDecodeError:
            return []
    
    def clean_education(self):
        education_str = self.cleaned_data.get('education', '[]')
        try:
            return json.loads(education_str) if education_str else []
        except json.JSONDecodeError:
            return []
    
    def clean_experience(self):
        experience_str = self.cleaned_data.get('experience', '[]')
        try:
            return json.loads(experience_str) if experience_str else []
        except json.JSONDecodeError:
            return []
    
    def clean_projects(self):
        projects_str = self.cleaned_data.get('projects', '[]')
        try:
            return json.loads(projects_str) if projects_str else []
        except json.JSONDecodeError:
            return []
    
    def clean_languages(self):
        languages_str = self.cleaned_data.get('languages', '[]')
        try:
            return json.loads(languages_str) if languages_str else []
        except json.JSONDecodeError:
            return []
    
    def clean_certifications(self):
        certifications_str = self.cleaned_data.get('certifications', '[]')
        try:
            return json.loads(certifications_str) if certifications_str else []
        except json.JSONDecodeError:
            return []

