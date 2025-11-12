from django import forms
from .models import Logement, LogementImage, BinomeRequest


class LogementForm(forms.ModelForm):
    """Formulaire pour créer et modifier un logement"""
    
    # Note: Les images supplémentaires sont gérées manuellement dans le template
    # avec des champs <input type="file" name="images"> et récupérées dans la vue
    # avec request.FILES.getlist('images')
    
    class Meta:
        model = Logement
        fields = [
            'title',
            'description',
            'type_logement',
            'address',
            'city',
            'price',
            'surface',
            'rooms',
            'bathrooms',
            'image',
            'model_3d',
            'available',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du logement'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Description détaillée du logement'
            }),
            'type_logement': forms.Select(attrs={
                'class': 'form-control'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse complète'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prix',
                'step': '0.01',
                'min': '0'
            }),
            'surface': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Surface en m²',
                'step': '0.01',
                'min': '0'
            }),
            'rooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de pièces',
                'min': '1'
            }),
            'bathrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de salles de bain',
                'min': '1'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'model_3d': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://exemple.com/modele-3d'
            }),
            'available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'title': 'Titre',
            'description': 'Description',
            'type_logement': 'Type de logement',
            'address': 'Adresse',
            'city': 'Ville',
            'price': 'Prix',
            'surface': 'Surface (m²)',
            'rooms': 'Nombre de pièces',
            'bathrooms': 'Nombre de salles de bain',
            'image': 'Image principale',
            'model_3d': 'Modèle 3D (optionnel)',
            'available': 'Disponible',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre le champ image optionnel
        self.fields['image'].required = False
        # Rendre le champ model_3d optionnel
        self.fields['model_3d'].required = False


class BinomeRequestForm(forms.ModelForm):
    """Formulaire pour créer une demande de recherche de binôme"""
    
    class Meta:
        model = BinomeRequest
        fields = [
            'title',
            'description',
            'city',
            'budget_max',
            'logement',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Recherche binôme pour appartement à Alger'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Décrivez ce que vous cherchez, vos préférences, etc.'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville recherchée'
            }),
            'budget_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Budget maximum par mois',
                'step': '0.01',
                'min': '0'
            }),
            'logement': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'title': 'Titre de la recherche',
            'description': 'Description',
            'city': 'Ville recherchée',
            'budget_max': 'Budget maximum (DZD/mois)',
            'logement': 'Logement spécifique (optionnel)',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Filtrer les logements de l'utilisateur
            self.fields['logement'].queryset = Logement.objects.filter(owner=user, approved=True, rejected=False)
        self.fields['logement'].required = False
        self.fields['logement'].empty_label = "Aucun logement spécifique"
