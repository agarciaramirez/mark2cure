# learn shortcuts
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views import generic
from django.utils import timezone

from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import get_object_or_404, redirect, render_to_response, RequestContext
from django.template.response import TemplateResponse
from django.contrib.messages import get_messages
from django.contrib.auth.models import User
from django.contrib import messages

from ..common.formatter import bioc_as_json, apply_bioc_annotations
from ..common.bioc import BioCReader
from ..userprofile.models import UserProfile
from ..document.models import Document, Section, Pubtator
from ..common.models import Group


from brabeion import badges
import datetime
import re
import json
import random
import itertools

from .models import Answer, Relation, Concept
from .forms import AnswerForm
import os


@login_required
def home(request):

    # Just get group 4 for now. TODO upon integration, make this better (Max)
    group_pk = 4
    group = Group.objects.get(pk=group_pk)
    documents = Document.objects.filter(task__group=group).all()
    docs_with_unanswered_relations_for_user = []

    for document in documents:
        relations = Relation.objects.filter(document=document)
        for relation in relations:
            if not Answer.objects.filter(username=request.user).filter(relation=relation.pk).exists():
                if document not in docs_with_unanswered_relations_for_user:
                    docs_with_unanswered_relations_for_user.append(document)
                break

    queryset_documents = docs_with_unanswered_relations_for_user[:20]

    ctx = {
        'documents': queryset_documents,
    }
    return TemplateResponse(request, 'relation/home.jade', ctx)


@login_required
def relation_api(request, document_pk):
    from django.http import JsonResponse
    # the document instance
    current_document = get_object_or_404(Document, pk=document_pk)

    # Only make api for relations that do not have an answer!
    # This is why data[0] inside relation.js works
    unanswered_relations_for_user = current_document.unanswered_relation_list(request)
    # ^^^^^^ no dry TODO Max, why isn't this dry?

    relation_list = []
    pub_list = []
    for relation in unanswered_relations_for_user:
        relation_dict = {}
        concept1 = Concept.objects.get(document=current_document, uid=relation.concept1_id)
        concept2 = Concept.objects.get(document=current_document, uid=relation.concept2_id)
        relation_type = concept1.stype + "_" + concept2.stype

        def get_pub_pk(concept_stype):
            if concept_stype == "g":
                pub = Pubtator.objects.get(document=current_document, kind="GNormPlus").pk
            elif concept_stype == "d":
                pub = Pubtator.objects.get(document=current_document, kind="DNorm").pk
            else:
                pub = Pubtator.objects.get(document=current_document, kind="tmChem").pk
            if pub not in pub_list:
                pub_list.append(pub)
            return pub
        if (relation_type == 'g_d' or relation_type == 'd_g'):
            file_key = 'gene_disease_relation_menu';

        if (relation_type == 'c_d' or relation_type == 'd_c' ):
            file_key = 'chemical_disease_relation_menu';

        if (relation_type == 'g_c' or relation_type == 'c_g' ):
            file_key = 'gene_chemical_relation_menu';

        # always have gene on the left and disease on the right for sentence structure
        if relation_type == 'c_g' or relation_type == 'd_g' or relation_type == 'd_c':
            concept1, concept2 = concept2, concept1

        # when I passed this information to html, I could not retain the object, (error "is not JSON serializable")
        # so I put them in different properties
        relation_dict['c1_id']= str(concept1.id)
        relation_dict['c1_text']= str(concept1.text)
        relation_dict['c1_stype']= str(concept1.stype)
        relation_dict['c1_correct'] = True
        relation_dict['c1_pub_pk'] = str(get_pub_pk(str(concept1.stype)))
        relation_dict['c2_id']= str(concept2.id)
        relation_dict['c2_text']= str(concept2.text)
        relation_dict['c2_stype']= str(concept2.stype)
        relation_dict['c2_correct'] = True
        relation_dict['c2_pub_pk'] = str(get_pub_pk(str(concept2.stype)))
        relation_dict['relation_type'] = file_key
        relation_dict['pk'] = relation.pk
        relation_dict['pub_list'] = pub_list

        relation_list.append(relation_dict)

    return JsonResponse(relation_list, safe=False)

@login_required
def relation(request, document_pk):
    form = AnswerForm
    # the document instance
    document = get_object_or_404(Document, pk=document_pk)


    # TODO do I need this relation piece
    relations = document.unanswered_relation_list(request)
    relation = relations[0]
    # TODO this is incorrect. Needs to be removed.
    # print relation, "relation, views"
    # unanswered_relations_for_user = document.unanswered_relation_list(request)
    # print unanswered_relations_for_user, "unanswered_relations_for_user views"

    ctx = {'sections': Section.objects.filter(document=document),
           'relation': relation,
           'document_pk': document_pk,
           }
    return TemplateResponse(request, 'relation/relation.jade', ctx)

#pass in relation similar to above method
def results(request, relation_id): #, relation_id
    # print request, "JEN RESULTS REQUEST"
    relation = get_object_or_404(Relation, pk=relation_id)
    relation_type = request.POST['relation_type']
    # print relation_type, "RELATION TYPE"
    form = AnswerForm(request.POST or None)

    if form.is_valid():
        print "VALID FORM"
        form.save()
    relation_type = "testing views relation_type"
    if request.method == 'POST':
        ctx = {
        'relation_type':relation_type,
        }
        return TemplateResponse(request, 'relation/results.jade', ctx)
    #return HttpResponseRedirect(reverse("relation:home"))

@login_required
@require_http_methods(['POST'])
def create_post(request):
    form = AnswerForm(request.POST or None)
    # print form
    if form.is_valid():
        form.save()

    return HttpResponse(200)

@login_required
@require_http_methods(['POST'])
def jen_bioc(request):
    # print request
    relation_list = request.POST['relation_list']
    # print relation_list
    writer_json = bioc_as_json(relation_list)
    return HttpResponse(200)
