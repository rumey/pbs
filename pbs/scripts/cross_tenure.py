import os

from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile

from pbs.prescription.models import Prescription
from pbs.document.models import Document,DocumentCategory,DocumentTag

ADD_IF_NOT_EXIST = 1
OVERRIDE_EXISTING_DOC = 2
ADD_DOC = 3
def batch_update_approve_status(burnids_file,signed_file,useremail,financial_year=None,signed_time=None,set_cross_tenure=None,upload_policy=None):
    now = timezone.now()
    signed_time = signed_time or now
    user = User.objects.get(email__iexact=useremail)
    upload_policy = upload_policy or ADD_DOC
    
    if not financial_year:
        today = timezone.now().date()
        fin_year = today.year if today.month <= 6 else today.year + 1
        financial_year = str(fin_year - 1) + '/' + str(fin_year)

    burnids = None
    with open(burnids_file,"r") as f:
        burnids = f.read()

    with open(signed_file,"rb") as f:
        signedcontent = ContentFile(f.read(),os.path.split(signed_file)[1])

    category = DocumentCategory.objects.get(name__iexact='declarations')
    tag = DocumentTag.objects.get(category=category,name__iexact='Section 33(1)(f) Declaration')

    burnids = [i for i in burnids.split() if i]

    processed_burnids = []
    not_existed_burnids = []
    not_cross_tenure_burnids = []
    doc_already_uploaded_burnids = []
    doc_uploaded_burnids = []
    for burnid in burnids:
        update_fields=["non_calm_tenure_approved"]
        if burnid == 'KAL_021':
            import ipdb;ipdb.set_trace()
        try:
            obj = Prescription.objects.get(burn_id=burnid,financial_year=financial_year)
        except ObjectDoesNotExist as ex:
            not_existed_burnids.append(burnid)
            continue;
        if not obj.non_calm_tenure:
            if set_cross_tenure:
                obj.non_calm_tenure = True
                update_fields.append("non_calm_tenure")
            else:
                not_cross_tenure_burnids.append(burnid)
                continue;
        obj.non_calm_tenure_approved = True
        obj.save(update_fields=update_fields)

        if Document.objects.filter(prescription=obj,category=category,tag=tag).count() == 0 or upload_policy == ADD_DOC:
            signeddoc = Document(prescription=obj,category=category,tag=tag,document=signedcontent,document_created=signed_time,creator=user,created=now,modifier=user,modified=now)
            signeddoc.save()
            doc_uploaded_burnids.append(burnid)
        elif upload_policy == OVERRIDE_EXISTING_DOC:
            Document.objects.filter(prescription=obj,category=category,tag=tag).delete()
            signeddoc = Document(prescription=obj,category=category,tag=tag,document=signedcontent,document_created=signed_time,creator=user,created=now,modifier=user,modified=now)
            signeddoc.save()
            doc_uploaded_burnids.append(burnid)
        else:
            doc_already_uploaded_burnids.append(burnid)

        processed_burnids.append(burnid)


    if not_existed_burnids:
        print("The burns({}) are not found".format(",".join(not_existed_burnids)))
        print("")

    if not_cross_tenure_burnids:
        print("The burns({}) are not cross tenure burns".format(",".join(not_cross_tenure_burnids)))
        print("")

    if doc_already_uploaded_burnids:
        print("The signed document for the burns({}) are alreay uploaded".format(",".join(doc_already_uploaded_burnids)))
        print("")

    print("The signed document for the burns({}) are uploaded successfully".format(",".join(doc_uploaded_burnids)))
    print("")

    if processed_burnids:
        print("The burns({}) are processed successfully".format(",".join(processed_burnids)))
        print("")

#batch_update_approve_status("logs/burnids.txt","logs/signed.pdf","rocky.chen@dbca.wa.gov.au",financial_year='2018/2019',set_cross_tenure=True,upload_policy=ADD_DOC)
