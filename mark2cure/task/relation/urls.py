from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',

    # AJAX Endpoints
    url(r'^(?P<document_pk>\d+)/(?P<relation_pk>\d+)/submit/$',
        views.submit_annotation, name='submit-annotation'),

    url(r'^(?P<document_pk>\d+)/submit/$',
        views.submit_document_set, name='submit-set'),

    url(r'^(?P<document_pk>\d+)/api/$',
        views.fetch_document_relations, name='fetch-document-relations'),

    url(r'^(?P<document_pk>\d+)/analysis/(?P<relation_pk>)/$',
        views.document_analysis, name='document-analysis-specific'),
    url(r'^(?P<document_pk>\d+)/analysis/$',
        views.document_analysis, name='document-analysis'),

    # View user endpoints
    url(r'^(?P<document_pk>\d+)/complete/$',
        views.relation_task_complete, name='task-complete'),

    url(r'^(?P<document_pk>\d+)/$',
        views.relation_task_home, name='task'),

    # Deprecated
    url(r'^(?P<relation_pk>\d+)/feedback-api/$',
        views.fetch_relation_feedback, name='fetch-relation-feedback'),
)
