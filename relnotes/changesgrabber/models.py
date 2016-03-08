from django.db import models

from django import forms
import xmlrpclib
import re
from P4 import P4,P4Exception

# We share a single p4 connection so we don't waste time opening and closing them every time
# a page is reloaded
p4 = P4()
p4.port = "sfo-perforce:5000"
p4.user = "perforce"
p4.password = "" # add password before deployment
p4.connect()

# We share a single Bugzilla connection for similar reasons

bzuser = "aanderso@opentv.com"
bzpasswd = "" # add password before deployment
proxyurl = "http://sfo-bugzilla.opentv.com/xmlrpc.cgi"
bzproxy = xmlrpclib.ServerProxy(proxyurl)
bzproxy.User.login({'login':bzuser,'password':bzpasswd})


class DepotspecForm(forms.Form):
    DEPOTSPECS = (
        ( '//OTV_OS/Core2/RELEASE/...', '//OTV_OS/Core2/RELEASE/...' ),
        ( '//OTV_OS/Core2/MAIN/...', '//OTV_OS/Core2/MAIN/...' ),
        ( '//OTV_OS/Core2/v2.1/...', '//OTV_OS/Core2/v2.1/...' ),
        ( '//OTV_OS/Core2/v2.0/...', '//OTV_OS/Core2/v2.0/...' ),
        ( '//OTV_OS/Core3/MAIN/...', '//OTV_OS/Core3/MAIN/...' ),
    )
    depotspec_list = forms.ChoiceField(choices = DEPOTSPECS)
    depotspec = forms.CharField(
        initial = DEPOTSPECS[0][0],
        widget = forms.TextInput(attrs={'size':'40'}),
    )
    def clean_depotspec(self):
        data = self.cleaned_data['depotspec']
        if not re.match('^//\S*\.{3}$', data):
            raise forms.ValidationError("Depots must begin with double slash and end with three trailing periods; e.g., //OTV_OS/Core2/v2.0/...")
        return data
    


class LabelCompareForm(forms.Form):

    labelone = forms.CharField(max_length=255, required=False,widget=forms.TextInput(attrs={'size':'40'}))
    labeltwo = forms.CharField(max_length=255, required=False,widget=forms.TextInput(attrs={'size':'40'}))
    labelone_list = forms.ChoiceField()
    labeltwo_list = forms.ChoiceField()
    
  
    def clean_labelone(self):
        data = self.cleaned_data['labelone']
        validlabel = self.data['labelone_list']
        if not ( data =='' or data == validlabel or data.isdigit() ):
            raise forms.ValidationError("Please select a label from the list or input a Perforce change number.")
        return data

    def clean_labeltwo(self):
        data = self.cleaned_data['labeltwo']
        validlabel = self.data['labeltwo_list']
        if not ( data == '' or data == validlabel or data.isdigit() ):
            raise forms.ValidationError("Please select a label from the list or input a Perforce change number.")
        return data    
    
    def set_labels_from_depotspec(self, depotspec):
        """
        Feed it a depot, and it will set this form's select inputs (ChoiceFields)
        to the labels found in that depot.
        """
        try:
            labels = p4.run("labels", "%s" % (depotspec) )
        except P4Exception:
            for e in p4.errors:
                print e
            return p4.errors
        mylabels = []
        if not labels:
            mylabels = ( ('No Labels Found','No Labels Found'),)
        for label in labels:
            mylabels.append( (label['label'],label['label']) )
        self.fields['labelone_list'].choices = mylabels
        self.fields['labeltwo_list'].choices = mylabels
        return mylabels #not really necessary, but here it is if folks want it



class BugzillaBugs(models.Model):
    """
    Grabs all the bugs in the list, via the Bugzilla XMLRPC interface
    """
    def get_bugs(self,idlist):
        bzids = {'ids':idlist, 'permissive': 1 } # add 'permissive' so one bad bug doesn't abort the whole thing
        # would it be faster to return less data?
        bugs = bzproxy.Bug.get(bzids)['bugs']
        return bugs


class PerforceChanges(models.Model):
    def get_changes_from_range(self, depotspec, labelone, labeltwo):
        """
        Checks the two entries, finding out if they are labels or change numbers.
        For labels, finds the earliest change number in that label.
        Then it returns a list of changes, with each change containing:
        change : Change number
        desc   : Change description
        user   : User who submitted the change.
        """

        changes = []
        #changenumregex = re.compile("(^\d$)") # all digits? It must be a change number!

        if not labelone or not labeltwo:
            return changes # remove this condition when form validation is fixed
        elif labelone.isdigit() and labeltwo.isdigit():
            # both are change nubmers, so it simple
            changes = p4.run("changes", "-l", "%s@%s,%s" % (depotspec, labelone, labeltwo))
        elif labelone.isdigit() and not labeltwo.isdigit():
            # labelone is a change number, labeltwo is a label
            lastchange = p4.run("changes","-m1", "%s@%s" % (depotspec, labeltwo))
            changes = p4.run("changes", "-l", "%s@%s,%s" % (depotspec, labelone, lastchange[0]['change']))                                                      
        elif not labelone.isdigit() and labelone.isdigit():
            #labeltwo is a change number, labelone is label
            firstchange = p4.run("changes","-m1", "%s@%s" % (depotspec, labelone))
            changes = p4.run("changes", "-l", "%s@%s,%s" % (depotspec, firstchange[0]['change'], labeltwo))
        else:
            # Neither are change numbers. Must be labels.
            label1changes = p4.run("changes", "%s@%s" % (depotspec, labelone))
            label2changes = p4.run("changes", "%s@%s" % (depotspec, labeltwo))

            label1changenumbers = [ change['change'] for change in label1changes ]
            label2changenumbers = [ change['change'] for change in label2changes ]
            # make the lists sets so set arithmatic works
            for change in (set(label2changenumbers) - set(label1changenumbers)):
                changespec = p4.run("change","-o","%s" % change)
                changes.append({ 'change' : changespec[0]['Change'], 
                                 'desc' : changespec[0]['Description'],
                                 'user' : changespec[0]['User'] })

        return changes

    def get_PRs_from_changes(self, p4changenumbers):
        """
        Once we have the changes, search through the change descriptions for
        Bugzilla bug numbers.
        Add Jira support someday?
        """
        buglist = {}

        bugregex = re.compile("([23][0-9]{6})")
        for change in p4changenumbers:
            test = p4.run("info")
            changed_files = p4.run("describe","-s","%s" % (change['change']))[0]['depotFile']
            m = bugregex.findall(change['desc'])
            buglist[int(change['change'])] = { 'changed_files' : changed_files, 'bugs' :(m) }

        return buglist

    def get_unique_dirs_from_change(self, changenum):
        changed_files = p4.run("describe","-s","%s" % (changenum))[0]['depotFile']
        return changed_files






