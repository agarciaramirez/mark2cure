from django.db import models
from django.contrib.auth.models import User

from mark2cure.document.managers import DocumentManager

from nltk.tokenize import WhitespaceTokenizer
from mark2cure.common.bioc import BioCReader, BioCDocument, BioCPassage


class Document(models.Model):
    document_id = models.IntegerField(blank=True)
    title = models.TextField(blank=False)
    authors = models.TextField(blank=False)

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=200, blank=True)

    objects = DocumentManager()

    def __unicode__(self):
        return self.title

    def available_sections(self):
        return self.section_set.exclude(kind='o').all()

    def count_available_sections(self):
        return self.section_set.exclude(kind='o').count()

    def init_pubtator(self):
        # (TODO) Remove any documents that don't have perfect pubtator
        if self.available_sections().exists() and Pubtator.objects.filter(document=self).count() < 3:
            for api_ann in ['tmChem', 'DNorm', 'GNormPlus']:
                Pubtator.objects.get_or_create(document=self, kind=api_ann)

    def valid_pubtator(self):
        pub_query_set = Pubtator.objects.filter(document=self)

        # They've all been validated in the past, leave early
        #if pub_query_set.filter(validate_cache=True).count() == 3:
        #    return True

        # The Docment doesn't have a response for each type
        if pub_query_set.count() < 3:
            return False

        # Check if each type validates, if so save
        for pubtator in Pubtator.objects.filter(document=self):
            try:
                # (TODO) Maybe try to validate actual content as well?
                r = BioCReader(source=pubtator.content)
                r.read()

                pubtator.document = Document.objects.get(document_id=r.collection.documents[0].id)
                pubtator.validate_cache = True
                pubtator.save()
            except Exception as e:
                # If one of them doesn't validate leave
                return False

        return True

    def get_pubtator(self):
        approved_types = ['Disease', 'Gene', 'Chemical']
        self.init_pubtator()
        reader = self.as_writer()

        # Load up our various pubtator responses
        pub_readers = []
        for pubtator in Pubtator.objects.filter(document=self):
            r = BioCReader(source=pubtator.content)
            r.read()
            pub_readers.append(r)

        for d_idx, document in enumerate(reader.collection.documents):
            for p_idx, passage in enumerate(document.passages):
                # For each passage in each document in the collection
                # add the appropriate annotation
                for p in pub_readers:
                    for annotation in p.collection.documents[d_idx].passages[p_idx].annotations:
                        ann_type = annotation.infons['type']

                        if ann_type in approved_types:
                            annotation.clear_infons()
                            annotation.put_infon('type', str( approved_types.index(ann_type) ))
                            annotation.put_infon('user', 'pubtator')
                            reader.collection.documents[d_idx].passages[p_idx].add_annotation(annotation)

        return reader

    def as_writer(self):
        from mark2cure.common.formatter import bioc_writer
        writer = bioc_writer(None)
        document = self.as_bioc()

        passage_offset = 0
        for section in self.available_sections():
            passage = section.as_bioc(passage_offset)
            passage_offset += len(passage.text)
            document.add_passage(passage)
        writer.collection.add_document(document)
        return writer

    def as_bioc(self):
        document = BioCDocument()
        document.id = str(self.document_id)
        document.put_infon('id', str(self.pk))
        document.put_infon('source', str(self.source))
        return document

    class Meta:
        ordering = ('-created',)
        get_latest_by = 'updated'


class Pubtator(models.Model):
    document = models.ForeignKey(Document)

    kind = models.CharField(max_length=200, blank=True)
    session_id = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True, null=True)

    request_count = models.IntegerField(default=0)
    validate_cache = models.BooleanField(default=False)

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return 'pubtator'


class Section(models.Model):
    SECTION_KIND_CHOICE = (
        ('o', 'Overview'),
        ('t', 'Title'),
        ('a', 'Abstract'),
        ('p', 'Paragraph'),
        ('f', 'Figure'),
    )
    kind = models.CharField(max_length=1, choices=SECTION_KIND_CHOICE)
    text = models.TextField(blank=True)
    source = models.ImageField(blank=True, upload_to='media/images/', default='images/figure.jpg')

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    document = models.ForeignKey(Document)

    def as_bioc(self, offset):
        passage = BioCPassage()
        passage.put_infon('type', 'paragraph')
        passage.put_infon('section', self.get_kind_display().lower())
        passage.put_infon('id', str(self.pk))
        passage.text = self.text
        passage.offset = str(offset)
        return passage

    def resultwords(self, user_view, gm_view):
        # Gather words and positions from the text
        words_index = WhitespaceTokenizer().span_tokenize(self.text)
        words_text = WhitespaceTokenizer().tokenize(self.text)
        words = zip(words_index, words_text)

        # Add counters for concensus count and personal annotation
        # ((start, stop), 'Word string itself', Intensity, GM Ann ID, User Ann ID, Did user annotate)
        words = [w + (0, None, None, False,) for w in words]

        # Gather other annotations from GM and users for this section
        gm_anns = Annotation.objects.filter(view=gm_view).values_list('pk', 'start', 'text')

        # Build the running counter of times a word was annotated
        for gm_pk, start, text in gm_anns:
            length = len(text)

            for idx, word in enumerate(words):
                word_start = word[0][0]
                counter = word[2]
                if word_start >= start and word_start <= start + length:
                    counter += 1
                    words[idx] = (word[0], word[1], counter, gm_pk, word[3], word[4])

        user_anns = Annotation.objects.filter(view=user_view).values_list('pk', 'start', 'text')

        # Build the running counter of times a word was annotated
        for user_pk, start, text in user_anns:
            length = len(text)
            for idx, word in enumerate(words):
                word_start = word[0][0]
                if word_start >= start and word_start <= start + length:
                    words[idx] = (word[0], word[1], word[2], word[3], user_pk, True)

        return words

    def update_view(self, user, task_type, completed=False):
        view = View.objects.filter(user=user, task_type=task_type, section=self).latest()
        view.completed = completed
        view.save()
        return view

    def __unicode__(self):
        if self.kind == 'o':
            return u'[Overview] {0}'.format(self.document.title)
        else:
            return self.text

TASK_TYPE_CHOICE = (
    ('cr', 'Concept Recognition'),
    ('cn', 'Concept Normalization'),
    ('rv', 'Relationship Verification'),
    ('ri', 'Relationship Identification'),
    ('rc', 'Relationship Correction'),
)


class View(models.Model):
    task_type = models.CharField(max_length=3, choices=TASK_TYPE_CHOICE, blank=True, default='cr')
    completed = models.BooleanField(default=False, blank=True)
    opponent = models.ForeignKey('self', blank=True, null=True)

    section = models.ForeignKey(Section)
    user = models.ForeignKey(User)


    class Meta:
        get_latest_by = 'pk'


    def __unicode__(self):
        return u'Document #{doc_id}, Section #{sec_id} by {username}'.format(
            doc_id=self.section.document.pk,
            sec_id=self.section.pk,
            username=self.user.username)


class Annotation(models.Model):
    ANNOTATION_KIND_CHOICE = (
        ('e', 'Entities'),
        ('a', 'Attributes'),
        ('r', 'Relations'),
        ('t', 'Triggers'),
        ('e', 'Events'),
    )
    kind = models.CharField(max_length=1, choices=ANNOTATION_KIND_CHOICE, blank=False, default='e')

    # Disease, Gene, Protein, et cetera...
    ANNOTATION_TYPE_CHOICE = (
        'disease',
        'drug',
        'gene_protein',
    )
    type = models.CharField(max_length=40, blank=True, null=True, default='disease')

    text = models.TextField(blank=True, null=True)
    start = models.IntegerField(blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)

    view = models.ForeignKey(View)

    def is_exact_match(self, comparing_annotation):
        return True if self.start == comparing_annotation.start and len(self.text) == len(comparing_annotation.text) else False

    def __unicode__(self):
        if self.kind == 'r':
            return 'Relationship Ann'
        if self.kind == 'e':
            return '{0} ({1}) [{2}]'.format(self.text, self.start, self.pk)
        else:
            return self.type

    class Meta:
        get_latest_by = 'updated'
        # (TODO) This is not supported by MySQL but would help prevent dups in this table
        # unique_together = ['kind', 'type', 'text', 'start', 'view']

