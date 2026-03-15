from django import forms
from django.core.exceptions import ValidationError

from .models import extract_first_youtube_url, extract_youtube_video_id, is_file_url


class PostForm(forms.Form):
    content = forms.CharField(
        max_length=280,
        label="Message",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-input composer-input",
                "placeholder": "Quoi de neuf ?",
                "rows": 3,
                "maxlength": 280,
            }
        ),
    )
    image = forms.ImageField(
        required=False,
        label="Image",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-input form-file-input",
                "accept": "image/*",
            }
        ),
    )
    attachment_url = forms.URLField(
        required=False,
        label="URL de fichier",
        widget=forms.URLInput(
            attrs={
                "class": "form-input",
                "placeholder": "https://exemple.com/fichier.pdf",
            }
        ),
    )

    def clean_content(self):
        return (self.cleaned_data.get("content") or "").strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 10 * 1024 * 1024:
            raise ValidationError("L'image doit faire moins de 10 Mo.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        content = (cleaned_data.get("content") or "").strip()
        image = cleaned_data.get("image")
        attachment_url = (cleaned_data.get("attachment_url") or "").strip()
        youtube_url = extract_first_youtube_url(content)

        if attachment_url and extract_youtube_video_id(attachment_url):
            self.add_error(
                "attachment_url",
                "Pour YouTube, colle le lien directement dans le message.",
            )
        elif attachment_url and not is_file_url(attachment_url):
            self.add_error(
                "attachment_url",
                "L'URL doit pointer vers un fichier (pdf, image, video, etc.).",
            )

        if not content and not image and not attachment_url:
            raise ValidationError("Ajoute un message, une image ou une URL de fichier.")

        cleaned_data["content"] = content
        cleaned_data["youtube_url"] = youtube_url
        cleaned_data["attachment_url"] = attachment_url
        return cleaned_data
