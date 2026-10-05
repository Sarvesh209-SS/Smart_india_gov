from django.urls import path

from .review_views import review_document, review_queue
from .views import delete_document, document_portfolio, upload_document

urlpatterns = [
    path("review/", review_queue, name="document-review-queue"),
    path("review/<int:pk>/", review_document, name="document-review-decision"),
    path("portfolio/", document_portfolio, name="document-portfolio"),
    path("upload/", upload_document, name="document-upload"),
    path("<int:pk>/delete/", delete_document, name="document-delete"),
]
