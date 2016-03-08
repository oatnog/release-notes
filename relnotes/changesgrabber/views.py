import csv
import codecs
from datetime import datetime
import re

from os import path


from django.shortcuts import render_to_response
from django.http import HttpResponse
from django import forms
from relnotes.changesgrabber.models import LabelCompareForm, DepotspecForm
from relnotes.changesgrabber.models import BugzillaBugs,PerforceChanges

from P4 import P4Exception

from xmlrpclib import Fault

def changes(request):

    # skip to the end if it's a GET, but here's the meat of the view  
    if request.method == 'POST': # If the form has been submitted...
        depotform = DepotspecForm(request.POST, auto_id = True)

        if not depotform.is_valid():
            # Can't go any further w/o a proper depot. Bail out and display errors
            labelform = LabelCompareForm(auto_id = True) # An unbound form
            labelform.set_labels_from_depotspec(depotform.DEPOTSPECS[0][0])
            return render_to_response('changes/index.html', {
                'depotform': depotform,
                'labelform': labelform,
            })

        # otherwise, carry on with the next form
        depotspec = depotform.cleaned_data['depotspec']
        labelform = LabelCompareForm(request.POST, auto_id = True)

        # Why do we need to always update the label_list ChoiceFields? 
        # Shouldn't they be forwarded along from request.POST?
        # I want to only do this if they click "Update Labels"
        labelform.set_labels_from_depotspec(depotspec)
        
        if 'update' in request.POST:
            return render_to_response('changes/index.html', {
                'depotform': depotform,
                'labelform': labelform,
            })


        if labelform.is_valid():
            labelone = labelform.cleaned_data['labelone']
            labeltwo = labelform.cleaned_data['labeltwo']                   

            try:
                p4changes = PerforceChanges()
            except P4Exception:
                return HttpResponse(p4changes.p4.errors)

            range_changes = p4changes.get_changes_from_range(depotspec,labelone,labeltwo)

            PR_ids = p4changes.get_PRs_from_changes(range_changes)
            bz = BugzillaBugs()

            """
            Here, we alter the  list of changes so it is now also list of...
            change       : the p4 change number
            user         : who submitted the change
            desc         : the p4 change description
            changed_dirs : a list of strings showing where the changes happened
            bzbugs       : a list of Bugzilla bug objects, with all the details.
            """
            for change in range_changes:
                if int(change['change']) in PR_ids.keys():
                    # If a PR is mentioned more than once in a change desc, only get it once
                    # ...the lazy way
                    PRset = frozenset(PR_ids[int(change['change'])]['bugs'])
                    try:
                        change['bzbugs'] = bz.get_bugs(list(PRset))
                    # This will fail if the PR id does not exist in Bz
                    # If so, just skip it for now. We should skip the bad PR and grab the others, but...
                    # maybe with a quicksort? or just check for the index before calling it?
                    except Fault, err:
                            if err.faultCode == 101:
                                bad_PR_numbers = re.search("([23][0-9]{6})", err.faultString).groups()
                                change['badbugs'] = bad_PR_numbers
                                change['bzbugs'] = bz.get_bugs(list(PRset - set(bad_PR_numbers)))
                    # It might be faster to do one p4 call with all the change #s. Not sure.
                    
                    changed_files = p4changes.get_unique_dirs_from_change(change['change'])
                    unique_dirs = []
                    for depotfile in changed_files:
                        if depotfile.startswith(depotspec[:-3]) and path.dirname(depotfile[len(depotspec[:-3]):]) not in unique_dirs:
                            unique_dirs.append(path.dirname(depotfile[len(depotspec[:-3]):]))

                    change['changed_dirs'] = unique_dirs      


            if request.POST["displaytype"] == u'Submit':       
                return render_to_response('changes/index.html', { 
                    'depotform': depotform,
                    'labelform': labelform,
                    'range_changes' : range_changes,
                })


            elif request.POST["displaytype"] == u'Generate CSV': # we could also do this with a template...
                response = HttpResponse(mimetype='text/csv')
                d = datetime.now()
                response['Content-Disposition'] = ("attachment; filename=%s.csv" % d.strftime('%d-%b-%y-%H%m'))

                writer = csv.writer(response)
                writer.writerow(["Change List for %s between %s and %s" % (request.POST["depotspec"], request.POST["labelone"], request.POST["labeltwo"])])
                writer.writerow(['Change','Submitted By','Description'])

                for change in range_changes:
                    changescsv = [ change['change'],change['user'],change['desc'] ]
                    writer.writerow(changescsv)
                    # Send the csv file (user should be prompted to save or load it)
                return response


    else:
        depotform = DepotspecForm(auto_id = True) # An unbound form
        labelform = LabelCompareForm(auto_id = True) # An unbound form
        labelform.set_labels_from_depotspec(depotform.DEPOTSPECS[0][0])
    return render_to_response('changes/index.html', {
        'depotform': depotform,
        'labelform': labelform,
    })

