from django.db.models import Q
from pbs.implementation.models import TrafficControlDiagram
import os
from datetime import datetime

def update_traffic_documents(path='/path/to/TrafficControlDiagram_2022/', filter_old_docs=['DBCA_21', 'DBCA-19', 'custom']):
    '''
    Script to update models with latest Traffic Flow Diagrams

    1. create the models from files located in 'path'
    2. if rewuseted to remove existing items from dropdown widget, need to filter these by setting 'display_order=-1', since existing records still need the files
    3. manually copy the files located at 'path' to '../pbs/static/pbs/traffic-control-diagrams/'

    From Shell:
        from pbs.utils.traffic_control_diagrams_update import update_traffic_documents
        update_traffic_documents(path='/home/jawaidm/Downloads/TrafficControlDiagram_2022/', filter_old_docs=['DBCA_21', 'DBCA-19', 'custom'])

    '''
    filenames = os.listdir(path)

    for filename in filenames:                                                   
        print(filename, len(filename))
	try:               
	    TrafficControlDiagram.objects.create(path=filename, name=filename)
	    #pass
	except Exception as e:
	    print(e)

    # filter existing diagrams from dropdown widget by assigning archive date to the record
    # Must not remove the files from media or delete records from the model - existing ePFPs refer to them !
    #for tcd in TrafficControlDiagram.objects.filter(Q(name__icontains='DBCA_21') | Q(name__icontains='DBCA-19') | Q(name__icontains='custom')):
    today = datetime.now().date()
    for filter_str in filter_old_docs:
        for tcd in TrafficControlDiagram.objects.filter(name__icontains=filter_str):
            print(tcd)              
            tcd.archive_date = today
            tcd.save()

